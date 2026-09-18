import os

# Đường dẫn mô hình YOLO đã huấn luyện
MODEL_PATH = "weights/best.pt"

# Danh sách lớp (Class IDs) từ mô hình
LUGGAGE_CLASS_ID = 0
PERSON_CLASS_ID = 1

CLASS_NAMES = {
    0: "luggage",
    1: "person"
}

# Ngưỡng phát hiện YOLO (Confidence & IOU)
CONF_THRESHOLD = 0.3
IOU_THRESHOLD = 0.50

TRACKER_TYPE = "bytetrack.yaml"  # Hoặc 'botsort.yaml'

# Các ngưỡng đánh giá Vật thể Bị bỏ quên
STATIONARY_MOVE_THRESHOLD = 25.0     # Khoảng cách tối đa (pixels) tâm hành lý di chuyển để coi là đứng yên
STATIONARY_HISTORY_FRAMES = 15      # Số frame lưu lại để tính độ ổn định vị trí
OWNER_DISTANCE_THRESHOLD = 180.0    # Khoảng cách tối đa (pixels) từ hành lý đến người gần nhất để tính là "có chủ"
ABANDON_TIME_THRESHOLD = 4.0        # Thời gian (giây) đứng yên không người để phát cảnh báo ABANDONED


# Cấu hình màu sắc hiển thị (BGR for OpenCV)
COLOR_MOVING = (0, 220, 0)          # Xanh lá (Luggage đang di chuyển)
COLOR_STATIONARY = (0, 215, 255)    # Vàng nhạt (Luggage đứng yên nhưng có chủ ở gần)
COLOR_ABANDONED = (0, 0, 255)       # Đỏ tươi (Luggage bị bỏ quên - ALERT)
COLOR_PERSON = (255, 165, 0)        # Xanh da trời / Cam (Người)
COLOR_LINE = (255, 255, 0)          # Vàng chanh (Đường nối hành lý -> chủ)

# Thư mục xuất kết quả
OUTPUT_DIR = "output"
os.makedirs(OUTPUT_DIR, exist_ok=True)
