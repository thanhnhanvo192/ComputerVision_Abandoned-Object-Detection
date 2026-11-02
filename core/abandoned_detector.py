import time
import math
import cv2
import numpy as np
from collections import deque
from dataclasses import dataclass, field
from typing import Dict, List, Tuple, Optional, Any
import config


@dataclass
class Detection:
    """Cấu trúc dữ liệu cho một detection từ YOLO"""
    track_id: int
    bbox: Tuple[float, float, float, float]  # x1, y1, x2, y2
    center: Tuple[float, float]
    conf: float
    class_id: int


class AbandonedObjectDetector:
    def __init__(self, 
                 move_thresh=config.STATIONARY_MOVE_THRESHOLD,
                 owner_dist_thresh=config.OWNER_DISTANCE_THRESHOLD,
                 abandon_time_thresh=config.ABANDON_TIME_THRESHOLD,
                 suspicious_time_thresh=config.SUSPICIOUS_TIME_THRESHOLD,
                 unattended_time_thresh=config.UNATTENDED_TIME_THRESHOLD,
                 min_static_confirm_sec=1.0,
                 max_missing_sec=30.0):
        """
        Khởi tạo Bộ phân tích phát hiện vật thể bị bỏ quên nâng cao.
        
        Cải tiến v2:
        - Adaptive Distance Threshold: Tự thích ứng ngưỡng khoảng cách theo kích thước người
        - Owner Memory: Ghi nhớ chủ sở hữu ban đầu của hành lý
        - IoU Spatial Matching: Kết hợp IoU để ghép nối track chính xác hơn
        - Multi-level Alerts: 3 cấp cảnh báo (SUSPICIOUS → UNATTENDED → ABANDONED)
        - ROI Support: Chỉ giám sát vùng quan tâm được chỉ định
        - Smart Static Lock Memory: Chỉ khóa vị trí bộ nhớ khi balo đứng yên thực sự
        """
        self.move_thresh = move_thresh
        self.owner_dist_thresh = owner_dist_thresh
        self.abandon_time_thresh = abandon_time_thresh
        self.suspicious_time_thresh = suspicious_time_thresh
        self.unattended_time_thresh = unattended_time_thresh
        self.min_static_confirm_sec = min_static_confirm_sec
        self.max_missing_sec = max_missing_sec
        
        self.luggage_tracks = {}
        self.alert_history = []
        
    def reset(self):
        """Xóa sạch lịch sử theo dõi"""
        self.luggage_tracks.clear()
        self.alert_history.clear()
    
    # ========================================================================
    # Các hàm tính toán khoảng cách và geometry
    # ========================================================================
        
    def _compute_distance(self, p1, p2):
        """Tính khoảng cách Euclidean giữa 2 điểm (x1, y1) và (x2, y2)"""
        return math.sqrt((p1[0] - p2[0])**2 + (p1[1] - p2[1])**2)
    
    def _compute_iou(self, box1, box2):
        """Tính IoU (Intersection over Union) giữa 2 bounding box [x1, y1, x2, y2]"""
        x1 = max(box1[0], box2[0])
        y1 = max(box1[1], box2[1])
        x2 = min(box1[2], box2[2])
        y2 = min(box1[3], box2[3])
        
        inter = max(0, x2 - x1) * max(0, y2 - y1)
        area1 = (box1[2] - box1[0]) * (box1[3] - box1[1])
        area2 = (box2[2] - box2[0]) * (box2[3] - box2[1])
        union = area1 + area2 - inter
        
        return inter / max(union, 1e-6)
        
    def _compute_person_distance(self, luggage_center, person_bbox):
        """
        Tính khoảng cách từ tâm hành lý đến vị trí người.
        Ưu tiên tính với chân người (bottom-center) và tâm người, lấy min.
        """
        px1, py1, px2, py2 = person_bbox
        feet_pos = ((px1 + px2) / 2.0, py2)
        center_pos = ((px1 + px2) / 2.0, (py1 + py2) / 2.0)
        
        dist_feet = self._compute_distance(luggage_center, feet_pos)
        dist_center = self._compute_distance(luggage_center, center_pos)
        
        return min(dist_feet, dist_center)
    
    def _compute_adaptive_threshold(self, person_bbox):
        """
        Tính ngưỡng khoảng cách tự thích ứng dựa trên kích thước bounding box người.
        Thay vì dùng ngưỡng cố định (150px), ngưỡng tự động scale theo perspective camera.
        Người ở xa camera → bbox nhỏ hơn → ngưỡng nhỏ hơn (hợp lý hơn).
        """
        px1, py1, px2, py2 = person_bbox
        person_height = py2 - py1
        return max(person_height * 1.2, 80.0)  # Tối thiểu 80px
    
    def _is_in_roi(self, center):
        """
        Kiểm tra xem điểm center có nằm trong vùng ROI (Region of Interest) không.
        Nếu ROI_POLYGON = None → toàn bộ frame đều hợp lệ.
        """
        if config.ROI_POLYGON is None:
            return True
        roi_points = np.array(config.ROI_POLYGON, dtype=np.float32)
        return cv2.pointPolygonTest(roi_points, center, False) >= 0
    
    # ========================================================================
    # Spatial Matching: Ghép nối track cũ với detection mới
    # ========================================================================
    
    def _match_tracks_to_detections(self, luggage_detections):
        """
        Spatial Matching nâng cao: Ghép nối vị trí gần + IoU cho các detection mới 
        với các track đứng yên ĐÃ XÁC NHẬN, để duy trì timer khi tracker bị mất ID.
        """
        matched_new_dets = set()
        for new_id, new_lug in list(luggage_detections.items()):
            new_center = new_lug['center']
            new_bbox = new_lug['bbox']
            best_match_id = None
            best_score = float('inf')
            
            for old_id, track in self.luggage_tracks.items():
                if old_id != new_id and track.get('is_confirmed_stationary', False):
                    dist = self._compute_distance(new_center, track['center'])
                    iou = self._compute_iou(new_bbox, track['bbox'])
                    
                    # Ghép nối nếu: khoảng cách tâm < 60px HOẶC IoU > 0.3
                    if (dist < 60.0 or iou > 0.3) and dist < best_score:
                        best_score = dist
                        best_match_id = old_id
                        
            if best_match_id is not None and best_match_id not in matched_new_dets:
                old_track = self.luggage_tracks[best_match_id]
                self.luggage_tracks[new_id] = old_track
                self.luggage_tracks[new_id]['track_id'] = new_id
                del self.luggage_tracks[best_match_id]
                matched_new_dets.add(new_id)
    
    # ========================================================================
    # Owner Detection: Tìm chủ sở hữu của hành lý (có Owner Memory)
    # ========================================================================
    
    def _find_owner(self, track, center, person_detections):
        """
        Tìm chủ sở hữu của hành lý với cơ chế Owner Memory.
        
        Ưu tiên kiểm tra chủ sở hữu ban đầu (original_owner) trước.
        Nếu chủ ban đầu không còn trong frame → mới tính người gần nhất.
        Nếu người lạ đi ngang qua gần hành lý → KHÔNG reset timer (trừ khi họ ở rất gần).
        """
        min_dist = float('inf')
        closest_pid = None
        has_owner = False
        best_adaptive_thresh = self.owner_dist_thresh  # Fallback
        
        # Trường hợp 1: Kiểm tra chủ sở hữu ban đầu (Original Owner Memory)
        original_owner_id = track.get('original_owner_id')
        if original_owner_id is not None and original_owner_id in person_detections:
            owner_bbox = person_detections[original_owner_id]['bbox']
            dist_to_original = self._compute_person_distance(center, owner_bbox)
            adaptive_thresh = self._compute_adaptive_threshold(owner_bbox)
            
            min_dist = dist_to_original
            closest_pid = original_owner_id
            best_adaptive_thresh = adaptive_thresh
            has_owner = (dist_to_original <= adaptive_thresh)
        
        # Trường hợp 2: Tìm người gần nhất trong tất cả person detections
        for pid, person in person_detections.items():
            p_dist = self._compute_person_distance(center, person['bbox'])
            if p_dist < min_dist:
                min_dist = p_dist
                closest_pid = pid
                best_adaptive_thresh = self._compute_adaptive_threshold(person['bbox'])
        
        # Chỉ xem là có chủ nếu chủ ban đầu ở gần, HOẶC nếu chưa có chủ ban đầu thì
        # bất kỳ ai ở gần đều được tính (dùng adaptive threshold)
        if original_owner_id is None or original_owner_id not in person_detections:
            has_owner = (min_dist <= best_adaptive_thresh)
        
        return min_dist, closest_pid, has_owner, best_adaptive_thresh
    
    # ========================================================================
    # Stationary Check: Kiểm tra hành lý có đứng yên không
    # ========================================================================
    
    def _check_stationary(self, track):
        """Kiểm tra tính đứng yên dựa vào lịch sử di chuyển"""
        is_stationary = False
        if len(track['history']) >= 4:
            hist_arr = list(track['history'])
            max_displacement = max(self._compute_distance(hist_arr[0], pt) for pt in hist_arr)
            if max_displacement <= self.move_thresh:
                is_stationary = True
        return is_stationary
    
    def _update_stationary_state(self, track, is_stationary, current_time):
        """Cập nhật trạng thái đứng yên và timer tương ứng"""
        track['is_stationary'] = is_stationary
        
        if is_stationary:
            if track['stationary_start_time'] is None:
                track['stationary_start_time'] = current_time
            track['static_timer'] = current_time - track['stationary_start_time']
            
            # CHỈ XÁC NHẬN ĐỨNG YÊN THỰC SỰ NẾU ĐỨNG YÊN ĐỦ LÂU (>= min_static_confirm_sec)
            if track['static_timer'] >= self.min_static_confirm_sec:
                track['is_confirmed_stationary'] = True
        else:
            # Nếu balo di chuyển -> HỦY TOÀN BỘ TRẠNG THÁI ĐỨNG YÊN & TIMER
            track['stationary_start_time'] = None
            track['static_timer'] = 0.0
            track['no_owner_start_time'] = None
            track['abandon_timer'] = 0.0
            track['state'] = 'MOVING'
            track['is_confirmed_stationary'] = False
            track['alert_sent'] = False
            # Reset original owner khi hành lý bắt đầu di chuyển lại
            track['original_owner_id'] = None
    
    # ========================================================================
    # Alert State: Xác định cấp cảnh báo đa cấp
    # ========================================================================
    
    def _determine_alert_state(self, track, has_owner, current_time, min_dist):
        """
        Xác định trạng thái cảnh báo đa cấp dựa trên timer:
        - STATIONARY_WITH_OWNER: Có chủ ở gần
        - SUSPICIOUS: Không chủ >= suspicious_time (cấp 1 — cảnh báo nhẹ)
        - UNATTENDED: Không chủ >= unattended_time (cấp 2 — cảnh báo trung bình)  
        - ABANDONED: Không chủ >= abandon_time (cấp 3 — cảnh báo nghiêm trọng)
        """
        new_alerts = []
        
        if has_owner:
            track['state'] = 'STATIONARY_WITH_OWNER'
            track['no_owner_start_time'] = None
            track['abandon_timer'] = 0.0
            track['alert_sent'] = False
        else:
            if track['no_owner_start_time'] is None:
                track['no_owner_start_time'] = current_time
            track['abandon_timer'] = current_time - track['no_owner_start_time']
            
            # Cấp 3: ABANDONED (Critical)
            if track['abandon_timer'] >= self.abandon_time_thresh:
                track['state'] = 'ABANDONED'
                if not track['alert_sent']:
                    track['alert_sent'] = True
                    alert_event = {
                        'timestamp': current_time,
                        'luggage_id': track['track_id'],
                        'bbox': track['bbox'],
                        'abandon_duration': track['abandon_timer'],
                        'closest_person_dist': min_dist,
                        'alert_level': 'CRITICAL'
                    }
                    new_alerts.append(alert_event)
                    self.alert_history.append(alert_event)
            # Cấp 2: UNATTENDED (Alert)
            elif track['abandon_timer'] >= self.unattended_time_thresh:
                track['state'] = 'UNATTENDED'
            # Cấp 1: SUSPICIOUS (Warning)
            elif track['abandon_timer'] >= self.suspicious_time_thresh:
                track['state'] = 'SUSPICIOUS'
            else:
                track['state'] = 'STATIONARY_NO_OWNER'
        
        return new_alerts
    
    # ========================================================================
    # Main Processing Pipeline
    # ========================================================================
    
    def _create_new_track(self, tid, center, bbox, current_time, closest_pid):
        """Tạo track mới cho hành lý vừa xuất hiện"""
        return {
            'track_id': tid,
            'first_seen_time': current_time,
            'last_seen_time': current_time,
            'history': deque(maxlen=config.STATIONARY_HISTORY_FRAMES),
            'stationary_start_time': None,
            'no_owner_start_time': None,
            'state': 'MOVING',
            'is_stationary': False,
            'is_confirmed_stationary': False,
            'abandon_timer': 0.0,
            'static_timer': 0.0,
            'alert_sent': False,
            'min_person_dist': float('inf'),
            'closest_person_id': None,
            'original_owner_id': closest_pid,  # Owner Memory: Ghi nhớ chủ ban đầu
            'bbox': bbox,
            'center': center,
            'has_owner': False,
        }

    def _update_active_tracks(self, luggage_detections, person_detections, current_time):
        """Xử lý các detections hiện tại từ YOLO — cập nhật trạng thái từng hành lý"""
        updated_luggage = {}
        new_alerts = []
        
        for tid, lug in luggage_detections.items():
            bbox = lug['bbox']
            center = lug['center']
            
            # Kiểm tra ROI — bỏ qua hành lý ngoài vùng quan tâm
            if not self._is_in_roi(center):
                continue
            
            # Tìm người gần nhất (để gán original_owner nếu track mới)
            temp_min_dist = float('inf')
            temp_closest_pid = None
            for pid, person in person_detections.items():
                p_dist = self._compute_person_distance(center, person['bbox'])
                if p_dist < temp_min_dist:
                    temp_min_dist = p_dist
                    temp_closest_pid = pid
            
            if tid not in self.luggage_tracks:
                self.luggage_tracks[tid] = self._create_new_track(
                    tid, center, bbox, current_time, temp_closest_pid
                )
                
            track = self.luggage_tracks[tid]
            track['last_seen_time'] = current_time
            track['bbox'] = bbox
            track['center'] = center
            track['history'].append(center)
            
            # Kiểm tra tính đứng yên
            is_stationary = self._check_stationary(track)
            self._update_stationary_state(track, is_stationary, current_time)
            
            # Tìm chủ sở hữu (có Owner Memory)
            min_dist, closest_pid, has_owner, _ = self._find_owner(track, center, person_detections)
            track['min_person_dist'] = min_dist
            track['closest_person_id'] = closest_pid
            track['has_owner'] = has_owner
            
            # Cập nhật Original Owner nếu track mới và chưa có
            if track.get('original_owner_id') is None and has_owner:
                track['original_owner_id'] = closest_pid
            
            # Xác định cấp cảnh báo (chỉ khi đứng yên)
            if is_stationary:
                alerts = self._determine_alert_state(track, has_owner, current_time, min_dist)
                new_alerts.extend(alerts)
            
            updated_luggage[tid] = track
        
        return updated_luggage, new_alerts
    
    def _handle_missing_tracks(self, active_luggage_ids, person_detections, current_time):
        """
        BỘ NHỚ LƯU KHÓA VỊ TRÍ THÔNG MINH (Smart Static Lock Buffer)
        Xử lý các track bị mất detection: giữ lại nếu đã xác nhận đứng yên, xóa nếu chưa.
        """
        updated_luggage = {}
        new_alerts = []
        
        for tid, track in list(self.luggage_tracks.items()):
            if tid in active_luggage_ids:
                continue
                
            time_missing = current_time - track['last_seen_time']
            
            # NẾU BALO CHỈ ĐANG DI CHUYỂN HOẶC CHƯA ĐỨNG YÊN ĐỦ -> XÓA NGAY
            if not track.get('is_confirmed_stationary', False):
                del self.luggage_tracks[tid]
                continue
                
            # Nếu đã xác nhận đứng yên thực sự và mới mất nhận diện dưới max_missing_sec
            if time_missing <= self.max_missing_sec:
                # Tìm chủ sở hữu cho track đang missing
                min_dist, closest_pid, has_owner, _ = self._find_owner(
                    track, track['center'], person_detections
                )
                track['min_person_dist'] = min_dist
                track['closest_person_id'] = closest_pid
                track['has_owner'] = has_owner
                
                # Xác định cấp cảnh báo
                alerts = self._determine_alert_state(track, has_owner, current_time, min_dist)
                new_alerts.extend(alerts)
                    
                updated_luggage[tid] = track
            else:
                del self.luggage_tracks[tid]
        
        return updated_luggage, new_alerts

    def process_frame(self, luggage_detections, person_detections, current_time=None, fps=30.0):
        """
        Entry point chính: Cập nhật trạng thái từng hành lý trong frame hiện tại.
        
        Pipeline:
        1. Spatial Matching — ghép nối track cũ với detection mới (IoU + distance)
        2. Update Active Tracks — cập nhật trạng thái, owner, alert level
        3. Handle Missing Tracks — xử lý memory buffer cho track bị mất detection
        
        Returns:
            updated_luggage: dict trạng thái tất cả hành lý đang theo dõi
            new_alerts: list các cảnh báo mới phát sinh trong frame này
        """
        if current_time is None:
            current_time = time.time()
        
        # 1. Spatial Matching
        self._match_tracks_to_detections(luggage_detections)
        
        # 2. Xử lý các detections hiện tại
        updated_luggage, new_alerts = self._update_active_tracks(
            luggage_detections, person_detections, current_time
        )
        
        # 3. Xử lý track bị mất detection (Memory Buffer)
        active_ids = set(luggage_detections.keys())
        missing_luggage, missing_alerts = self._handle_missing_tracks(
            active_ids, person_detections, current_time
        )
        updated_luggage.update(missing_luggage)
        new_alerts.extend(missing_alerts)
        
        return updated_luggage, new_alerts
