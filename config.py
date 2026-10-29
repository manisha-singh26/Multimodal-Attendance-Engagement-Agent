"""System Configuration for Multimodal Attendance & Engagement Agent.
All parameters are tuned for offline, low-latency, privacy-preserving execution.
"""
from dataclasses import dataclass
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "db", "classroom_intel.db")

@dataclass
class AttendanceConfig:
    # Minimum ratio of session windows a student must be present to be marked PRESENT (e.g. 75%)
    min_presence_ratio: float = 0.70
    # Minimum continuous presence duration in seconds to avoid transient false positives
    min_sustained_seconds: float = 60.0
    # Tardy threshold: arriving after this percentage of session has elapsed
    tardy_threshold_ratio: float = 0.20
    # Window analysis interval (in seconds)
    window_interval_sec: float = 5.0

@dataclass
class VisionConfig:
    # Head pose pitch/yaw tolerance in degrees (looking forward vs. distracted)
    max_yaw_dev_deg: float = 30.0
    max_pitch_dev_deg: float = 25.0
    # Inactivity threshold in seconds (motionless / sleeping / frozen)
    inactivity_seconds_threshold: float = 45.0
    # High motion threshold (restlessness / fidgeting)
    excessive_motion_threshold: float = 0.85

@dataclass
class AudioConfig:
    # Audio sampling rate
    sample_rate: int = 16000
    # RMS Energy threshold for detecting speech vs ambient background noise
    speech_energy_threshold: float = 0.035
    # Silence energy threshold
    silence_energy_threshold: float = 0.008
    # Window duration in seconds
    audio_chunk_sec: float = 2.0

@dataclass
class FusionConfig:
    # Weight of visual attention in overall engagement (0.0 to 1.0)
    visual_weight: float = 0.65
    # Weight of audio interactivity in overall engagement (0.0 to 1.0)
    audio_weight: float = 0.35
    # Engagement drop-off threshold (drop by >= 20% compared to rolling baseline)
    dropoff_threshold: float = 0.20
    # Pacing alert: monologue duration in minutes before triggering warning
    max_monologue_minutes: float = 12.0

@dataclass
class PrivacyConfig:
    # Anonymize student names in logs and visual outputs (e.g. Student_01 instead of real names)
    anonymize_identifiers: bool = False
    # Retain raw video frames on disk (False = immediate memory discard after feature extraction)
    save_raw_video: bool = False
    # Offline mode enforced
    enforce_offline: bool = True

