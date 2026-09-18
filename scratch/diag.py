import cv2
import sys
import os
sys.path.insert(0, os.path.abspath('.'))

if sys.stdout and hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

from core.detector import YOLODetector

print("Inspecting raw YOLO predictions on pets2006_3.mp4...", flush=True)

det = YOLODetector('weights/best.pt', conf_thresh=0.10)
cap = cv2.VideoCapture('pets2006_3.mp4')
frame_idx = 0

luggage_frames = 0
person_frames = 0

while cap.isOpened():
    ret, frame = cap.read()
    if not ret:
        break
    frame_idx += 1
    t_sec = frame_idx / 30.0
    
    lug, per = det.detect_and_track(frame)
    if lug:
        luggage_frames += 1
        print(f"Frame {frame_idx:4d} ({t_sec:5.1f}s): DETECTED LUGGAGE! {lug}", flush=True)
    if per and frame_idx % 100 == 0:
        person_frames += 1
        print(f"Frame {frame_idx:4d} ({t_sec:5.1f}s): DETECTED PERSON! Count: {len(per)}", flush=True)

cap.release()
print(f"DONE! Total frames: {frame_idx}, Frames with Luggage: {luggage_frames}", flush=True)
