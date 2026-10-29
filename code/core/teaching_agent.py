"""AI Pedagogical Reasoning Agent.
Evaluates multimodal dynamics in real-time and provides context-aware,
actionable teaching suggestions to assist educators without intrusiveness.
"""
from typing import Dict, Any, List, Optional
from dataclasses import dataclass

@dataclass
class TeachingSuggestion:
    category: str      # 'PACING', 'INTERACTION', 'DROP_OFF', 'DYNAMICS', 'AFFIRMATION'
    severity: str      # 'INFO', 'WARNING', 'ACTION_REQUIRED'
    trigger_reason: str
    suggestion_text: str
    timestamp_sec: float

class PedagogicalReasoningAgent:
    def __init__(self, alert_cooldown_sec: float = 60.0):
        self.alert_cooldown_sec = alert_cooldown_sec
        self.last_alert_timestamps: Dict[str, float] = {}
        self.suggestion_history: List[TeachingSuggestion] = []

    def _can_fire(self, category: str, current_time: float) -> bool:
        last_time = self.last_alert_timestamps.get(category, -9999.0)
        return (current_time - last_time) >= self.alert_cooldown_sec

    def evaluate_dynamics(
        self,
        timestamp_sec: float,
        fusion_metrics: Dict[str, Any],
        visual_metrics: Dict[str, Any],
        audio_metrics: Dict[str, Any]
    ) -> Optional[TeachingSuggestion]:
        """Analyzes session metrics and yields a teaching suggestion if pedagogical heuristics trigger."""
        composite = fusion_metrics.get("composite_engagement", 50.0)
        is_dropoff = fusion_metrics.get("is_dropoff", False)
        dropoff_mag = fusion_metrics.get("dropoff_magnitude_percent", 0.0)
        
        monologue_sec = audio_metrics.get("consecutive_monologue_sec", 0.0)
        silence_sec = audio_metrics.get("consecutive_silence_sec", 0.0)
        acoustic_state = audio_metrics.get("acoustic_state", "NORMAL")

        # 1. Pacing & Monologue Detection (> 10-12 minutes without student interaction)
        if monologue_sec >= 600.0 and self._can_fire("PACING", timestamp_sec):
            mins = int(monologue_sec // 60)
            suggestion = TeachingSuggestion(
                category="PACING",
                severity="WARNING",
                trigger_reason=f"Continuous instructor monologue detected for {mins} minutes with zero student audio.",
                suggestion_text=(
                    f"Pacing Alert: You have spoken continuously for {mins} minutes. "
                    "Cognitive retention drops during long passive listening. "
                    "Consider a 2-minute Think-Pair-Share, a formative pulse poll, or calling for student questions."
                ),
                timestamp_sec=timestamp_sec
            )
            self._record_suggestion(suggestion, timestamp_sec)
            return suggestion

        # 2. Attention Drop-off Detection (sudden drop >= 20% in engagement)
        if is_dropoff and composite < 55.0 and self._can_fire("DROP_OFF", timestamp_sec):
            suggestion = TeachingSuggestion(
                category="DROP_OFF",
                severity="ACTION_REQUIRED",
                trigger_reason=f"Classroom engagement dropped abruptly by {dropoff_mag}% below recent baseline.",
                suggestion_text=(
                    f"Engagement Dip Detected: Attention dropped by {dropoff_mag}%. "
                    "Material may be overly complex or cognitive fatigue is setting in. "
                    "Suggest pausing to ask: 'What is the most confusing part of this concept so far?' "
                    "or offering a concrete real-world case study."
                ),
                timestamp_sec=timestamp_sec
            )
            self._record_suggestion(suggestion, timestamp_sec)
            return suggestion

        # 3. Awkward / Prolonged Silence (> 25s of dead silence)
        if silence_sec >= 25.0 and self._can_fire("INTERACTION", timestamp_sec):
            suggestion = TeachingSuggestion(
                category="INTERACTION",
                severity="INFO",
                trigger_reason=f"Prolonged dead silence for {int(silence_sec)}s.",
                suggestion_text=(
                    "Scaffolding Opportunity: Extended silence detected. Students may feel intimidated by the question format. "
                    "Try breaking the prompt down into a quick true/false check or allow 30 seconds for written reflection."
                ),
                timestamp_sec=timestamp_sec
            )
            self._record_suggestion(suggestion, timestamp_sec)
            return suggestion

        # 4. Restlessness / Classroom Chatter
        if acoustic_state == "HIGH_NOISE_OR_CHATTER" and self._can_fire("DYNAMICS", timestamp_sec):
            suggestion = TeachingSuggestion(
                category="DYNAMICS",
                severity="WARNING",
                trigger_reason="High ambient noise and erratic physical motion detected across classroom.",
                suggestion_text=(
                    "Classroom Dynamics Alert: Restlessness and side-conversations detected. "
                    "Regain group focus with an interactive attention-getter, a quick recap, "
                    "or transition to the next lecture segment."
                ),
                timestamp_sec=timestamp_sec
            )
            self._record_suggestion(suggestion, timestamp_sec)
            return suggestion

        # 5. High Engagement Affirmation
        if composite >= 82.0 and acoustic_state == "INTERACTIVE_DISCUSSION_QA" and self._can_fire("AFFIRMATION", timestamp_sec):
            suggestion = TeachingSuggestion(
                category="AFFIRMATION",
                severity="INFO",
                trigger_reason="Classroom is in a high-engagement, collaborative Q&A state.",
                suggestion_text=(
                    "Optimal Dynamics: Excellent collaborative energy detected (Composite Engagement: 82%+). "
                    "Current discussion format is highly engaging for participants."
                ),
                timestamp_sec=timestamp_sec
            )
            self._record_suggestion(suggestion, timestamp_sec)
            return suggestion

        return None

    def _record_suggestion(self, suggestion: TeachingSuggestion, timestamp_sec: float):
        self.last_alert_timestamps[suggestion.category] = timestamp_sec
        self.suggestion_history.append(suggestion)

    def get_all_suggestions(self) -> List[Dict[str, Any]]:
        return [
            {
                "category": s.category,
                "severity": s.severity,
                "trigger_reason": s.trigger_reason,
                "suggestion_text": s.suggestion_text,
                "timestamp_sec": round(s.timestamp_sec, 1)
            }
            for s in self.suggestion_history
        ]

