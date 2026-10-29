"""Automated Attendance Tracking Module.
Implements continuous presence detection over time, filtering transient noise and
accurately classifying participants as PRESENT, TARDY, or ABSENT.
"""
from typing import Dict, List, Optional
from config import AttendanceConfig

class StudentAttendanceState:
    def __init__(self, student_id: str, name: str):
        self.student_id = student_id
        self.name = name
        self.first_seen_sec: Optional[float] = None
        self.last_seen_sec: Optional[float] = None
        self.total_present_sec: float = 0.0
        self.current_streak_sec: float = 0.0
        self.max_continuous_streak_sec: float = 0.0
        self.is_currently_present: bool = False
        self.presence_history: List[bool] = []

    def update_presence(self, is_detected: bool, timestamp_sec: float, interval_sec: float):
        self.presence_history.append(is_detected)
        self.is_currently_present = is_detected

        if is_detected:
            if self.first_seen_sec is None:
                self.first_seen_sec = timestamp_sec
            self.last_seen_sec = timestamp_sec
            self.total_present_sec += interval_sec
            self.current_streak_sec += interval_sec
            if self.current_streak_sec > self.max_continuous_streak_sec:
                self.max_continuous_streak_sec = self.current_streak_sec
        else:
            self.current_streak_sec = 0.0

    def compute_status(self, total_session_sec: float, config: AttendanceConfig) -> Dict[str, any]:
        if total_session_sec <= 0:
            return {
                "status": "ABSENT",
                "presence_ratio": 0.0,
                "notes": "Session duration invalid"
            }

        presence_ratio = min(1.0, self.total_present_sec / total_session_sec)
        
        # 1. Did student meet sustained presence duration?
        if self.total_present_sec < config.min_sustained_seconds:
            return {
                "status": "ABSENT",
                "presence_ratio": presence_ratio,
                "notes": f"Presence duration ({round(self.total_present_sec, 1)}s) below sustained minimum threshold ({config.min_sustained_seconds}s)"
            }

        # 2. Did student meet the presence ratio requirement?
        if presence_ratio < config.min_presence_ratio:
            return {
                "status": "ABSENT",
                "presence_ratio": presence_ratio,
                "notes": f"Attendance ratio {round(presence_ratio*100, 1)}% below required {int(config.min_presence_ratio*100)}%"
            }

        # 3. Was the arrival tardy?
        if self.first_seen_sec is not None:
            tardy_cutoff = total_session_sec * config.tardy_threshold_ratio
            if self.first_seen_sec > tardy_cutoff:
                return {
                    "status": "TARDY",
                    "presence_ratio": presence_ratio,
                    "notes": f"Arrived late at {round(self.first_seen_sec, 1)}s (cutoff: {round(tardy_cutoff, 1)}s)"
                }

        return {
            "status": "PRESENT",
            "presence_ratio": presence_ratio,
            "notes": "Met sustained continuous presence requirements"
        }


class AttendanceTracker:
    def __init__(self, config: AttendanceConfig = None):
        self.config = config or AttendanceConfig()
        self.students: Dict[str, StudentAttendanceState] = {}
        self.total_session_elapsed_sec: float = 0.0

    def register_roster(self, roster: List[Dict[str, str]]):
        """Pre-registers expected students into the tracker."""
        for item in roster:
            s_id = item["student_id"]
            name = item.get("display_name", s_id)
            if s_id not in self.students:
                self.students[s_id] = StudentAttendanceState(s_id, name)

    def process_frame_detections(self, detected_student_ids: List[str], timestamp_sec: float, interval_sec: float):
        """Processes detections from the vision engine for a time window."""
        self.total_session_elapsed_sec = max(self.total_session_elapsed_sec, timestamp_sec)
        detected_set = set(detected_student_ids)

        # Update all registered students
        for s_id, state in self.students.items():
            is_present = s_id in detected_set
            state.update_presence(is_present, timestamp_sec, interval_sec)

        # Handle any new/unregistered detected participants
        for s_id in detected_set:
            if s_id not in self.students:
                new_state = StudentAttendanceState(s_id, f"Participant_{s_id}")
                new_state.update_presence(True, timestamp_sec, interval_sec)
                self.students[s_id] = new_state

    def get_live_summary(self) -> Dict[str, any]:
        """Returns live statistics of who is currently present in the classroom."""
        currently_present = [s for s in self.students.values() if s.is_currently_present]
        return {
            "total_enrolled": len(self.students),
            "currently_present_count": len(currently_present),
            "session_elapsed_sec": round(self.total_session_elapsed_sec, 1),
            "students": [
                {
                    "student_id": s.student_id,
                    "name": s.name,
                    "is_present": s.is_currently_present,
                    "total_present_sec": round(s.total_present_sec, 1),
                    "current_streak_sec": round(s.current_streak_sec, 1)
                }
                for s in self.students.values()
            ]
        }

    def finalize_attendance(self, total_session_sec: Optional[float] = None) -> List[Dict[str, any]]:
        """Calculates final attendance determinations for all students."""
        session_duration = total_session_sec or self.total_session_elapsed_sec
        final_records = []
        for s_id, state in self.students.items():
            outcome = state.compute_status(session_duration, self.config)
            final_records.append({
                "student_id": s_id,
                "name": state.name,
                "first_seen_sec": state.first_seen_sec,
                "last_seen_sec": state.last_seen_sec,
                "total_present_sec": state.total_present_sec,
                "presence_ratio": outcome["presence_ratio"],
                "status": outcome["status"],
                "notes": outcome["notes"]
            })
        return final_records

