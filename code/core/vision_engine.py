"""Visual Perception Engine.
Extracts behavioral engagement indicators:
- Head pose orientation (yaw, pitch) -> screen/board attention
- Motion energy dynamics (frame differencing / optical activity)
- Inactivity / drowsiness tracking
- Aggregated classroom visual attention metric
"""
import numpy as np
from typing import Dict, List, Any, Optional
from config import VisionConfig

class StudentVisualState:
    def __init__(self, student_id: str):
        self.student_id = student_id
        self.consecutive_inactive_sec: float = 0.0
        self.last_yaw: float = 0.0
        self.last_pitch: float = 0.0
        self.recent_attention_scores: List[float] = []

    def evaluate_behavior(
        self,
        yaw_deg: float,
        pitch_deg: float,
        motion_energy: float,
        interval_sec: float,
        config: VisionConfig
    ) -> Dict[str, Any]:
        """Calculates attention and engagement score for a single student in a time window."""
        self.last_yaw = yaw_deg
        self.last_pitch = pitch_deg

        # 1. Head Pose Attention Penalty
        # Gaze looking forward towards instructor/board: yaw within +/- max_yaw, pitch within +/- max_pitch
        yaw_err = max(0.0, abs(yaw_deg) - config.max_yaw_dev_deg)
        pitch_err = max(0.0, abs(pitch_deg) - config.max_pitch_dev_deg)
        
        # Exponential or smooth drop-off for orientation deviation
        orientation_score = np.exp(-0.04 * (yaw_err + 1.2 * pitch_err))
        orientation_score = float(np.clip(orientation_score, 0.0, 1.0))

        # 2. Motion Energy & Inactivity Penalty
        # Motion energy is between 0.0 (completely frozen/sleeping) and 1.0 (erratic fidgeting)
        if motion_energy < 0.05:
            self.consecutive_inactive_sec += interval_sec
        else:
            self.consecutive_inactive_sec = 0.0

        inactivity_penalty = 0.0
        if self.consecutive_inactive_sec > config.inactivity_seconds_threshold:
            # Drop score significantly if inactive for longer than threshold
            overstay = self.consecutive_inactive_sec - config.inactivity_seconds_threshold
            inactivity_penalty = min(0.6, overstay * 0.02)

        # High fidgeting penalty
        fidget_penalty = 0.0
        if motion_energy > config.excessive_motion_threshold:
            fidget_penalty = (motion_energy - config.excessive_motion_threshold) * 0.5

        # 3. Composite Student Attention Score
        raw_score = (orientation_score * 0.7 + (1.0 - fidget_penalty) * 0.3) - inactivity_penalty
        student_attention = float(np.clip(raw_score, 0.0, 1.0) * 100.0)

        # Categorize posture / engagement state
        if inactivity_penalty > 0.3:
            state_label = "INACTIVE_OR_DOZING"
        elif fidget_penalty > 0.2:
            state_label = "RESTLESS_FIDGETING"
        elif orientation_score < 0.4:
            state_label = "DISTRACTED_LOOKING_AWAY"
        else:
            state_label = "ATTENTIVE"

        self.recent_attention_scores.append(student_attention)
        if len(self.recent_attention_scores) > 20:
            self.recent_attention_scores.pop(0)

        return {
            "student_id": self.student_id,
            "attention_score": round(student_attention, 1),
            "state_label": state_label,
            "yaw": round(yaw_deg, 1),
            "pitch": round(pitch_deg, 1),
            "motion_energy": round(motion_energy, 2),
            "consecutive_inactive_sec": round(self.consecutive_inactive_sec, 1)
        }


class VisionPerceptionEngine:
    def __init__(self, config: VisionConfig = None):
        self.config = config or VisionConfig()
        self.student_states: Dict[str, StudentVisualState] = {}

    def get_or_create_state(self, student_id: str) -> StudentVisualState:
        if student_id not in self.student_states:
            self.student_states[student_id] = StudentVisualState(student_id)
        return self.student_states[student_id]

    def process_classroom_frame(
        self,
        student_detections: List[Dict[str, Any]],
        interval_sec: float
    ) -> Dict[str, Any]:
        """Processes observations for all detected students in the current frame/window.
        
        Args:
            student_detections: List of dicts, each containing:
                - 'student_id': str
                - 'yaw_deg': float
                - 'pitch_deg': float
                - 'motion_energy': float (0.0 to 1.0)
            interval_sec: Elapsed seconds in window
        """
        student_metrics = {}
        scores = []

        for det in student_detections:
            s_id = det["student_id"]
            state = self.get_or_create_state(s_id)
            metrics = state.evaluate_behavior(
                yaw_deg=det.get("yaw_deg", 0.0),
                pitch_deg=det.get("pitch_deg", 0.0),
                motion_energy=det.get("motion_energy", 0.15),
                interval_sec=interval_sec,
                config=self.config
            )
            student_metrics[s_id] = metrics
            scores.append(metrics["attention_score"])

        # Aggregate classroom visual attention score
        if scores:
            avg_visual_attention = float(np.mean(scores))
        else:
            avg_visual_attention = 0.0

        return {
            "avg_visual_attention": round(avg_visual_attention, 1),
            "tracked_count": len(scores),
            "student_details": student_metrics
        }

