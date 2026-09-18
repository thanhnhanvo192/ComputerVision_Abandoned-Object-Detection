import time
import math
from collections import deque
import config

class AbandonedObjectDetector:
    def __init__(self, 
                 move_thresh=config.STATIONARY_MOVE_THRESHOLD,
                 owner_dist_thresh=config.OWNER_DISTANCE_THRESHOLD,
                 abandon_time_thresh=config.ABANDON_TIME_THRESHOLD,
                 min_static_confirm_sec=1.0,  # Balo phải đứng yên ít nhất 1.0 giây mới được Khóa vị trí Bộ nhớ
                 max_missing_sec=30.0):
        """
        Khởi tạo Bộ phân tích phát hiện vật thể bị bỏ quên nâng cao.
        Hỗ trợ cơ chế KHÓA BỘ NHỚ THÔNG MINH (Smart Static Lock Memory):
        - Chỉ khóa vị trí bộ nhớ khi balo đứng yên THỰC SỰ (>= 1.0 giây).
        - Nếu balo đang di chuyển trên lưng người mà mất detection -> KHÔNG lưu vị trí ma.
        - Tự động hủy vị trí khóa nếu người nhặt/xách balo đi nơi khác.
        """
        self.move_thresh = move_thresh
        self.owner_dist_thresh = owner_dist_thresh
        self.abandon_time_thresh = abandon_time_thresh
        self.min_static_confirm_sec = min_static_confirm_sec
        self.max_missing_sec = max_missing_sec
        
        # Lưu trữ trạng thái vết theo dõi của hành lý theo track_id
        self.luggage_tracks = {}
        self.alert_history = []
        
    def reset(self):
        """Xóa sạch lịch sử theo dõi"""
        self.luggage_tracks.clear()
        self.alert_history.clear()
        
    def _compute_distance(self, p1, p2):
        """Tính khoảng cách Euclidean giữa 2 điểm (x1, y1) và (x2, y2)"""
        return math.sqrt((p1[0] - p2[0])**2 + (p1[1] - p2[1])**2)
        
    def _compute_person_distance(self, luggage_center, person_bbox):
        """
        Tính khoảng cách từ tâm hành lý đến vị trí người.
        Ưu tiên tính với chân người (bottom-center) và tâm người.
        """
        px1, py1, px2, py2 = person_bbox
        feet_pos = ((px1 + px2) / 2.0, py2)  # Vị trí chân người
        center_pos = ((px1 + px2) / 2.0, (py1 + py2) / 2.0)  # Tâm người
        
        dist_feet = self._compute_distance(luggage_center, feet_pos)
        dist_center = self._compute_distance(luggage_center, center_pos)
        
        return min(dist_feet, dist_center)

    def process_frame(self, luggage_detections, person_detections, current_time=None, fps=30.0):
        """
        Cập nhật trạng thái từng hành lý trong frame hiện tại.
        """
        if current_time is None:
            current_time = time.time()
            
        updated_luggage = {}
        new_alerts = []
        
        # 1. Spatial Matching (Ghép nối vị trí gần cho các detection mới với các track đứng yên ĐÃ XÁC NHẬN)
        matched_new_dets = set()
        for new_id, new_lug in list(luggage_detections.items()):
            new_center = new_lug['center']
            best_match_id = None
            min_spatial_dist = float('inf')
            
            for old_id, track in self.luggage_tracks.items():
                # Chỉ ghép nối với track cũ ĐÃ ĐỨNG YÊN THỰC SỰ
                if old_id != new_id and track.get('is_confirmed_stationary', False):
                    dist = self._compute_distance(new_center, track['center'])
                    if dist < 60.0 and dist < min_spatial_dist:  # Bán kính 60px
                        min_spatial_dist = dist
                        best_match_id = old_id
                        
            if best_match_id is not None and best_match_id not in matched_new_dets:
                old_track = self.luggage_tracks[best_match_id]
                self.luggage_tracks[new_id] = old_track
                self.luggage_tracks[new_id]['track_id'] = new_id
                del self.luggage_tracks[best_match_id]
                matched_new_dets.add(new_id)

        active_luggage_ids = set(luggage_detections.keys())
        
        # 2. Xử lý các detections hiện tại từ YOLO
        for tid, lug in luggage_detections.items():
            bbox = lug['bbox']
            center = lug['center']
            
            if tid not in self.luggage_tracks:
                self.luggage_tracks[tid] = {
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
                    'closest_person_id': None
                }
                
            track = self.luggage_tracks[tid]
            track['last_seen_time'] = current_time
            track['bbox'] = bbox
            track['center'] = center
            track['history'].append(center)
            
            # Kiểm tra tính đứng yên dựa vào lịch sử di chuyển
            is_stationary = False
            if len(track['history']) >= 4:
                hist_arr = list(track['history'])
                max_displacement = max(self._compute_distance(hist_arr[0], pt) for pt in hist_arr)
                if max_displacement <= self.move_thresh:
                    is_stationary = True
                    
            track['is_stationary'] = is_stationary
            
            if is_stationary:
                if track['stationary_start_time'] is None:
                    track['stationary_start_time'] = current_time
                track['static_timer'] = current_time - track['stationary_start_time']
                
                # CHỈ XÁC NHẬN ĐỨNG YÊN THỰC SỰ NẾU ĐỨNG YÊN ĐỦ LÂU (>= 1.0 giây)
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

            # Tính khoảng cách tới tất cả người có trong video
            min_dist = float('inf')
            closest_pid = None
            for pid, person in person_detections.items():
                p_dist = self._compute_person_distance(center, person['bbox'])
                if p_dist < min_dist:
                    min_dist = p_dist
                    closest_pid = pid
                    
            track['min_person_dist'] = min_dist
            track['closest_person_id'] = closest_pid
            has_owner = (min_dist <= self.owner_dist_thresh)
            track['has_owner'] = has_owner
            
            # Cập nhật state & đếm timer
            if is_stationary:
                if has_owner:
                    track['state'] = 'STATIONARY_WITH_OWNER'
                    track['no_owner_start_time'] = None
                    track['abandon_timer'] = 0.0
                    track['alert_sent'] = False
                else:
                    if track['no_owner_start_time'] is None:
                        track['no_owner_start_time'] = current_time
                    track['abandon_timer'] = current_time - track['no_owner_start_time']
                    
                    if track['abandon_timer'] >= self.abandon_time_thresh:
                        track['state'] = 'ABANDONED'
                        if not track['alert_sent']:
                            track['alert_sent'] = True
                            alert_event = {
                                'timestamp': current_time,
                                'luggage_id': tid,
                                'bbox': bbox,
                                'abandon_duration': track['abandon_timer'],
                                'closest_person_dist': min_dist
                            }
                            new_alerts.append(alert_event)
                            self.alert_history.append(alert_event)
                    else:
                        track['state'] = 'STATIONARY_NO_OWNER'

            updated_luggage[tid] = track

        # 3. BỘ NHỚ LƯU KHÓA VỊ TRÍ THÔNG MINH (Smart Static Lock Buffer)
        # CHỈ giữ lại các balo ĐÃ XÁC NHẬN ĐỨNG YÊN THỰC SỰ (>= 1.0 giây) khi mất detection
        for tid, track in list(self.luggage_tracks.items()):
            if tid not in active_luggage_ids:
                time_missing = current_time - track['last_seen_time']
                
                # NẾU BALO CHỈ ĐANG DI CHUYỂN HOẶC CHƯA ĐỨNG YÊN ĐỦ 1 GIÂY -> XÓA NGAY (KHÔNG TẠO VỊ TRÍ MA)
                if not track.get('is_confirmed_stationary', False):
                    del self.luggage_tracks[tid]
                    continue
                    
                # Nếu đã xác nhận đứng yên thực sự và mới mất nhận diện dưới 30s -> DÙNG BỘ NHỚ KHÓA VỊ TRÍ
                if time_missing <= self.max_missing_sec:
                    min_dist = float('inf')
                    closest_pid = None
                    for pid, person in person_detections.items():
                        p_dist = self._compute_person_distance(track['center'], person['bbox'])
                        if p_dist < min_dist:
                            min_dist = p_dist
                            closest_pid = pid
                            
                    track['min_person_dist'] = min_dist
                    track['closest_person_id'] = closest_pid
                    has_owner = (min_dist <= self.owner_dist_thresh)
                    track['has_owner'] = has_owner
                    
                    if has_owner:
                        track['state'] = 'STATIONARY_WITH_OWNER'
                        track['no_owner_start_time'] = None
                        track['abandon_timer'] = 0.0
                        track['alert_sent'] = False
                    else:
                        if track['no_owner_start_time'] is None:
                            track['no_owner_start_time'] = current_time
                        track['abandon_timer'] = current_time - track['no_owner_start_time']
                        
                        if track['abandon_timer'] >= self.abandon_time_thresh:
                            track['state'] = 'ABANDONED'
                            if not track['alert_sent']:
                                track['alert_sent'] = True
                                alert_event = {
                                    'timestamp': current_time,
                                    'luggage_id': tid,
                                    'bbox': track['bbox'],
                                    'abandon_duration': track['abandon_timer'],
                                    'closest_person_dist': min_dist
                                }
                                new_alerts.append(alert_event)
                                self.alert_history.append(alert_event)
                        else:
                            track['state'] = 'STATIONARY_NO_OWNER'
                            
                    updated_luggage[tid] = track
                else:
                    del self.luggage_tracks[tid]
                    
        return updated_luggage, new_alerts
