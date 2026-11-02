import cv2
import numpy as np
from ultralytics import YOLO
from typing import Dict, Tuple
import config

class YOLODetector:
    def __init__(self, model_path: str = config.MODEL_PATH, 
                 conf_thresh: float = config.CONF_THRESHOLD, 
                 tracker: str = config.TRACKER_TYPE):
        """
        Khởi tạo detector sử dụng Ultralytics YOLO11.
        
        Args:
            model_path: Đường dẫn tới file trọng số (.pt)
            conf_thresh: Ngưỡng tin cậy tối thiểu cho detection
            tracker: Loại tracker sử dụng (bytetrack.yaml hoặc botsort.yaml)
        """
        self.model = YOLO(model_path)
        self.conf_thresh = conf_thresh
        self.tracker = tracker
        
    def detect_and_track(self, frame: np.ndarray) -> Tuple[Dict, Dict]:
        """
        Phát hiện và theo dõi đối tượng trong 1 frame.
        
        Args:
            frame: Frame ảnh BGR từ OpenCV (numpy array HxWx3)
        
        Returns:
            luggage_detections: dict {track_id: {track_id, bbox, center, conf, class_id}}
            person_detections:  dict {track_id: {track_id, bbox, center, conf, class_id}}
        """
        results = self.model.track(
            source=frame,
            conf=self.conf_thresh,
            iou=config.IOU_THRESHOLD,
            tracker=self.tracker,
            persist=True,
            verbose=False
        )
        
        luggage_detections: Dict[int, dict] = {}
        person_detections: Dict[int, dict] = {}
        
        if not results or len(results) == 0:
            return luggage_detections, person_detections
            
        result = results[0]
        if result.boxes is None or len(result.boxes) == 0:
            return luggage_detections, person_detections
            
        boxes = result.boxes
        
        for i in range(len(boxes)):
            box = boxes[i]
            # Lấy tọa độ bounding box [x1, y1, x2, y2]
            xyxy = box.xyxy[0].cpu().numpy()
            x1, y1, x2, y2 = float(xyxy[0]), float(xyxy[1]), float(xyxy[2]), float(xyxy[3])
            
            # Lấy ID theo dõi (Track ID)
            if box.id is not None:
                track_id = int(box.id[0].cpu().numpy())
            else:
                # Nếu chưa được cấp track_id (ví dụ frame đầu hoặc unassigned)
                track_id = -(i + 1)
                
            class_id = int(box.cls[0].cpu().numpy())
            conf = float(box.conf[0].cpu().numpy())
            
            center_x = (x1 + x2) / 2.0
            center_y = (y1 + y2) / 2.0
            
            obj_data = {
                'track_id': track_id,
                'bbox': [x1, y1, x2, y2],
                'center': (center_x, center_y),
                'conf': conf,
                'class_id': class_id
            }
            
            if class_id == config.LUGGAGE_CLASS_ID:
                luggage_detections[track_id] = obj_data
            elif class_id == config.PERSON_CLASS_ID:
                person_detections[track_id] = obj_data
                
        return luggage_detections, person_detections
