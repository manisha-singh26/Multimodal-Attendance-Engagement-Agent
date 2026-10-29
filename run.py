"""Classroom Intelligence System Entry Point.
Supports running in Web Dashboard mode or Headless CLI Simulation mode.
"""
import argparse
import sys
import time

if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass
from core.simulator import ClassroomSimulator
from core.attendance_tracker import AttendanceTracker
from core.vision_engine import VisionPerceptionEngine
from core.audio_engine import AudioPerceptionEngine
from core.fusion_engine import MultimodalFusionEngine
from core.teaching_agent import PedagogicalReasoningAgent
from db.database import DatabaseManager
from config import DB_PATH, AttendanceConfig, VisionConfig, AudioConfig, FusionConfig

def run_cli_demo(duration_sec: float = 120.0, step_sec: float = 5.0):
    print("=" * 80)
    print("🚀 MULTIMODAL ATTENDANCE & ENGAGEMENT AGENT - OFFLINE SIMULATION")
    print("=" * 80)
    print(f"Session Duration: {duration_sec}s | Step Interval: {step_sec}s | Local DB: {DB_PATH}")
    print("-" * 80)

    db = DatabaseManager(DB_PATH)
    tracker = AttendanceTracker(AttendanceConfig(window_interval_sec=step_sec))
    vision = VisionPerceptionEngine(VisionConfig())
    audio = AudioPerceptionEngine(AudioConfig())
    fusion = MultimodalFusionEngine(FusionConfig())
    agent = PedagogicalReasoningAgent(alert_cooldown_sec=20.0)
    sim = ClassroomSimulator()

    session_id = f"CLI-DEMO-{int(time.time())}"
    db.create_session(session_id, "Edge Multimodal Classroom Intelligence", "AI-101")
    roster = sim.get_roster()
    tracker.register_roster(roster)
    for s in roster:
        db.enroll_student(s["student_id"], s["display_name"])

    t = 0.0
    while t < duration_sec:
        t += step_sec
        obs = sim.generate_step(t, duration_sec)

        tracker.process_frame_detections(obs["detected_student_ids"], t, step_sec)
        vis_res = vision.process_classroom_frame(obs["visual_detections"], step_sec)
        aud_res = audio.process_audio_chunk(simulated_rms=obs["audio_rms"], duration_sec=step_sec)
        fus_res = fusion.fuse_signals(t, vis_res, aud_res)

        db.record_telemetry(
            session_id=session_id,
            timestamp_sec=t,
            visual_score=fus_res["visual_attention_score"],
            audio_score=fus_res["audio_activity_score"],
            composite_score=fus_res["composite_engagement"],
            active_count=len(obs["detected_student_ids"]),
            state_tag=fus_res["state_tag"],
            student_metrics=vis_res["student_details"]
        )

        sugg = agent.evaluate_dynamics(t, fus_res, vis_res, aud_res)
        if sugg:
            db.add_teaching_suggestion(session_id, t, sugg.category, sugg.severity, sugg.trigger_reason, sugg.suggestion_text)
            print(f"\n[💡 AI AGENT PROMPT @ {t:.0f}s] [{sugg.severity}] {sugg.trigger_reason}")
            print(f"   👉 SUGGESTION: {sugg.suggestion_text}\n")

        print(f"[{t:4.0f}s / {duration_sec:.0f}s] Present: {len(obs['detected_student_ids']):2d}/10 | "
              f"Visual Attn: {fus_res['visual_attention_score']:5.1f}% | "
              f"Audio Act: {fus_res['audio_activity_score']:5.1f}% | "
              f"Composite: {fus_res['composite_engagement']:5.1f}% | "
              f"State: {fus_res['state_tag']}")

    # Finalize
    avg_eng = fusion.get_overall_session_average()
    db.complete_session(session_id, duration_sec, avg_eng)
    final_attendance = tracker.finalize_attendance(duration_sec)

    print("\n" + "=" * 80)
    print("📊 SESSION ATTENDANCE SUMMARY LOG (CONTINUOUS PRESENCE VERIFIED)")
    print("=" * 80)
    print(f"{'STUDENT ID':<12} | {'NAME':<20} | {'STATUS':<10} | {'PRESENCE %':<12} | {'NOTES'}")
    print("-" * 80)
    for a in final_attendance:
        db.record_attendance(session_id, a["student_id"], a["first_seen_sec"], a["last_seen_sec"], 
                             a["total_present_sec"], a["presence_ratio"], a["status"], a["notes"])
        print(f"{a['student_id']:<12} | {a['name']:<20} | {a['status']:<10} | {a['presence_ratio']*100:10.1f}% | {a['notes']}")
    
    print("-" * 80)
    print(f"Overall Average Engagement: {avg_eng}%")
    print(f"Total Pedagogical Insights Generated: {len(agent.suggestion_history)}")
    print(f"Data persisted locally in SQLite: {DB_PATH}")
    print("=" * 80 + "\n")

def main():
    parser = argparse.ArgumentParser(description="Multimodal Attendance & Engagement Agent")
    parser.add_argument("--cli", action="store_true", help="Run in headless terminal simulation mode")
    parser.add_argument("--port", type=int, default=5000, help="Port for the web dashboard (default: 5000)")
    parser.add_argument("--duration", type=float, default=120.0, help="Session duration in seconds for CLI mode")
    args = parser.parse_args()

    if args.cli:
        run_cli_demo(duration_sec=args.duration)
    else:
        from app.server import app
        print(f"Starting Classroom Intelligence Dashboard on http://127.0.0.1:{args.port} (100% Offline Mode)...")
        app.run(host="127.0.0.1", port=args.port, debug=False)

if __name__ == "__main__":
    main()
