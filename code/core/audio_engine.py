"""Audio Signal Processing Engine.
Analyzes acoustic dynamics of the classroom:
- Root-Mean-Square (RMS) vocal energy
- Speech activity vs. dead silence vs. disruptive noise
- Turn-taking / collaborative interaction vs. monologue
- Audio engagement indexing
"""
import numpy as np
from typing import Dict, Any, List
from config import AudioConfig

class AudioPerceptionEngine:
    def __init__(self, config: AudioConfig = None):
        self.config = config or AudioConfig()
        self.energy_history: List[float] = []
        self.consecutive_silence_sec: float = 0.0
        self.consecutive_monologue_sec: float = 0.0

    def process_audio_chunk(
        self,
        raw_samples: Optional[np.ndarray] = None,
        simulated_rms: Optional[float] = None,
        duration_sec: float = 2.0
    ) -> Dict[str, Any]:
        """Processes an audio chunk to compute acoustic activity metrics.
        Can consume raw audio PCM waveform array or simulated RMS energy.
        """
        if raw_samples is not None and len(raw_samples) > 0:
            rms_energy = float(np.sqrt(np.mean(raw_samples**2)))
        elif simulated_rms is not None:
            rms_energy = float(simulated_rms)
        else:
            rms_energy = 0.01

        self.energy_history.append(rms_energy)
        if len(self.energy_history) > 30:
            self.energy_history.pop(0)

        # Variance of energy indicates conversational turn-taking vs monotonous speech
        energy_std = float(np.std(self.energy_history)) if len(self.energy_history) > 1 else 0.0

        # Classify acoustic state
        if rms_energy < self.config.silence_energy_threshold:
            self.consecutive_silence_sec += duration_sec
            self.consecutive_monologue_sec = 0.0
            state = "SILENCE_OR_PAUSE"
            # Silence during a lecture: could be thinking time (moderate) or awkward lull
            audio_engagement_score = max(20.0, 60.0 - (self.consecutive_silence_sec * 2.0))

        elif rms_energy > 0.18:
            # High chaotic sound - disruptive ambient chatter or noise
            self.consecutive_silence_sec = 0.0
            self.consecutive_monologue_sec = 0.0
            state = "HIGH_NOISE_OR_CHATTER"
            audio_engagement_score = 45.0

        elif rms_energy >= self.config.speech_energy_threshold:
            self.consecutive_silence_sec = 0.0
            self.consecutive_monologue_sec += duration_sec

            # If dynamic variation is high, indicates Q&A / lively discussion
            if energy_std > 0.015:
                state = "INTERACTIVE_DISCUSSION_QA"
                audio_engagement_score = min(100.0, 75.0 + (energy_std * 500.0))
            else:
                state = "LECTURE_PRESENTATION"
                # Moderate engagement during direct lecture, slightly decay if monologue is very long
                monologue_penalty = min(25.0, (self.consecutive_monologue_sec / 60.0) * 1.5)
                audio_engagement_score = max(40.0, 80.0 - monologue_penalty)
        else:
            # Low ambient background
            self.consecutive_silence_sec = 0.0
            state = "AMBIENT_NORMAL"
            audio_engagement_score = 55.0

        return {
            "rms_energy": round(rms_energy, 4),
            "energy_variance": round(energy_std, 4),
            "audio_engagement_score": round(float(np.clip(audio_engagement_score, 0.0, 100.0)), 1),
            "acoustic_state": state,
            "consecutive_silence_sec": round(self.consecutive_silence_sec, 1),
            "consecutive_monologue_sec": round(self.consecutive_monologue_sec, 1)
        }

