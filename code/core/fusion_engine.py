"""Multimodal Fusion Engine.
Fuses visual behavioral attention and acoustic dynamics into a unified
Classroom Engagement Index, detecting drop-offs, interaction peaks, and pacing dynamics.
"""
import numpy as np
from typing import Dict, Any, List
from config import FusionConfig

class MultimodalFusionEngine:
    def __init__(self, config: FusionConfig = None):
        self.config = config or FusionConfig()
        self.engagement_history: List[float] = []
        self.timestamps: List[float] = []
        self.baseline_window_size: int = 10 # Rolling window for baseline

    def fuse_signals(
        self,
        timestamp_sec: float,
        visual_metrics: Dict[str, Any],
        audio_metrics: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Fuses visual attention and audio activity for a given timestamp."""
        v_score = visual_metrics.get("avg_visual_attention", 50.0)
        a_score = audio_metrics.get("audio_engagement_score", 50.0)

        # Weighted Multimodal Fusion
        w_v = self.config.visual_weight
        w_a = self.config.audio_weight
        composite_score = (w_v * v_score) + (w_a * a_score)
        composite_score = float(np.clip(composite_score, 0.0, 100.0))

        self.engagement_history.append(composite_score)
        self.timestamps.append(timestamp_sec)

        # Detect trend & drop-off
        is_dropoff = False
        dropoff_magnitude = 0.0
        rolling_baseline = composite_score

        if len(self.engagement_history) >= 4:
            # Baseline is mean of previous items (excluding current)
            prev_window = self.engagement_history[-min(len(self.engagement_history), self.baseline_window_size):-1]
            rolling_baseline = float(np.mean(prev_window))
            
            # Check relative drop
            if rolling_baseline > 30.0:
                rel_drop = (rolling_baseline - composite_score) / rolling_baseline
                if rel_drop >= self.config.dropoff_threshold:
                    is_dropoff = True
                    dropoff_magnitude = float(rel_drop * 100.0)

        # State Tag Classification
        acoustic_state = audio_metrics.get("acoustic_state", "NORMAL")
        if is_dropoff:
            state_tag = "ATTENTION_DROPOFF"
        elif acoustic_state == "INTERACTIVE_DISCUSSION_QA" and composite_score >= 70.0:
            state_tag = "HIGH_INTERACTIVE_ENGAGEMENT"
        elif acoustic_state == "HIGH_NOISE_OR_CHATTER":
            state_tag = "DISRUPTIVE_DISTRACTION"
        elif acoustic_state == "SILENCE_OR_PAUSE" and composite_score < 45.0:
            state_tag = "LOW_ENERGY_SILENCE"
        elif composite_score >= 75.0:
            state_tag = "OPTIMAL_ATTENTIVE_LECTURE"
        elif composite_score >= 50.0:
            state_tag = "MODERATE_PASSIVE_LISTENING"
        else:
            state_tag = "DISENGAGED_OR_TIRED"

        return {
            "timestamp_sec": round(timestamp_sec, 1),
            "visual_attention_score": round(v_score, 1),
            "audio_activity_score": round(a_score, 1),
            "composite_engagement": round(composite_score, 1),
            "rolling_baseline": round(rolling_baseline, 1),
            "is_dropoff": is_dropoff,
            "dropoff_magnitude_percent": round(dropoff_magnitude, 1),
            "state_tag": state_tag
        }

    def get_overall_session_average(self) -> float:
        if not self.engagement_history:
            return 0.0
        return float(round(np.mean(self.engagement_history), 1))

