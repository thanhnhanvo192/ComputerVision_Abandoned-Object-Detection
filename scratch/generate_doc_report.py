import os
import docx
from docx import Document
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml import OxmlElement, parse_xml
from docx.oxml.ns import nsdecls, qn

def set_cell_background(cell, fill_hex):
    """Đặt màu nền cho cell trong table"""
    tcPr = cell._tc.get_or_add_tcPr()
    shd = parse_xml(f'<w:shd {nsdecls("w")} w:fill="{fill_hex}"/>')
    tcPr.append(shd)

def set_cell_margins(cell, top=100, bottom=100, left=150, right=150):
    """Đặt padding cho cell (đơn vị dxa, 1 pt = 20 dxa)"""
    tcPr = cell._tc.get_or_add_tcPr()
    tcMar = parse_xml(
        f'<w:tcMar {nsdecls("w")}>'
        f'<w:top w:w="{top}" w:type="dxa"/>'
        f'<w:bottom w:w="{bottom}" w:type="dxa"/>'
        f'<w:left w:w="{left}" w:type="dxa"/>'
        f'<w:right w:w="{right}" w:type="dxa"/>'
        f'</w:tcMar>'
    )
    tcPr.append(tcMar)

def add_callout(doc, text, title="GHI CHÚ QUAN TRỌNG", color_hex="1E40AF", bg_hex="EFF6FF"):
    """Tạo hộp thông tin (Callout Box) nổi bật"""
    tbl = doc.add_table(rows=1, cols=1)
    tbl.alignment = WD_TABLE_ALIGNMENT.CENTER
    cell = tbl.cell(0, 0)
    set_cell_background(cell, bg_hex)
    set_cell_margins(cell, top=140, bottom=140, left=200, right=200)
    
    # Border trái đậm, các border khác không có
    tcPr = cell._tc.get_or_add_tcPr()
    borders = parse_xml(
        f'<w:tcBorders {nsdecls("w")}>'
        f'<w:left w:val="single" w:sz="24" w:space="0" w:color="{color_hex}"/>'
        f'<w:top w:val="none"/>'
        f'<w:right w:val="none"/>'
        f'<w:bottom w:val="none"/>'
        f'</w:tcBorders>'
    )
    tcPr.append(borders)
    
    p = cell.paragraphs[0]
    p.paragraph_format.space_before = Pt(2)
    p.paragraph_format.space_after = Pt(2)
    p.paragraph_format.line_spacing = 1.15
    run_title = p.add_run(f"📌 {title}: ")
    run_title.bold = True
    run_title.font.name = "Arial"
    run_title.font.size = Pt(10)
    run_title.font.color.rgb = RGBColor(0x1E, 0x40, 0xAF)
    
    run_text = p.add_run(text)
    run_text.font.name = "Arial"
    run_text.font.size = Pt(10)
    run_text.font.color.rgb = RGBColor(0x1E, 0x29, 0x3B)
    
    doc.add_paragraph().paragraph_format.space_after = Pt(4)

def build_report():
    doc = Document()
    
    # Thiết lập lề trang chuẩn (1 inch = 2.54 cm)
    for section in doc.sections:
        section.top_margin = Inches(1)
        section.bottom_margin = Inches(1)
        section.left_margin = Inches(1)
        section.right_margin = Inches(1)
    
    # Thiết lập default font
    style_normal = doc.styles['Normal']
    font = style_normal.font
    font.name = 'Times New Roman'
    font.size = Pt(11.5)
    font.color.rgb = RGBColor(0x1F, 0x29, 0x37)
    
    # -------------------------------------------------------------------------
    # TIÊU ĐỀ BÁO CÁO
    # -------------------------------------------------------------------------
    p_meta = doc.add_paragraph()
    p_meta.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r_sub = p_meta.add_run("BỘ MÔN THỊ GIÁC MÁY TÍNH (COMPUTER VISION) — HỌC KỲ 7\n")
    r_sub.font.name = "Arial"
    r_sub.font.size = Pt(10)
    r_sub.font.color.rgb = RGBColor(0x64, 0x74, 0x8B)
    r_sub.bold = True
    
    p_title = doc.add_paragraph()
    p_title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_title.paragraph_format.space_before = Pt(4)
    p_title.paragraph_format.space_after = Pt(8)
    r_title = p_title.add_run("BÁO CÁO CẢI TIẾN KỸ THUẬT VÀ TỐI ƯU MÃ NGUỒN")
    r_title.font.name = "Arial"
    r_title.font.size = Pt(18)
    r_title.bold = True
    r_title.font.color.rgb = RGBColor(0x0F, 0x17, 0x2A)
    
    p_desc = doc.add_paragraph()
    p_desc.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_desc.paragraph_format.space_after = Pt(18)
    r_desc = p_desc.add_run("Đề tài: Hệ Thống Phát Hiện Vật Thể Bị Bỏ Quên Trong Video Giám Sát\n(Abandoned Object Detection System using YOLO11 & Object Tracking)")
    r_desc.font.name = "Arial"
    r_desc.font.size = Pt(12)
    r_desc.font.italic = True
    r_desc.font.color.rgb = RGBColor(0x25, 0x63, 0xEB)
    
    # Đường kẻ ngang phân cách
    p_line = doc.add_paragraph()
    p_line.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_line.paragraph_format.space_after = Pt(14)
    r_line = p_line.add_run("—" * 45)
    r_line.font.color.rgb = RGBColor(0xCB, 0xD5, 0xE1)
    
    # -------------------------------------------------------------------------
    # 1. TỔNG QUAN VÀ ĐỘNG LỰC CẢI TIẾN
    # -------------------------------------------------------------------------
    h1 = doc.add_heading("1. TỔNG QUAN VÀ ĐỘNG LỰC CẢI TIẾN", level=1)
    h1.paragraph_format.space_before = Pt(12)
    h1.paragraph_format.space_after = Pt(6)
    
    doc.add_paragraph(
        "Hệ thống phát hiện vật thể bị bỏ quên (Abandoned Luggage/Object Detection) là một bài toán trọng điểm trong giám sát an ninh tại sân bay, nhà ga và trung tâm thương mại. Phiên bản mã nguồn ban đầu của dự án đã bước đầu tích hợp mô hình YOLO11n và thuật toán theo dõi đối tượng ByteTrack. Tuy nhiên, qua quá trình rà soát và đánh giá kỹ thuật chuyên sâu, hệ thống tồn tại các hạn chế nghiêm trọng về tính chính xác thuật toán, trải nghiệm người dùng và tính ổn định phần mềm."
    )
    
    doc.add_paragraph(
        "Báo cáo này trình bày toàn bộ các nội dung nghiên cứu, thiết kế lại và triển khai cải tiến toàn diện trên hệ thống, bao gồm 4 trụ cột chính: (1) Thuật toán cốt lõi, (2) Kiến trúc phần mềm & Hiệu năng, (3) Mô hình học máy & Dữ liệu, và (4) Khắc phục lỗi & Trải nghiệm giao diện người dùng."
    )
    
    # -------------------------------------------------------------------------
    # 2. PHÂN TÍCH HẠN CHẾ CỦA MÃ NGUỒN CŨ
    # -------------------------------------------------------------------------
    h2 = doc.add_heading("2. PHÂN TÍCH CÁC HẠN CHẾ CỦA MÃ NGUỒN CŨ", level=1)
    h2.paragraph_format.space_before = Pt(14)
    h2.paragraph_format.space_after = Pt(6)
    
    issues = [
        ("Khoảng cách xác định chủ sở hữu tĩnh (Fixed Pixel Distance)", 
         "Hệ thống cũ quy định OWNER_DISTANCE_THRESHOLD = 150px cố định. Khi người đứng ở xa camera, kích thước toàn thân chỉ khoảng 40-60px nhưng khoảng cách 150px lại bao phủ một vùng không gian quá rộng. Ngược lại khi người ở cận cảnh (chiều cao 300px), 150px lại quá nhỏ. Điều này dẫn tới tỷ lệ báo động giả (False Positive) và bỏ sót (False Negative) rất cao do vi phạm phối cảnh hình học 3D sang 2D."),
        ("Hiện tượng reset timer sai do người lạ đi ngang qua (Thiếu Owner Memory)", 
         "Trong mã nguồn cũ, hàm xác định chủ sở hữu chỉ đơn thuần tìm người gần nhất ở frame hiện tại (min_dist <= 150px). Khi một hành lý đã bị chủ thực sự bỏ lại, bất kỳ khách bộ hành nào tình cờ đi lướt qua gần hành lý cũng khiến bộ đếm abandon_timer bị reset về 0, làm hệ thống thất bại trong việc phát hiện bỏ quên."),
        ("Ghép nối vết theo dõi (Track Matching) thiếu tin cậy khi mất ID", 
         "Cơ chế Spatial Matching cũ chỉ dựa vào khoảng cách tâm Euclidean (< 60px). Khi nhiều vật thể hoặc người qua lại gần nhau, việc chỉ so sánh tâm mà không xét độ trùng khớp khung bao (IoU) khiến hệ thống dễ gán nhầm vết theo dõi."),
        ("Cơ chế cảnh báo nhị phân đơn điệu (Binary Alert)", 
         "Hệ thống chỉ có 2 trạng thái: bình thường hoặc ABANDONED (khi quá 4 giây). Thiếu các cấp độ cảnh báo trung gian (Cảnh báo nghi ngờ, Không người trông coi) để nhân viên an ninh có thời gian chủ động phản ứng trước khi sự cố chuyển sang mức nghiêm trọng."),
        ("Lỗi thụt đầu dòng (Indentation Bug) làm tê liệt chức năng Upload trên Web GUI", 
         "Trong tệp app_gui.py (dòng 84-91), khối mã xử lý file người dùng tải lên bị thụt vào bên trong nhánh 'if uploaded_file is None'. Hậu quả là người dùng tải file lên nhưng hệ thống luôn nhận định là chưa tải và không thể phân tích video của người dùng."),
        ("Trùng lặp mã nguồn (Code Duplication) giữa CLI và GUI", 
         "Cả hai tệp main.py và app_gui.py đều tự viết lại vòng lặp đọc frame, gọi model, cập nhật timer và visualizer. Khi thay đổi thuật toán ở một bên thì bên còn lại bị phân rã, không đồng nhất."),
        ("Cấu hình huấn luyện mô hình YOLO sơ sài", 
         "Tệp cấu hình huấn luyện args.yaml chỉ train 50 epochs, không kích hoạt Cosine Learning Rate Schedule, tắt hoàn toàn MixUp và Copy-Paste Augmentation dẫn đến mô hình khái quát hóa kém trên các góc máy giám sát thực tế.")
    ]
    
    for title, desc in issues:
        p = doc.add_paragraph()
        p.paragraph_format.left_indent = Inches(0.2)
        p.paragraph_format.space_after = Pt(4)
        run_b = p.add_run(f"• {title}: ")
        run_b.bold = True
        run_b.font.color.rgb = RGBColor(0x99, 0x1B, 0x1B)
        p.add_run(desc)
        
    add_callout(
        doc,
        "Lỗi indentation trong tệp app_gui.py là lỗi nghiêm trọng (Critical Bug) khiến giao diện web không thể sử dụng được với video tùy chỉnh. Việc phát hiện và tái cấu trúc lại luồng xử lý đầu vào là một cải tiến thiết yếu.",
        title="ĐÁNH GIÁ MỨC ĐỘ ẢNH HƯỞNG",
        color_hex="DC2626",
        bg_hex="FEF2F2"
    )

    # -------------------------------------------------------------------------
    # 3. CHI TIẾT CÁC CẢI TIẾN KỸ THUẬT ĐÃ THỰC HIỆN
    # -------------------------------------------------------------------------
    h3 = doc.add_heading("3. CHI TIẾT CÁC CẢI TIẾN KỸ THUẬT ĐÃ TRIỂN KHAI", level=1)
    h3.paragraph_format.space_before = Pt(14)
    h3.paragraph_format.space_after = Pt(6)

    # 3.1
    h3_1 = doc.add_heading("3.1. Thuật toán Ngưỡng Khoảng Cách Thích Ứng (Adaptive Distance Threshold)", level=2)
    doc.add_paragraph(
        "Thay vì áp dụng ngưỡng pixel cố định 150px, hệ thống mới tự động tính toán ngưỡng khoảng cách tối đa giữa hành lý và chủ sở hữu dựa trên tỷ lệ chiều cao khung bao (bounding box) của chính người đó:"
    )
    
    # Formula box
    p_fm = doc.add_paragraph()
    p_fm.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r_fm = p_fm.add_run("Threshold_Adaptive = max( 1.2 × Person_Height,  80.0 px )")
    r_fm.bold = True
    r_fm.font.name = "Consolas"
    r_fm.font.size = Pt(11)
    r_fm.font.color.rgb = RGBColor(0x1E, 0x40, 0xAF)
    
    doc.add_paragraph(
        "• Ý nghĩa vật lý: Chiều cao bounding box của người phản ánh chân thực độ sâu (depth) và phối cảnh góc nhìn của camera. Người ở xa camera có bbox nhỏ → ngưỡng nhỏ tương ứng. Người ở gần camera có bbox lớn → ngưỡng rộng hơn tự nhiên.\n"
        "• Giá trị sàn 80px: Đảm bảo không bị ngưỡng quá hẹp khi người ngồi hoặc bị che khuất một phần (occlusion)."
    )

    # 3.2
    h3_2 = doc.add_heading("3.2. Cơ chế Bộ Nhớ Ghi Nhớ Chủ Sở Hữu (Original Owner Memory)", level=2)
    doc.add_paragraph(
        "Khắc phục hoàn toàn bài toán 'người lạ đi lướt qua làm reset cảnh báo':"
    )
    doc.add_paragraph(
        "1. Ghi nhận chủ ban đầu: Khi hành lý lần đầu tiên xuất hiện cùng người đi kèm (hoặc khi người đặt hành lý xuống sàn), ID của người đó được lưu vào trường 'original_owner_id' trong cấu trúc theo dõi của hành lý.\n"
        "2. Kiểm tra ưu tiên: Trong các frame tiếp theo, hệ thống ưu tiên đo khoảng cách tới chính chủ nhân ban đầu này. Dù có khách bộ hành khác tiến vào bán kính gần hành lý, hệ thống vẫn nhận biết chủ nhân thực sự đã rời đi và tiếp tục duy trì bộ đếm thời gian bỏ quên.\n"
        "3. Tự động giải phóng: Khi hành lý được người di chuyển đi nơi khác (trạng thái chuyển sang MOVING), bộ nhớ chủ sở hữu sẽ được cập nhật lại tương ứng với người mới xách nó."
    )

    # 3.3
    h3_3 = doc.add_heading("3.3. Ghép Nối Vết Không Gian Đa Tiêu Chí (IoU & Spatial Matching)", level=2)
    doc.add_paragraph(
        "Bổ sung hàm tính chỉ số giao trên hợp _compute_iou(box1, box2). Khi YOLO hoặc ByteTrack bị mất track_id do người đi ngang qua che khuất (occlusion), hệ thống so khớp detection mới với các vật thể tĩnh trong bộ nhớ bằng điều kiện kép:"
    )
    p_fm2 = doc.add_paragraph()
    p_fm2.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r_fm2 = p_fm2.add_run("Match_Condition = ( Distance(Center1, Center2) < 60px )  HOẶC  ( IoU(Box1, Box2) > 0.30 )")
    r_fm2.bold = True
    r_fm2.font.name = "Consolas"
    r_fm2.font.size = Pt(11)
    r_fm2.font.color.rgb = RGBColor(0x1E, 0x40, 0xAF)
    doc.add_paragraph(
        "Giải pháp này giúp hệ thống giữ vững bộ đếm timer liên tục mà không bị gián đoạn hay tạo ra các ID mới trùng lặp khi xảy ra che khuất ngắn hạn."
    )

    # 3.4
    h3_4 = doc.add_heading("3.4. Hệ Thống Phân Cấp Cảnh Báo Đa Tầng (Multi-Level Alert System)", level=2)
    doc.add_paragraph(
        "Thay đổi từ cơ chế nhị phân thành quy trình cảnh báo 3 cấp độ leo thang theo thời gian thực tế:"
    )
    
    # Bảng phân cấp
    tbl_alert = doc.add_table(rows=4, cols=4)
    tbl_alert.alignment = WD_TABLE_ALIGNMENT.CENTER
    headers = ["Cấp độ", "Thời gian không chủ", "Màu hiển thị", "Hành động & Ý nghĩa"]
    for i, h in enumerate(headers):
        cell = tbl_alert.cell(0, i)
        cell.paragraphs[0].text = h
        cell.paragraphs[0].runs[0].bold = True
        cell.paragraphs[0].runs[0].font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)
        set_cell_background(cell, "1E3A8A")
        set_cell_margins(cell, top=120, bottom=120, left=140, right=140)
        
    data_alerts = [
        ("Cấp 1: SUSPICIOUS (Nghi ngờ)", ">= 2.0 giây", "Cam nhạt (Amber)", "Hiển thị nhãn cảnh báo vàng trên HUD; đưa vật thể vào diện theo dõi trọng điểm."),
        ("Cấp 2: UNATTENDED (Không người trông)", ">= 3.0 giây", "Cam đậm (Orange)", "Banner cảnh báo nổi góc trên khung hình; ghi nhận nhật ký hệ thống."),
        ("Cấp 3: ABANDONED (Bị bỏ quên)", ">= 4.0 giây (hoặc cấu hình)", "Đỏ tươi (Red)", "Kích hoạt còi/banner nhấp nháy khẩn cấp; xuất sự kiện cảnh báo chính thức vào file CSV/JSON.")
    ]
    
    for row_idx, row_data in enumerate(data_alerts, start=1):
        bg = "F8FAFC" if row_idx % 2 == 1 else "FFFFFF"
        for col_idx, val in enumerate(row_data):
            cell = tbl_alert.cell(row_idx, col_idx)
            cell.paragraphs[0].text = val
            set_cell_background(cell, bg)
            set_cell_margins(cell, top=100, bottom=100, left=140, right=140)
            
    doc.add_paragraph().paragraph_format.space_after = Pt(4)

    # 3.5
    h3_5 = doc.add_heading("3.5. Thiết Lập Vùng Quan Tâm (Region of Interest - ROI)", level=2)
    doc.add_paragraph(
        "Bổ sung cấu hình ROI_POLYGON trong config.py và tích hợp thuật toán kiểm tra đa giác cv2.pointPolygonTest(). Hệ thống cho phép thiết lập giám sát khu vực trọng điểm (ví dụ: khu vực cửa ra vào sân bay, trước quầy vé) và loại bỏ hoàn toàn các vật thể nằm ngoài phạm vi quan tâm, giảm tải tính toán và loại bỏ nhiễu biên."
    )

    # 3.6
    h3_6 = doc.add_heading("3.6. Tái Cấu Trúc Kiến Trúc: Đóng Gói VideoPipeline (Design Pattern)", level=2)
    doc.add_paragraph(
        "Tạo mới tệp core/pipeline.py tuân thủ nguyên lý DRY (Don't Repeat Yourself). Lớp VideoPipeline đóng gói toàn bộ chu trình xử lý: Nhận frame → YOLO Tracking → Logic Phân tích Bỏ quên → Vẽ đồ họa Visualizer. Cả hai ứng dụng main.py (CLI) và app_gui.py (Streamlit) đều có thể tái sử dụng một đường ống duy nhất, giúp mã nguồn nhất quán, dễ kiểm thử đơn vị (Unit Test) và dễ bảo trì."
    )

    # 3.7
    h3_7 = doc.add_heading("3.7. Cải Thiện Bộ Tham Số Huấn Luyện YOLO (args.yaml)", level=2)
    doc.add_paragraph(
        "Nâng cấp cấu hình huấn luyện mô hình YOLO11 phát hiện hành lý và con người:"
    )
    doc.add_paragraph(
        "• Tăng số lượng epoch: Từ 50 lên 150 epochs, cho phép mạng nơ-ron hội tụ sâu hơn trên tập dữ liệu đặc thù.\n"
        "• Kích hoạt Cosine Annealing Learning Rate (cos_lr: true): Giúp tốc độ học giảm dần theo hàm cosin mượt mà, tránh bị kẹt tại cực tiểu địa phương.\n"
        "• Tăng cường dữ liệu mạnh mẽ (Data Augmentation): Bật MixUp (0.15) và Copy-Paste (0.10) giúp mô hình có khả năng nhận diện các trường hợp hành lý bị người đứng che khuất một nửa.\n"
        "• Tắt Mosaic ở 15 epoch cuối (close_mosaic: 15): Giúp mô hình ổn định trọng số trên ảnh thực tế nguyên bản trước khi xuất bản bản checkpoint tối ưu."
    )

    # 3.8
    h3_8 = doc.add_heading("3.8. Sửa Lỗi Nghiêm Trọng và Nâng Cấp Giao Diện Streamlit", level=2)
    doc.add_paragraph(
        "• Khắc phục hoàn toàn lỗi thụt đầu dòng (indentation bug) tại tệp app_gui.py, cho phép nhận diện và xử lý mọi file video người dùng kéo thả tải lên.\n"
        "• Bổ sung tính năng chọn nhanh danh sách video mẫu (video1, video2, pets2006,...) ngay trên giao diện web thông qua dropdown menu tiện lợi.\n"
        "• Sửa lỗi tiềm ẩn tràn khung HUD trong core/visualizer.py (kiểm tra kích thước frame >= 260x110px trước khi phủ lớp bán trong suốt).\n"
        "• Chuẩn hóa hàm kiểm tra fps NaN bằng thư viện chuẩn math.isnan()."
    )

    # -------------------------------------------------------------------------
    # 4. BẢNG SO SÁNH TRƯỚC VÀ SAU CẢI TIẾN
    # -------------------------------------------------------------------------
    h4 = doc.add_heading("4. BẢNG TỔNG HỢP SO SÁNH TRƯỚC VÀ SAU CẢI TIẾN", level=1)
    h4.paragraph_format.space_before = Pt(14)
    h4.paragraph_format.space_after = Pt(6)

    tbl_comp = doc.add_table(rows=10, cols=3)
    tbl_comp.alignment = WD_TABLE_ALIGNMENT.CENTER
    comp_headers = ["Hạng mục so sánh", "Phiên bản cũ (Trước cải tiến)", "Phiên bản mới (Sau cải tiến)"]
    for i, h in enumerate(comp_headers):
        cell = tbl_comp.cell(0, i)
        cell.paragraphs[0].text = h
        cell.paragraphs[0].runs[0].bold = True
        cell.paragraphs[0].runs[0].font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)
        set_cell_background(cell, "0F172A")
        set_cell_margins(cell, top=120, bottom=120, left=140, right=140)

    comparisons = [
        ("Xác định khoảng cách chủ", "Cố định 150 pixels (bất kể phối cảnh gần/xa).", "Tự thích ứng theo chiều cao người: max(1.2×H, 80px)."),
        ("Khả năng nhận diện chủ nhân", "Chỉ xét người gần nhất ở frame hiện tại; dễ bị người lạ đi ngang làm reset timer.", "Ghi nhớ chủ nhân ban đầu (Owner Memory); người lạ đi qua không làm gián đoạn timer."),
        ("Phương thức ghép track", "Chỉ so khoảng cách Euclidean tâm (< 60px).", "Kết hợp khoảng cách Euclidean tâm + IoU Bounding Box (> 0.30)."),
        ("Cơ chế cảnh báo", "Nhị phân (chỉ có Normal hoặc Abandoned).", "3 cấp độ leo thang: Nghi ngờ (2s) → Không người trông (3s) → Bị bỏ quên (4s)."),
        ("Hỗ trợ vùng giám sát", "Không có; xử lý toàn bộ khung hình.", "Tích hợp ROI Polygon; loại bỏ các vật thể ngoài khu vực giám sát."),
        ("Kiến trúc mã nguồn", "Trùng lặp mã nguồn giữa main.py và app_gui.py.", "Tách module VideoPipeline dùng chung, hỗ trợ Dataclass và Type Hints."),
        ("Xuất báo cáo kết quả", "Chỉ xuất file CSV danh sách alert cơ bản.", "Xuất đồng thời CSV và JSON metadata đầy đủ (cấu hình, thống kê, cảnh báo)."),
        ("Trạng thái Streamlit Web GUI", "Bị lỗi thụt lề, không thể phân tích file video upload.", "Đã khắc phục hoàn toàn; hỗ trợ tải file hoặc chọn video mẫu có sẵn."),
        ("Cấu hình huấn luyện mô hình", "50 epochs, LR tĩnh, không Augmentation mạnh.", "150 epochs, Cosine LR, MixUp (0.15), Copy-Paste (0.10), Close Mosaic (15).")
    ]

    for row_idx, (col0, col1, col2) in enumerate(comparisons, start=1):
        bg = "F1F5F9" if row_idx % 2 == 1 else "FFFFFF"
        cell0 = tbl_comp.cell(row_idx, 0)
        cell1 = tbl_comp.cell(row_idx, 1)
        cell2 = tbl_comp.cell(row_idx, 2)
        
        cell0.paragraphs[0].text = col0
        cell0.paragraphs[0].runs[0].bold = True
        cell1.paragraphs[0].text = col1
        cell2.paragraphs[0].text = col2
        cell2.paragraphs[0].runs[0].font.color.rgb = RGBColor(0x15, 0x80, 0x3D)
        cell2.paragraphs[0].runs[0].bold = True
        
        for c in (cell0, cell1, cell2):
            set_cell_background(c, bg)
            set_cell_margins(c, top=80, bottom=80, left=120, right=120)

    doc.add_paragraph().paragraph_format.space_after = Pt(8)

    # -------------------------------------------------------------------------
    # 5. KẾT LUẬN VÀ HƯỚNG PHÁT TRIỂN
    # -------------------------------------------------------------------------
    h5 = doc.add_heading("5. KẾT LUẬN VÀ HƯỚNG PHÁT TRIỂN TIẾP THEO", level=1)
    h5.paragraph_format.space_before = Pt(14)
    h5.paragraph_format.space_after = Pt(6)

    doc.add_paragraph(
        "Thông qua các cải tiến kỹ thuật trên, hệ thống Phát hiện Vật thể Bị Bỏ Quên đã giải quyết triệt để các lỗ hổng logic nghiêm trọng của phiên bản cũ, đặc biệt là hiện tượng báo động giả và khả năng kháng nhiễu khi có người lạ di chuyển trong khung hình. Kiến trúc mã nguồn được quy hoạch khoa học, đạt chuẩn chất lượng đồ án tốt nghiệp/nghiên cứu môn học Thị giác máy tính."
    )
    doc.add_paragraph(
        "Các hướng mở rộng tiềm năng trong tương lai bao gồm:\n"
        "• Tích hợp Re-Identification (ReID): Trích xuất vector đặc trưng ngoại hình (appearance embeddings) của người để nhận diện lại chủ nhân chính xác tuyệt đối ngay cả khi họ khuất khỏi camera một thời gian dài rồi quay lại.\n"
        "• Ước lượng tư thế người (YOLO-Pose): Phân tích hành động cúi người đặt túi xách hoặc buông tay khỏi quai vali để kích hoạt mốc thời gian bỏ quên tức thì thay vì chờ đếm số frame đứng yên.\n"
        "• Triển khai biên (Edge AI): Tối ưu mô hình với TensorRT hoặc OpenVINO để chạy thời gian thực trên các thiết bị nhúng như NVIDIA Jetson Orin."
    )
    
    # Ký tên / Ngày lập
    p_sign = doc.add_paragraph()
    p_sign.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    p_sign.paragraph_format.space_before = Pt(24)
    r_date = p_sign.add_run("Báo cáo được hoàn thành vào ngày 02 tháng 11 năm 2026\n")
    r_date.font.italic = True
    r_sign = p_sign.add_run("NHÓM PHÁT TRIỂN DỰ ÁN THỊ GIÁC MÁY TÍNH")
    r_sign.bold = True
    
    output_docx_path = r"d:\Semester7\ComputerVision\project\Bao_Cao_Cai_Tien_Ky_Thuat.docx"
    doc.save(output_docx_path)
    print(f"[OK] File Word bao cao da duoc luu thanh cong tai: {output_docx_path}")

if __name__ == "__main__":
    build_report()
