import streamlit as st
import cv2
import tempfile
import time
import os
import pandas as pd
import numpy as np
from PIL import Image

import config
from core.detector import YOLODetector
from core.abandoned_detector import AbandonedObjectDetector
from core.visualizer import Visualizer

# Cấu hình Trang Streamlit
st.set_page_config(
    page_title="Hệ thống Phát hiện Vật thể Bị Bỏ Quên",
    page_icon="🎒",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS giao diện hiện đại
st.markdown("""
<style>
    .main-header {
        font-size: 2.3rem;
        font-weight: 700;
        color: #1E293B;
        text-align: center;
        margin-bottom: 0.5rem;
    }
    .sub-header {
        font-size: 1.1rem;
        color: #64748B;
        text-align: center;
        margin-bottom: 2rem;
    }
    .metric-card {
        background-color: #F8FAFC;
        border: 1px solid #E2E8F0;
        border-radius: 10px;
        padding: 15px;
        text-align: center;
    }
    .alert-banner {
        background-color: #FEE2E2;
        border-left: 5px solid #EF4444;
        color: #991B1B;
        padding: 12px;
        border-radius: 6px;
        font-weight: 600;
        margin-bottom: 10px;
    }
</style>
""", unsafe_allow_html=True)

st.markdown('<div class="main-header">🎒 HỆ THỐNG PHÁT HIỆN VẬT THỂ BỊ BỎ QUÊN</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-header">Đồ án môn học Thị giác Máy tính (Computer Vision) | Mô hình YOLO11 + Object Tracking</div>', unsafe_allow_html=True)

# SIDEBAR: Cấu hình Tham số
st.sidebar.header("⚙️ Cấu hình Tham số")

model_path = st.sidebar.text_input("Đường dẫn Model Weights", value=config.MODEL_PATH)
conf_thresh = st.sidebar.slider("Ngưỡng tin cậy (Confidence)", min_value=0.1, max_value=0.9, value=config.CONF_THRESHOLD, step=0.05)
abandon_time_thresh = st.sidebar.slider("Thời gian cảnh báo bỏ quên (Giây)", min_value=2.0, max_value=20.0, value=config.ABANDON_TIME_THRESHOLD, step=0.5)
owner_dist_thresh = st.sidebar.slider("Khoảng cách tối đa với chủ (Pixels)", min_value=50.0, max_value=500.0, value=config.OWNER_DISTANCE_THRESHOLD, step=10.0)

st.sidebar.markdown("---")
st.sidebar.subheader("📌 Trạng thái màu sắc nhãn")
st.sidebar.markdown("🟢 **MOVING**: Hành lý đang di chuyển")
st.sidebar.markdown("🟡 **STATIONARY**: Đứng yên nhưng có người ở gần")
st.sidebar.markdown("🔴 **ABANDONED**: Đứng yên không có chủ quá thời gian")

# BODY: Nguồn Video
uploaded_file = st.file_uploader("Tải lên File Video Giám sát (MP4, AVI, MOV)", type=["mp4", "avi", "mov", "mkv"])

# Nếu không upload file, kiểm tra xem có video test mặc định nào không
sample_video_path = "test_video.mp4"
use_sample = False
if uploaded_file is None and os.path.exists(sample_video_path):
    use_sample = st.checkbox(f"Hoặc dùng video mẫu sẵn có ({sample_video_path})", value=True)

if uploaded_file is not None or use_sample:
    if uploaded_file is not None:
        tfile = tempfile.NamedTemporaryFile(delete=False, suffix='.mp4')
        tfile.write(uploaded_file.read())
        video_input_path = tfile.name
    else:
        video_input_path = sample_video_path

    cap = cv2.VideoCapture(video_input_path)
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = cap.get(cv2.CAP_PROP_FPS)
    if fps <= 0 or np.isnan(fps):
        fps = 30.0
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    cap.release()

    col_info1, col_info2, col_info3 = st.columns(3)
    with col_info1:
        st.metric("Độ phân giải Video", f"{width} x {height}")
    with col_info2:
        st.metric("Tốc độ khung hình", f"{fps:.1f} FPS")
    with col_info3:
        st.metric("Tổng số khung hình", f"{total_frames} frames")

    if st.button("🚀 Bắt đầu Phân tích Video", type="primary", use_container_width=True):
        st.markdown("---")
        
        # Placeholders giao diện
        col_left, col_right = st.columns([2, 1])
        with col_left:
            st.subheader("🎥 Xem trực tiếp Phân tích Video")
            st_frame = st.empty()
            progress_bar = st.progress(0)
            status_text = st.empty()

        with col_right:
            st.subheader("🚨 Bảng Cảnh báo Thực tế")
            alert_placeholder = st.empty()
            st.subheader("📊 Thống kê Hệ thống")
            metric_col1, metric_col2 = st.columns(2)
            m_fps = metric_col1.empty()
            m_alerts = metric_col2.empty()

        # Khởi tạo mô hình
        try:
            detector = YOLODetector(model_path=model_path, conf_thresh=conf_thresh)
            abandon_engine = AbandonedObjectDetector(
                owner_dist_thresh=owner_dist_thresh,
                abandon_time_thresh=abandon_time_thresh
            )
            visualizer = Visualizer()
        except Exception as e:
            st.error(f"Lỗi khởi tạo mô hình YOLO: {e}")
            st.stop()

        cap = cv2.VideoCapture(video_input_path)
        output_video_path = os.path.join(config.OUTPUT_DIR, "web_output.mp4")
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        out_writer = cv2.VideoWriter(output_video_path, fourcc, fps, (width, height))

        frame_idx = 0
        all_alert_records = []
        start_time = time.time()

        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break

            frame_idx += 1
            frame_time = frame_idx / fps
            t0 = time.time()

            # Detect & Track & Abandon Logic
            luggage_dets, person_dets = detector.detect_and_track(frame)
            luggage_states, new_alerts = abandon_engine.process_frame(
                luggage_dets, person_dets, current_time=frame_time, fps=fps
            )

            for alert in new_alerts:
                all_alert_records.append({
                    'Frame': frame_idx,
                    'Thời gian (s)': round(frame_time, 2),
                    'Luggage ID': alert['luggage_id'],
                    'Bỏ quên (s)': round(alert['abandon_duration'], 2),
                    'Khoảng cách chủ (px)': round(alert['closest_person_dist'], 1)
                })

            proc_fps = 1.0 / max(time.time() - t0, 0.001)
            annotated_frame = visualizer.draw_frame(frame, luggage_states, person_dets, fps=proc_fps)
            out_writer.write(annotated_frame)

            # Cập nhật UI Streamlit mỗi vài frames để mượt
            if frame_idx % 2 == 0 or frame_idx == total_frames:
                frame_rgb = cv2.cvtColor(annotated_frame, cv2.COLOR_BGR2RGB)
                st_frame.image(frame_rgb, channels="RGB", use_container_width=True)
                
                progress_bar.progress(min(frame_idx / max(total_frames, 1), 1.0))
                status_text.text(f"Đã xử lý {frame_idx}/{total_frames} frames ({frame_idx/max(total_frames,1)*100:.1f}%)")

                m_fps.metric("Processing FPS", f"{proc_fps:.1f}")
                m_alerts.metric("Số Cảnh báo phát hiện", len(all_alert_records))

                if all_alert_records:
                    df_show = pd.DataFrame(all_alert_records).tail(5)
                    alert_placeholder.dataframe(df_show, use_container_width=True)
                else:
                    alert_placeholder.info("Chưa phát hiện vật thể bị bỏ quên nào.")

        cap.release()
        out_writer.release()
        total_proc_time = time.time() - start_time

        st.success(f"🎉 Hoàn thành xử lý trong {total_proc_time:.2f} giây!")

        # Xuất kết quả chi tiết
        st.markdown("---")
        st.subheader("📋 Kết quả Phân tích & Xuất dữ liệu")

        col_dl1, col_dl2 = st.columns(2)
        with col_dl1:
            if os.path.exists(output_video_path):
                with open(output_video_path, "rb") as file:
                    st.download_button(
                        label="📥 Tải xuống Video Kết quả (.mp4)",
                        data=file,
                        file_name="abandoned_object_output.mp4",
                        mime="video/mp4",
                        use_container_width=True
                    )

        with col_dl2:
            if all_alert_records:
                df_alerts = pd.DataFrame(all_alert_records)
                csv = df_alerts.to_csv(index=False).encode('utf-8')
                st.download_button(
                    label="📥 Tải xuống Nhật ký Cảnh báo CSV",
                    data=csv,
                    file_name="alert_log_report.csv",
                    mime="text/csv",
                    use_container_width=True
                )

        if all_alert_records:
            st.markdown("##### 📜 Danh sách Chi tiết Tất cả Cảnh báo:")
            st.dataframe(pd.DataFrame(all_alert_records), use_container_width=True)

else:
    st.info("👋 Vui lòng tải lên một file video giám sát ở trên để bắt đầu thử nghiệm hệ thống.")
