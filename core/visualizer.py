import cv2
import numpy as np
import time
import config

class Visualizer:
    def __init__(self):
        self.font = cv2.FONT_HERSHEY_SIMPLEX
        
    def draw_rounded_rect(self, img, pt1, pt2, color, thickness=1, r=10):
        """Vẽ khung hình chữ nhật bo góc góc mượt mà"""
        x1, y1 = int(pt1[0]), int(pt1[1])
        x2, y2 = int(pt2[0]), int(pt2[1])
        
        cv2.rectangle(img, (x1, y1), (x2, y2), color, thickness, cv2.LINE_AA)
        
    def draw_text_with_bg(self, img, text, pos, font_scale=0.5, text_color=(255, 255, 255), bg_color=(0, 0, 0), thickness=1, padding=4):
        """Vẽ văn bản có nền mờ phía sau giúp dễ đọc"""
        x, y = int(pos[0]), int(pos[1])
        (w, h), baseline = cv2.getTextSize(text, self.font, font_scale, thickness)
        
        # Nền phía sau chữ
        cv2.rectangle(img, (x, y - h - padding * 2), (x + w + padding * 2, y + baseline), bg_color, -1)
        # Chữ
        cv2.putText(img, text, (x + padding, y - padding), self.font, font_scale, text_color, thickness, cv2.LINE_AA)

    def draw_frame(self, frame, luggage_states, person_detections, fps=0.0):
        """
        Vẽ toàn bộ thông tin Bounding Box, Timer, HUD lên frame
        """
        annotated_frame = frame.copy()
        height, width = annotated_frame.shape[:2]
        
        # 1. Vẽ vị trí NGƯỜI (Person)
        for pid, pdata in person_detections.items():
            x1, y1, x2, y2 = pdata['bbox']
            label = f"Person #{pid}"
            
            # Vẽ Bounding Box người
            cv2.rectangle(annotated_frame, (int(x1), int(y1)), (int(x2), int(y2)), config.COLOR_PERSON, 2, cv2.LINE_AA)
            self.draw_text_with_bg(annotated_frame, label, (x1, y1 - 5), font_scale=0.5, bg_color=config.COLOR_PERSON)
            
            # Vẽ chấm vị trí chân người
            feet_x, feet_y = int((x1 + x2) / 2.0), int(y2)
            cv2.circle(annotated_frame, (feet_x, feet_y), 4, config.COLOR_PERSON, -1)

        # 2. Vẽ HÀNH LÝ (Luggage) và trạng thái
        has_active_abandon_alert = False
        abandoned_ids = []
        
        for tid, lug in luggage_states.items():
            x1, y1, x2, y2 = lug['bbox']
            state = lug['state']
            center = (int(lug['center'][0]), int(lug['center'][1]))
            
            # Chọn màu theo trạng thái
            if state == 'MOVING':
                color = config.COLOR_MOVING
                status_str = f"Luggage #{tid} | MOVING"
            elif state == 'STATIONARY_WITH_OWNER':
                color = config.COLOR_STATIONARY
                status_str = f"Luggage #{tid} | Static: {lug['static_timer']:.1f}s (With Owner)"
            elif state == 'STATIONARY_NO_OWNER':
                color = config.COLOR_STATIONARY
                status_str = f"Luggage #{tid} | Static: {lug['abandon_timer']:.1f}s / {config.ABANDON_TIME_THRESHOLD:.1f}s"
            elif state == 'ABANDONED':
                color = config.COLOR_ABANDONED
                status_str = f"ALERT! ABANDONED #{tid} | {lug['abandon_timer']:.1f}s"
                has_active_abandon_alert = True
                abandoned_ids.append(tid)
            else:
                color = config.COLOR_MOVING
                status_str = f"Luggage #{tid}"

            # Vẽ đường nối đến người ở gần nhất (nếu có)
            if lug.get('closest_person_id') is not None and lug['closest_person_id'] in person_detections:
                p_bbox = person_detections[lug['closest_person_id']]['bbox']
                p_feet = (int((p_bbox[0] + p_bbox[2]) / 2.0), int(p_bbox[3]))
                # Chỉ vẽ đường nối nếu người trong khoảng cách xem xét
                if lug['min_person_dist'] <= config.OWNER_DISTANCE_THRESHOLD * 1.5:
                    line_color = config.COLOR_LINE if lug.get('has_owner') else (128, 128, 128)
                    cv2.line(annotated_frame, center, p_feet, line_color, 1, cv2.LINE_AA)
                    # Ghi khoảng cách
                    mid_x = (center[0] + p_feet[0]) // 2
                    mid_y = (center[1] + p_feet[1]) // 2
                    cv2.putText(annotated_frame, f"{int(lug['min_person_dist'])}px", (mid_x, mid_y), 
                                self.font, 0.4, line_color, 1, cv2.LINE_AA)

            # Vẽ Bounding box cho Luggage
            thickness = 3 if state == 'ABANDONED' else 2
            cv2.rectangle(annotated_frame, (int(x1), int(y1)), (int(x2), int(y2)), color, thickness, cv2.LINE_AA)
            cv2.circle(annotated_frame, center, 4, color, -1)
            
            # Vẽ nhãn thông tin
            self.draw_text_with_bg(annotated_frame, status_str, (x1, y1 - 5), font_scale=0.5, bg_color=color)

        # 3. Vẽ Banner Cảnh báo Đỏ Nhấp Nháy nếu có Vật thể Bị bỏ quên
        if has_active_abandon_alert:
            # Tạo màu nhấp nháy theo thời gian
            blink = int(time.time() * 5) % 2 == 0
            banner_bg = (0, 0, 220) if blink else (0, 0, 150)
            
            cv2.rectangle(annotated_frame, (0, 0), (width, 45), banner_bg, -1)
            alert_msg = f"WARNING: ABANDONED LUGGAGE DETECTED! ID: {abandoned_ids}"
            (tw, th), _ = cv2.getTextSize(alert_msg, self.font, 0.7, 2)
            text_x = (width - tw) // 2
            cv2.putText(annotated_frame, alert_msg, (text_x, 30), self.font, 0.7, (255, 255, 255), 2, cv2.LINE_AA)

        # 4. Vẽ Bảng thông số HUD Overlay (Top-Left)
        hud_bg = np.zeros((90, 240, 3), dtype=np.uint8)
        hud_overlay = annotated_frame[10:100, 10:250].copy()
        cv2.addWeighted(hud_bg, 0.6, hud_overlay, 0.4, 0, hud_overlay)
        annotated_frame[10:100, 10:250] = hud_overlay
        
        cv2.rectangle(annotated_frame, (10, 10), (250, 100), (200, 200, 200), 1, cv2.LINE_AA)
        cv2.putText(annotated_frame, "ABANDONED OBJECT DETECTOR", (18, 30), self.font, 0.45, (0, 255, 255), 1, cv2.LINE_AA)
        cv2.putText(annotated_frame, f"FPS: {fps:.1f}", (18, 50), self.font, 0.4, (255, 255, 255), 1, cv2.LINE_AA)
        cv2.putText(annotated_frame, f"Luggage: {len(luggage_states)} | Person: {len(person_detections)}", (18, 70), self.font, 0.4, (255, 255, 255), 1, cv2.LINE_AA)
        
        status_color = (0, 0, 255) if has_active_abandon_alert else (0, 255, 0)
        status_text = "STATUS: ALERT!" if has_active_abandon_alert else "STATUS: NORMAL"
        cv2.putText(annotated_frame, status_text, (18, 90), self.font, 0.4, status_color, 1, cv2.LINE_AA)

        return annotated_frame
