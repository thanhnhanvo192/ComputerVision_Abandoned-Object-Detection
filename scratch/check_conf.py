import cv2
import sys
import os
sys.path.insert(0, os.path.abspath('.'))

from core.detector import YOLODetector

print("Checking low confidence detections (conf >= 0.05) in pets2006_3.mp4...", flush=True)

det = YOLODetector('weights/best.pt', conf_thresh=0.05)
cap = cv2.VideoCapture('pets2006_3.mp4')
f_idx = 0
found_center_luggage = 0

while cap.isOpened():
    ret, frame = cap.read()
    if not ret:
        break
    f_idx += 1
    
    lug, per = det.detect_and_track(frame)
    if lug:
        for tid, ldata in lug.items():
            bbox = ldata['bbox']
            conf = ldata['conf']
            # Kiểm tra các bbox nằm ở giữa khung hình (y1 < 900)
            if bbox[1] < 900:
                found_center_luggage += 1
                if found_center_luggage % 15 == 0:
                    print(f"Frame {f_idx:4d} ({f_idx/30.0:5.1f}s): Luggage #{tid:2d} | Conf: {conf:.3f} | BBox: {[round(v,1) for v in bbox]}", flush=True)

cap.release()
print(f"Finished! Total frames: {f_idx}, Luggage detections in center: {found_center_luggage}", flush=True)
