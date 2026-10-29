"""Multimodal Classroom Session Simulator.
Generates realistic multi-student behavioral and acoustic streams to test and demonstrate
the attendance tracker, fusion engine, and AI pedagogical agent offline.
"""
import random
import time
from typing import List, Dict, Any, Generator

class StudentProfile:
    def __init__(self, student_id: str, name: str, attendance_type: str, behavior_archetype: str):
        self.student_id = student_id
        self.name = name
        self.attendance_type = attendance_type  # 'REGULAR', 'TARDY', 'ABSENT', 'EARLY_LEAVER'
        self.behavior_archetype = behavior_archetype  # 'HIGH_ATTENTION', 'AVERAGE', 'DISTRACTED_PHONE', 'DROWSY'

class ClassroomSimulator:
    def __init__(self):
        # Default test class roster
        self.students = [
            StudentProfile("STU-101", "Emma Watson", "REGULAR", "HIGH_ATTENTION"),
            StudentProfile("STU-102", "Liam Smith", "REGULAR", "AVERAGE"),
            StudentProfile("STU-103", "Aarav Sharma", "REGULAR", "AVERAGE"),
            StudentProfile("STU-104", "Sophia Chen", "REGULAR", "HIGH_ATTENTION"),
            StudentProfile("STU-105", "Marcus Jones", "TARDY", "AVERAGE"), # Arrives late
            StudentProfile("STU-106", "Chloe Taylor", "REGULAR", "DISTRACTED_PHONE"), # Head tilted down
            StudentProfile("STU-107", "Daniel Kim", "REGULAR", "DROWSY"), # Low motion, head nodding
            StudentProfile("STU-108", "Elena Rodriguez", "EARLY_LEAVER", "AVERAGE"), # Leaves early
            StudentProfile("STU-109", "Noah Patel", "ABSENT", "AVERAGE"), # Never attends
            StudentProfile("STU-110", "Maya Al-Mansoor", "REGULAR", "HIGH_ATTENTION"),
        ]

    def get_roster(self) -> List[Dict[str, str]]:
        return [{"student_id": s.student_id, "display_name": s.name} for s in self.students]

    def generate_step(self, current_time_sec: float, total_duration_sec: float) -> Dict[str, Any]:
        """Generates visual and acoustic observations for a single time slice."""
        progress_ratio = min(1.0, current_time_sec / max(1.0, total_duration_sec))

        # 1. Determine who is physically present in the room
        detected_students = []
        visual_detections = []

        for s in self.students:
            is_present = False
            if s.attendance_type == "REGULAR":
                # Present 95% of frames (occasional 5% occlusion/stepping out)
                is_present = random.random() > 0.05
            elif s.attendance_type == "TARDY":
                # Arrives after 35% of session has passed
                if progress_ratio >= 0.35:
                    is_present = random.random() > 0.05
            elif s.attendance_type == "EARLY_LEAVER":
                # Leaves after 50% of session has passed
                if progress_ratio < 0.50:
                    is_present = random.random() > 0.05
            elif s.attendance_type == "ABSENT":
                is_present = False

            if is_present:
                detected_students.append(s.student_id)

                # Generate behavioral metrics based on archetype
                if s.behavior_archetype == "HIGH_ATTENTION":
                    yaw = random.uniform(-10.0, 10.0)
                    pitch = random.uniform(-8.0, 8.0)
                    motion = random.uniform(0.10, 0.35)
                elif s.behavior_archetype == "DISTRACTED_PHONE":
                    # Looking down at desk / lap
                    yaw = random.uniform(-25.0, 25.0)
                    pitch = random.uniform(30.0, 48.0) # Downward tilt
                    motion = random.uniform(0.15, 0.40)
                elif s.behavior_archetype == "DROWSY":
                    # Head nodding or prolonged zero motion
                    yaw = random.uniform(-15.0, 15.0)
                    pitch = random.uniform(25.0, 40.0)
                    motion = random.uniform(0.01, 0.04) # Barely moving
                else: # AVERAGE
                    yaw = random.uniform(-20.0, 20.0)
                    pitch = random.uniform(-12.0, 18.0)
                    motion = random.uniform(0.10, 0.45)

                # Simulate a mid-session general attention slump around progress 55%-70%
                if 0.55 <= progress_ratio <= 0.70:
                    pitch += random.uniform(10.0, 20.0)
                    motion *= 0.6

                visual_detections.append({
                    "student_id": s.student_id,
                    "yaw_deg": yaw,
                    "pitch_deg": pitch,
                    "motion_energy": motion
                })

        # 2. Simulate Audio dynamics
        # Phase 1 (0-20%): Intro & Lecture
        # Phase 2 (20-40%): Interactive Q&A discussion
        # Phase 3 (40-60%): Long technical monologue (triggers pacing alert)
        # Phase 4 (60-70%): Attention drop-off & side chatter / lull
        # Phase 5 (70-100%): Active recap & discussion
        if progress_ratio < 0.20:
            audio_state = "LECTURE_PRESENTATION"
            rms = random.uniform(0.045, 0.075)
        elif progress_ratio < 0.40:
            audio_state = "INTERACTIVE_DISCUSSION_QA"
            rms = random.uniform(0.060, 0.120)
        elif progress_ratio < 0.60:
            # Monologue
            audio_state = "LECTURE_PRESENTATION"
            rms = random.uniform(0.040, 0.065)
        elif progress_ratio < 0.70:
            # Drop-off + silence / murmur
            if random.random() < 0.5:
                audio_state = "SILENCE_OR_PAUSE"
                rms = random.uniform(0.002, 0.006)
            else:
                audio_state = "HIGH_NOISE_OR_CHATTER"
                rms = random.uniform(0.19, 0.24)
        else:
            audio_state = "INTERACTIVE_DISCUSSION_QA"
            rms = random.uniform(0.065, 0.130)

        return {
            "timestamp_sec": current_time_sec,
            "detected_student_ids": detected_students,
            "visual_detections": visual_detections,
            "audio_rms": rms,
            "simulated_acoustic_state": audio_state
        }

