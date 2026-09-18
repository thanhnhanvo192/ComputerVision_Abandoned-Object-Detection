import cv2
import time
import argparse
import os
import sys
import pandas as pd
import config

import functools
import sys
if sys.stdout and hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
print = functools.partial(print, flush=True)


from core.detector import YOLODetector
from core.abandoned_detector import AbandonedObjectDetector
from core.visualizer import Visualizer

def parse_args():
    parser = argparse.ArgumentParser(description="Hệ thống Phát hiện Vật thể Bị Bỏ Quên trong Video Giám sát")
    parser.add_argument("--source", type=str, default="pets2006_3.mp4", help="Đường dẫn file video đầu vào hoặc 0 cho Webcam")
    parser.add_argument("--weights", type=str, default=config.MODEL_PATH, help="Đường dẫn file trọng số YOLO best.pt")
    parser.add_argument("--output", type=str, default=os.path.join(config.OUTPUT_DIR, "output_result.mp4"), help="Đường dẫn file video đầu ra")
    parser.add_argument("--save-csv", type=str, default=os.path.join(config.OUTPUT_DIR, "alert_logs.csv"), help="Đường dẫn lưu file log cảnh báo CSV")
    parser.add_argument("--conf", type=float, default=config.CONF_THRESHOLD, help="Ngưỡng tin cậy nhận diện YOLO")
    parser.add_argument("--abandon-time", type=float, default=config.ABANDON_TIME_THRESHOLD, help="Thời gian (giây) đứng yên không người để phát cảnh báo")
    parser.add_argument("--owner-dist", type=float, default=config.OWNER_DISTANCE_THRESHOLD, help="Khoảng cách tối đa (pixel) giữa người và hành lý")
    parser.add_argument("--no-show", action="store_true", help="Không hiển thị cửa sổ xem trực tiếp OpenCV")
    return parser.parse_args()

def main():
    args = parse_args()
    
    print("=" * 60)
    print(" HỆ THỐNG PHÁT HIỆN VẬT THỂ BỊ BỎ QUÊN (ABANDONED OBJECT DETECTOR)")
    print("=" * 60)
    print(f"[*] Model Weights: {args.weights}")
    print(f"[*] Input Source:  {args.source}")
    print(f"[*] Output Video:  {args.output}")
    print(f"[*] Alert CSV:     {args.save_csv}")
    print(f"[*] Abandon Time:  {args.abandon_time}s")
    print(f"[*] Owner Dist:    {args.owner_dist}px")
    print("=" * 60)
    
    # Khởi tạo Video Capture
    source = int(args.source) if args.source.isdigit() else args.source
    
    # Kiểm tra tồn tại file video nếu source là chuỗi đường dẫn
    if isinstance(source, str) and not os.path.exists(source):
        print(f"[!] WARNING: File video '{source}' không tồn tại!")
        fallback_video = "pets2006_3.mp4"
        if os.path.exists(fallback_video):
            print(f"[*] Tự động chuyển sang sử dụng video mẫu: '{fallback_video}'")
            source = fallback_video
        else:
            print(f"[*] Đang tự động khởi tạo video mẫu '{fallback_video}'...")
            try:
                from create_sample_video import create_test_video
                create_test_video(fallback_video)
                source = fallback_video
            except Exception as e:
                print(f"[!] Lỗi khi khởi tạo video mẫu: {e}")

    cap = cv2.VideoCapture(source)
    
    if not cap.isOpened():
        print(f"[!] ERROR: Không thể mở nguồn video/camera: {args.source}")
        print(f"    Vui lòng kiểm tra lại đường dẫn file video hoặc đảm bảo webcam hoạt động.")
        return

        
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = cap.get(cv2.CAP_PROP_FPS)
    if fps <= 0 or math_isnan(fps):
        fps = 30.0
        
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    print(f"[*] Video Resolution: {width}x{height} | FPS: {fps:.1f} | Total Frames: {total_frames}")

    # Khởi tạo Video Writer
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out_writer = cv2.VideoWriter(args.output, fourcc, fps, (width, height))
    
    # Khởi tạo các module core
    detector = YOLODetector(model_path=args.weights, conf_thresh=args.conf)
    abandon_engine = AbandonedObjectDetector(
        owner_dist_thresh=args.owner_dist,
        abandon_time_thresh=args.abandon_time
    )
    visualizer = Visualizer()
    
    frame_idx = 0
    start_system_time = time.time()
    all_alert_records = []
    
    print("[*] Đang tiến hành xử lý video...")
    
    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                break
                
            frame_idx += 1
            frame_time = frame_idx / fps
            
            # Tính FPS xử lý của hệ thống
            t0 = time.time()
            
            # 1. Phát hiện & Theo dõi đối tượng
            luggage_dets, person_dets = detector.detect_and_track(frame)
            
            # 2. Phân tích logic vật thể bị bỏ quên
            luggage_states, new_alerts = abandon_engine.process_frame(
                luggage_dets, person_dets, current_time=frame_time, fps=fps
            )
            
            # Ghi lại các cảnh báo mới phát sinh
            for alert in new_alerts:
                print(f"[🚨 ALERTS @ {frame_time:.2f}s] Luggage #{alert['luggage_id']} bị bỏ quên! Thời gian: {alert['abandon_duration']:.1f}s")
                all_alert_records.append({
                    'frame_index': frame_idx,
                    'timestamp_sec': round(frame_time, 2),
                    'luggage_id': alert['luggage_id'],
                    'bbox_x1': alert['bbox'][0],
                    'bbox_y1': alert['bbox'][1],
                    'bbox_x2': alert['bbox'][2],
                    'bbox_y2': alert['bbox'][3],
                    'abandon_duration_sec': round(alert['abandon_duration'], 2),
                    'closest_person_dist_px': round(alert['closest_person_dist'], 1)
                })

            process_fps = 1.0 / max(time.time() - t0, 0.001)
            
            # 3. Vẽ đồ họa Visualizer
            annotated_frame = visualizer.draw_frame(frame, luggage_states, person_dets, fps=process_fps)
            
            # Ghi video đầu ra
            out_writer.write(annotated_frame)
            
            # Hiển thị trực tiếp OpenCV Preview
            if not args.no_show:
                cv2.imshow("Abandoned Object Detection System", annotated_frame)
                key = cv2.waitKey(1) & 0xFF
                if key == ord('q') or key == 27:
                    print("[*] Người dùng bấm 'Q' để dừng chương trình.")
                    break
                    
            if frame_idx % 50 == 0:
                print(f" -> Đã xử lý {frame_idx}/{total_frames} frames ({frame_idx/max(total_frames,1)*100:.1f}%) | Processing FPS: {process_fps:.1f}")

    finally:
        cap.release()
        out_writer.release()
        if not args.no_show:
            cv2.destroyAllWindows()
            
    total_time = time.time() - start_system_time
    print("=" * 60)
    print(" HOÀN THÀNH XỬ LÝ VIDEO!")
    print(f"[*] Tổng số frames: {frame_idx}")
    print(f"[*] Thời gian xử lý: {total_time:.2f}s (Tốc độ trung bình: {frame_idx/max(total_time,0.001):.1f} FPS)")
    print(f"[*] Video kết quả đã lưu tại: {args.output}")
    
    # Xuất file CSV log cảnh báo
    if all_alert_records:
        df_alerts = pd.DataFrame(all_alert_records)
        df_alerts.to_csv(args.save_csv, index=False)
        print(f"[*] Nhật ký cảnh báo đã ghi vào CSV: {args.save_csv} ({len(all_alert_records)} sự kiện)")
    else:
        print("[*] Không phát hiện thấy vật thể bị bỏ quên nào trong video.")
    print("=" * 60)

def math_isnan(val):
    return val != val

if __name__ == "__main__":
    main()
