import cv2
import numpy as np
import os
import sys

if sys.stdout and hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')


def create_test_video(output_path="test_video.mp4", duration_sec=14, fps=30):
    """
    Tạo một video kiểm thử tổng hợp (Synthetic Test Video) mô phỏng lại kịch bản:
    1. Người đi vào cùng túi xách
    2. Đặt túi xách xuống sàn tại (320, 260)
    3. Stand near luggage (3 giây)
    4. Người rời khỏi khung hình
    5. Túi đứng yên 1 mình > 5 giây -> Kích hoạt CẢNH BÁO
    """
    width, height = 640, 480
    total_frames = duration_sec * fps
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))
    
    # Tạo nền phòng giám sát / Sàn nhà đơn giản
    bg = np.zeros((height, width, 3), dtype=np.uint8)
    # Sàn nhà xám nhạt
    bg[:] = (220, 220, 220)
    # Thêm đường gạch lát sàn
    for y in range(0, height, 60):
        cv2.line(bg, (0, y), (width, y), (190, 190, 190), 1)
    for x in range(0, width, 60):
        cv2.line(bg, (x, 0), (x, height), (190, 190, 190), 1)
        
    print(f"[*] Đang khởi tạo video kiểm thử '{output_path}' ({total_frames} frames)...")
    
    for i in range(total_frames):
        frame = bg.copy()
        t = i / fps  # Thời gian (giây)
        
        # Thêm nhãn thời gian thực tế
        cv2.putText(frame, f"TEST SURVEILLANCE VIDEO - Time: {t:.1f}s", (15, 30), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (50, 50, 50), 2)
        
        # 1. Giai đoạn 0s -> 3s: Người đi vào xách túi
        if t < 3.0:
            px = int(100 + t * 70)  # Người di chuyển từ 100 -> 310
            py = 220
            lx = px + 35
            ly = py + 30
            
            # Vẽ người (Person)
            cv2.rectangle(frame, (px - 20, py - 60), (px + 20, py + 40), (200, 100, 0), -1)
            cv2.circle(frame, (px, py - 75), 18, (200, 100, 0), -1)
            cv2.putText(frame, "PERSON", (px - 22, py - 100), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (200, 100, 0), 1)
            
            # Vẽ hành lý (Luggage)
            cv2.rectangle(frame, (lx - 25, ly - 20), (lx + 25, ly + 20), (0, 120, 200), -1)
            cv2.putText(frame, "SUITCASE", (lx - 25, ly - 25), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 120, 200), 1)

        # 2. Giai đoạn 3s -> 6s: Đặt hành lý tại (345, 250) và đứng cạnh
        elif 3.0 <= t < 6.0:
            px = 310
            py = 220
            lx = 345
            ly = 250
            
            # Vẽ người đứng gần túi
            cv2.rectangle(frame, (px - 20, py - 60), (px + 20, py + 40), (200, 100, 0), -1)
            cv2.circle(frame, (px, py - 75), 18, (200, 100, 0), -1)
            cv2.putText(frame, "PERSON (STANDING)", (px - 35, py - 100), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (200, 100, 0), 1)
            
            # Vẽ hành lý nằm trên sàn
            cv2.rectangle(frame, (lx - 25, ly - 20), (lx + 25, ly + 20), (0, 120, 200), -1)
            cv2.putText(frame, "SUITCASE", (lx - 25, ly - 25), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 120, 200), 1)

        # 3. Giai đoạn 6s -> 14s: Người đi ra xa, túi ở lại một mình
        else:
            lx = 345
            ly = 250
            
            # Người đi dần ra ngoài lề màn hình
            px = int(310 + (t - 6.0) * 80)
            py = 220
            
            if px < width + 50:
                cv2.rectangle(frame, (px - 20, py - 60), (px + 20, py + 40), (200, 100, 0), -1)
                cv2.circle(frame, (px, py - 75), 18, (200, 100, 0), -1)
                cv2.putText(frame, "PERSON (WALKING AWAY)", (px - 45, py - 100), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (200, 100, 0), 1)
                
            # Hành lý đứng yên cố định
            cv2.rectangle(frame, (lx - 25, ly - 20), (lx + 25, ly + 20), (0, 120, 200), -1)
            cv2.putText(frame, "SUITCASE (STATIONARY)", (lx - 45, ly - 25), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 120, 200), 1)

        out.write(frame)
        
    out.release()
    print(f"[*] Đã tạo thành công video kiểm thử: {output_path}")

if __name__ == "__main__":
    create_test_video()
