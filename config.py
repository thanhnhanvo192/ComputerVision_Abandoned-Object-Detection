import os

# Đường dẫn mô hình YOLO đã huấn luyện
MODEL_PATH = "weights/best_yolo26.pt"

# Danh sách lớp (Class IDs) từ mô hình
LUGGAGE_CLASS_ID = 0
PERSON_CLASS_ID = 1

CLASS_NAMES = {
    0: "luggage",
    1: "person"
}

# Ngưỡng phát hiện YOLO (Confidence & IOU)
CONF_THRESHOLD = 0.2
IOU_THRESHOLD = 0.50

TRACKER_TYPE = "bytetrack.yaml"  # Hoặc 'botsort.yaml'

# Các ngưỡng đánh giá Vật thể Bị bỏ quên
STATIONARY_MOVE_THRESHOLD = 20.0     # Khoảng cách tối đa (pixels) tâm hành lý di chuyển để coi là đứng yên
STATIONARY_HISTORY_FRAMES = 15      # Số frame lưu lại để tính độ ổn định vị trí
OWNER_DISTANCE_THRESHOLD = 150.0    # Khoảng cách tối đa (pixels) từ hành lý đến người gần nhất để tính là "có chủ"
ABANDON_TIME_THRESHOLD = 4.0        # Thời gian (giây) đứng yên không người để phát cảnh báo ABANDONED

# Hệ thống cảnh báo đa cấp (Multi-level Alert)
SUSPICIOUS_TIME_THRESHOLD = 2.0     # Cấp 1: Nghi ngờ (Warning) — hành lý đứng yên không chủ >= 2s
UNATTENDED_TIME_THRESHOLD = None    # Cấp 2: Không có người trông (Alert) — auto = ABANDON_TIME / 2
ABANDONED_TIME_THRESHOLD_ALIAS = None  # Cấp 3: Bị bỏ quên (Critical) — auto = ABANDON_TIME

# Tự động tính ngưỡng cấp 2, 3 nếu không chỉ định
if UNATTENDED_TIME_THRESHOLD is None:
    UNATTENDED_TIME_THRESHOLD = ABANDON_TIME_THRESHOLD * 0.75
if ABANDONED_TIME_THRESHOLD_ALIAS is None:
    ABANDONED_TIME_THRESHOLD_ALIAS = ABANDON_TIME_THRESHOLD

# Vùng quan tâm ROI (Region of Interest)
# Đặt None = giám sát toàn bộ frame; hoặc list các điểm polygon [(x1,y1), (x2,y2), ...]
ROI_POLYGON = None

# Frame skip: Chỉ chạy YOLO detection mỗi N frame (các frame trung gian dùng kết quả trước)
DETECT_EVERY_N = 1  # Mặc định 1 = detect mọi frame; đặt 2-3 để tăng tốc

# Cấu hình màu sắc hiển thị (BGR for OpenCV)
COLOR_MOVING = (0, 220, 0)          # Xanh lá (Luggage đang di chuyển)
COLOR_STATIONARY = (0, 215, 255)    # Vàng nhạt (Luggage đứng yên nhưng có chủ ở gần)
COLOR_SUSPICIOUS = (0, 180, 255)    # Cam nhạt (Luggage nghi ngờ — cấp 1)
COLOR_UNATTENDED = (0, 120, 255)    # Cam đậm (Luggage không người trông — cấp 2)
COLOR_ABANDONED = (0, 0, 255)       # Đỏ tươi (Luggage bị bỏ quên - ALERT — cấp 3)
COLOR_PERSON = (255, 165, 0)        # Xanh da trời / Cam (Người)
COLOR_LINE = (255, 255, 0)          # Vàng chanh (Đường nối hành lý -> chủ)

# Thư mục xuất kết quả
OUTPUT_DIR = "output"
os.makedirs(OUTPUT_DIR, exist_ok=True)
