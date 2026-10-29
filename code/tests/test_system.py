"""Comprehensive Unit & Pipeline Integration Tests.
Validates attendance tracking logic, multimodal fusion, agent suggestions, and database storage.
"""
import unittest
import os
import tempfile
import sqlite3
from config import AttendanceConfig, VisionConfig, AudioConfig, FusionConfig
from core.attendance_tracker import AttendanceTracker
from core.vision_engine import VisionPerceptionEngine
from core.audio_engine import AudioPerceptionEngine
from core.fusion_engine import MultimodalFusionEngine
from core.teaching_agent import PedagogicalReasoningAgent
from core.simulator import ClassroomSimulator
from db.database import DatabaseManager

class TestMultimodalAttendanceAndEngagement(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.test_db_path = os.path.join(tempfile.gettempdir(), "test_classroom_intel.db")

    def setUp(self):
        if os.path.exists(self.test_db_path):
            try:
                os.remove(self.test_db_path)
            except OSError:
                pass
        self.db = DatabaseManager(self.test_db_path)

    def test_attendance_sustained_presence(self):
        """Test continuous presence vs momentary false positive vs tardy arrival."""
        # Config: min 50% presence ratio, min 40s sustained
        config = AttendanceConfig(min_presence_ratio=0.60, min_sustained_seconds=40.0, tardy_threshold_ratio=0.15)
        tracker = AttendanceTracker(config)
        tracker.register_roster([
            {"student_id": "S1", "display_name": "Alice Regular"},
            {"student_id": "S2", "display_name": "Bob Passerby"},
            {"student_id": "S3", "display_name": "Charlie Tardy"}
        ])

        # Simulate 100 seconds session (20 steps of 5 seconds each)
        for step in range(20):
            t = (step + 1) * 5.0
            detected = []
            # S1 present all 20 steps (100s)
            detected.append("S1")
            # S2 only seen for step 0 and 1 (10s total -> passerby)
            if step < 2:
                detected.append("S2")
            # S3 arrives at step 5 (t=25s, past 15s tardy cutoff) and stays until the end (75s total)
            if step >= 5:
                detected.append("S3")

            tracker.process_frame_detections(detected, t, 5.0)

        results = tracker.finalize_attendance(100.0)
        lookup = {r["student_id"]: r for r in results}

        # Alice met sustained presence (100% presence)
        self.assertEqual(lookup["S1"]["status"], "PRESENT")
        self.assertAlmostEqual(lookup["S1"]["presence_ratio"], 1.0)

        # Bob only attended 10s (< 40s sustained threshold) -> ABSENT
        self.assertEqual(lookup["S2"]["status"], "ABSENT")

        # Charlie attended 75s (75% >= 60%), but first seen at 25s (cutoff was 15s) -> TARDY
        self.assertEqual(lookup["S3"]["status"], "TARDY")
        self.assertAlmostEqual(lookup["S3"]["presence_ratio"], 0.75)

    def test_visual_attention_scoring(self):
        """Test head pose penalty and inactivity scoring."""
        engine = VisionPerceptionEngine(VisionConfig())
        # Student 1 looking forward towards instructor
        # Student 2 looking heavily down at smartphone
        frame_input = [
            {"student_id": "S1", "yaw_deg": 4.0, "pitch_deg": 2.0, "motion_energy": 0.20},
            {"student_id": "S2", "yaw_deg": 22.0, "pitch_deg": 42.0, "motion_energy": 0.15}
        ]
        res = engine.process_classroom_frame(frame_input, interval_sec=5.0)
        s1_score = res["student_details"]["S1"]["attention_score"]
        s2_score = res["student_details"]["S2"]["attention_score"]

        self.assertGreater(s1_score, s2_score)
        self.assertEqual(res["student_details"]["S1"]["state_label"], "ATTENTIVE")

    def test_audio_engine_states(self):
        """Test audio state detection for speech, silence, and chatter."""
        audio = AudioPerceptionEngine()
        # Test silence
        silence_res = audio.process_audio_chunk(simulated_rms=0.002, duration_sec=5.0)
        self.assertEqual(silence_res["acoustic_state"], "SILENCE_OR_PAUSE")

        # Test speech
        speech_res = audio.process_audio_chunk(simulated_rms=0.05, duration_sec=5.0)
        self.assertIn(speech_res["acoustic_state"], ["LECTURE_PRESENTATION", "INTERACTIVE_DISCUSSION_QA"])

    def test_multimodal_fusion_and_dropoff(self):
        """Test fusion weighted combination and drop-off alarm."""
        fusion = MultimodalFusionEngine(FusionConfig(visual_weight=0.6, audio_weight=0.4, dropoff_threshold=0.20))
        # Warmup high baseline
        for i in range(5):
            fusion.fuse_signals(
                timestamp_sec=i * 5.0,
                visual_metrics={"avg_visual_attention": 85.0},
                audio_metrics={"audio_engagement_score": 80.0, "acoustic_state": "LECTURE_PRESENTATION"}
            )

        # Abrupt crash in attention
        drop_res = fusion.fuse_signals(
            timestamp_sec=30.0,
            visual_metrics={"avg_visual_attention": 30.0},
            audio_metrics={"audio_engagement_score": 25.0, "acoustic_state": "SILENCE_OR_PAUSE"}
        )
        self.assertTrue(drop_res["is_dropoff"])
        self.assertGreater(drop_res["dropoff_magnitude_percent"], 20.0)

    def test_pedagogical_agent_triggers(self):
        """Test that AI agent produces actionable pedagogical suggestions."""
        agent = PedagogicalReasoningAgent(alert_cooldown_sec=10.0)

        # Simulate drop-off trigger
        fusion_metrics = {"composite_engagement": 42.0, "is_dropoff": True, "dropoff_magnitude_percent": 35.0}
        vis_metrics = {"avg_visual_attention": 40.0}
        aud_metrics = {"consecutive_monologue_sec": 0.0, "consecutive_silence_sec": 0.0, "acoustic_state": "NORMAL"}

        sugg = agent.evaluate_dynamics(50.0, fusion_metrics, vis_metrics, aud_metrics)
        self.assertIsNotNone(sugg)
        self.assertEqual(sugg.category, "DROP_OFF")
        self.assertEqual(sugg.severity, "ACTION_REQUIRED")
        self.assertIn("Engagement Dip Detected", sugg.suggestion_text)

    def test_database_persistence_and_export(self):
        """Test SQLite storage, roster enrollment, telemetry, and export."""
        self.db.enroll_student("STU-1", "Jane Doe")
        self.db.create_session("SESS-001", "Introduction to ML", "CS101", "Dr. Turing")

        self.db.record_telemetry("SESS-001", 10.0, 80.0, 75.0, 78.0, 1, "ATTENTIVE", {"STU-1": {"score": 80}})
        self.db.add_teaching_suggestion("SESS-001", 10.0, "PACING", "WARNING", "Monologue", "Consider asking a question")
        self.db.record_attendance("SESS-001", "STU-1", 0.0, 100.0, 95.0, 0.95, "PRESENT", "Regular attendee")

        summary = self.db.export_session_summary("SESS-001")
        self.assertEqual(summary["metrics"]["total_enrolled"], 1)
        self.assertEqual(summary["metrics"]["present_count"], 1)
        self.assertEqual(len(summary["suggestions"]), 1)

if __name__ == "__main__":
    unittest.main()
