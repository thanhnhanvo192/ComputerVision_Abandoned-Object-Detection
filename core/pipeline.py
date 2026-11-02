"""
VideoPipeline: Module xử lý video dùng chung cho cả main.py và app_gui.py.
Loại bỏ code trùng lặp (DRY) giữa CLI và GUI interface.
"""
import time
import json
import os
import pandas as pd
from typing import Dict, List, Tuple, Optional, Any

import config
from core.detector import YOLODetector
from core.abandoned_detector import AbandonedObjectDetector
from core.visualizer import Visualizer


class VideoPipeline:
    """
    Pipeline xử lý video phát hiện vật thể bị bỏ quên.
    
    Đóng gói toàn bộ logic: YOLO Detection → Tracking → Abandon Analysis → Visualization.
    Hỗ trợ frame skip để tăng hiệu năng.
    """
    
    def __init__(self, 
                 model_path: str = config.MODEL_PATH,
                 conf_thresh: float = config.CONF_THRESHOLD,
                 abandon_time: float = config.ABANDON_TIME_THRESHOLD,
                 owner_dist: float = config.OWNER_DISTANCE_THRESHOLD,
                 detect_every_n: int = config.DETECT_EVERY_N):
        """
        Khởi tạo pipeline.
        
        Args:
            model_path: Đường dẫn file trọng số YOLO
            conf_thresh: Ngưỡng tin cậy YOLO
            abandon_time: Thời gian (giây) để phát cảnh báo bỏ quên
            owner_dist: Khoảng cách tối đa (pixel) người–hành lý
            detect_every_n: Chỉ chạy YOLO mỗi N frame (frame skip)
        """
        self.detector = YOLODetector(model_path=model_path, conf_thresh=conf_thresh)
        self.abandon_engine = AbandonedObjectDetector(
            owner_dist_thresh=owner_dist,
            abandon_time_thresh=abandon_time
        )
        self.visualizer = Visualizer()
        self.detect_every_n = max(1, detect_every_n)
        
        # Cache kết quả detection gần nhất (cho frame skip)
        self._last_luggage_dets: Dict = {}
        self._last_person_dets: Dict = {}
    
    def process_frame(self, frame, frame_idx: int, fps: float) -> Tuple[Any, Dict, Dict, List, float]:
        """
        Xử lý một frame: detect → track → analyze → visualize.
        
        Args:
            frame: Frame ảnh BGR từ OpenCV
            frame_idx: Chỉ số frame hiện tại (bắt đầu từ 1)
            fps: Tốc độ video gốc (dùng để tính timestamp)
        
        Returns:
            annotated_frame: Frame đã vẽ annotation
            luggage_states: Dict trạng thái hành lý
            person_dets: Dict detection người
            new_alerts: List cảnh báo mới
            process_fps: FPS xử lý thực tế
        """
        frame_time = frame_idx / fps
        t0 = time.time()
        
        # Frame skip: Chỉ chạy YOLO mỗi N frame, các frame trung gian dùng kết quả cũ
        if frame_idx % self.detect_every_n == 0 or frame_idx == 1:
            luggage_dets, person_dets = self.detector.detect_and_track(frame)
            self._last_luggage_dets = luggage_dets
            self._last_person_dets = person_dets
        else:
            luggage_dets = self._last_luggage_dets
            person_dets = self._last_person_dets
        
        # Phân tích logic bỏ quên
        luggage_states, new_alerts = self.abandon_engine.process_frame(
            luggage_dets, person_dets, current_time=frame_time, fps=fps
        )
        
        process_fps = 1.0 / max(time.time() - t0, 0.001)
        
        # Vẽ visualization
        annotated_frame = self.visualizer.draw_frame(
            frame, luggage_states, person_dets, fps=process_fps
        )
        
        return annotated_frame, luggage_states, person_dets, new_alerts, process_fps
    
    def reset(self):
        """Reset trạng thái pipeline (khi xử lý video mới)"""
        self.abandon_engine.reset()
        self._last_luggage_dets = {}
        self._last_person_dets = {}
    
    @staticmethod
    def export_results(all_alert_records: List[Dict], 
                       csv_path: str,
                       json_path: Optional[str] = None,
                       video_info: Optional[Dict] = None,
                       processing_stats: Optional[Dict] = None):
        """
        Xuất kết quả phân tích ra file CSV và JSON.
        
        Args:
            all_alert_records: Danh sách các bản ghi cảnh báo
            csv_path: Đường dẫn file CSV đầu ra
            json_path: Đường dẫn file JSON đầu ra (None = tự sinh từ csv_path)
            video_info: Thông tin video đầu vào
            processing_stats: Thống kê xử lý
        """
        # Xuất CSV
        if all_alert_records:
            df_alerts = pd.DataFrame(all_alert_records)
            df_alerts.to_csv(csv_path, index=False)
            print(f"[*] Nhật ký cảnh báo đã ghi vào CSV: {csv_path} ({len(all_alert_records)} sự kiện)")
        else:
            print("[*] Không phát hiện thấy vật thể bị bỏ quên nào trong video.")
        
        # Xuất JSON (chi tiết hơn CSV)
        if json_path is None:
            json_path = csv_path.replace('.csv', '.json')
        
        output_data = {
            "video_info": video_info or {},
            "config": {
                "abandon_threshold_sec": config.ABANDON_TIME_THRESHOLD,
                "suspicious_threshold_sec": config.SUSPICIOUS_TIME_THRESHOLD,
                "unattended_threshold_sec": config.UNATTENDED_TIME_THRESHOLD,
                "owner_distance_px": config.OWNER_DISTANCE_THRESHOLD,
                "model_path": config.MODEL_PATH,
                "conf_threshold": config.CONF_THRESHOLD,
            },
            "alerts": all_alert_records,
            "statistics": processing_stats or {},
            "total_alerts": len(all_alert_records)
        }
        
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, ensure_ascii=False, indent=2)
        print(f"[*] Báo cáo JSON đã ghi tại: {json_path}")

