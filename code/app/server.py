"""Flask Application Server & Local REST API.
Serves the educator analytics dashboard, controls live/simulated sessions,
and handles exportable reports completely offline.
"""
import os
import json
import uuid
from flask import Flask, render_template, request, jsonify, send_file, Response
from config import BASE_DIR, DB_PATH, AttendanceConfig, VisionConfig, AudioConfig, FusionConfig, PrivacyConfig
from db.database import DatabaseManager
from core.attendance_tracker import AttendanceTracker
from core.vision_engine import VisionPerceptionEngine
from core.audio_engine import AudioPerceptionEngine
from core.fusion_engine import MultimodalFusionEngine
from core.teaching_agent import PedagogicalReasoningAgent
from core.simulator import ClassroomSimulator

app = Flask(
    __name__,
    template_folder=os.path.join(BASE_DIR, "app", "templates"),
    static_folder=os.path.join(BASE_DIR, "app", "static")
)

db = DatabaseManager(DB_PATH)
privacy_cfg = PrivacyConfig()

# In-memory active session runtime controller
class ActiveSessionRunner:
    def __init__(self, session_id: str, title: str, course: str, total_duration_sec: float = 300.0, step_interval_sec: float = 5.0):
        self.session_id = session_id
        self.title = title
        self.course = course
        self.total_duration_sec = total_duration_sec
        self.step_interval_sec = step_interval_sec
        self.current_time_sec = 0.0

        # Initialize Core Engines
        self.attendance_cfg = AttendanceConfig(window_interval_sec=step_interval_sec)
        self.vision_cfg = VisionConfig()
        self.audio_cfg = AudioConfig()
        self.fusion_cfg = FusionConfig()

        self.tracker = AttendanceTracker(self.attendance_cfg)
        self.vision_engine = VisionPerceptionEngine(self.vision_cfg)
        self.audio_engine = AudioPerceptionEngine(self.audio_cfg)
        self.fusion_engine = MultimodalFusionEngine(self.fusion_cfg)
        self.teaching_agent = PedagogicalReasoningAgent(alert_cooldown_sec=30.0)
        self.simulator = ClassroomSimulator()

        # Enroll roster in DB and tracker
        roster = self.simulator.get_roster()
        for s in roster:
            db.enroll_student(s["student_id"], s["display_name"])
        self.tracker.register_roster(roster)

        db.create_session(self.session_id, self.title, self.course)
        self.is_completed = False

    def step(self) -> dict:
        if self.current_time_sec >= self.total_duration_sec:
            self.complete()
            return {"status": "COMPLETED", "session_id": self.session_id}

        self.current_time_sec += self.step_interval_sec

        # 1. Generate multi-student and acoustic inputs
        obs = self.simulator.generate_step(self.current_time_sec, self.total_duration_sec)

        # 2. Process Attendance Tracking
        self.tracker.process_frame_detections(
            detected_student_ids=obs["detected_student_ids"],
            timestamp_sec=self.current_time_sec,
            interval_sec=self.step_interval_sec
        )

        # 3. Process Visual Perception
        vis_metrics = self.vision_engine.process_classroom_frame(
            student_detections=obs["visual_detections"],
            interval_sec=self.step_interval_sec
        )

        # 4. Process Audio Perception
        aud_metrics = self.audio_engine.process_audio_chunk(
            simulated_rms=obs["audio_rms"],
            duration_sec=self.step_interval_sec
        )

        # 5. Multimodal Signal Fusion
        fusion_metrics = self.fusion_engine.fuse_signals(
            timestamp_sec=self.current_time_sec,
            visual_metrics=vis_metrics,
            audio_metrics=aud_metrics
        )

        # 6. AI Pedagogical Agent Reasoning
        new_suggestion = self.teaching_agent.evaluate_dynamics(
            timestamp_sec=self.current_time_sec,
            fusion_metrics=fusion_metrics,
            visual_metrics=vis_metrics,
            audio_metrics=aud_metrics
        )

        # Persist to local database
        db.record_telemetry(
            session_id=self.session_id,
            timestamp_sec=self.current_time_sec,
            visual_score=fusion_metrics["visual_attention_score"],
            audio_score=fusion_metrics["audio_activity_score"],
            composite_score=fusion_metrics["composite_engagement"],
            active_count=len(obs["detected_student_ids"]),
            state_tag=fusion_metrics["state_tag"],
            student_metrics=vis_metrics["student_details"]
        )

        suggestion_dict = None
        if new_suggestion:
            s_id = db.add_teaching_suggestion(
                session_id=self.session_id,
                timestamp_sec=self.current_time_sec,
                category=new_suggestion.category,
                severity=new_suggestion.severity,
                trigger_reason=new_suggestion.trigger_reason,
                suggestion_text=new_suggestion.suggestion_text
            )
            suggestion_dict = {
                "id": s_id,
                "category": new_suggestion.category,
                "severity": new_suggestion.severity,
                "trigger_reason": new_suggestion.trigger_reason,
                "suggestion_text": new_suggestion.suggestion_text,
                "timestamp_sec": self.current_time_sec
            }

        return {
            "status": "RUNNING",
            "session_id": self.session_id,
            "timestamp_sec": self.current_time_sec,
            "progress_percent": round((self.current_time_sec / self.total_duration_sec) * 100, 1),
            "telemetry": fusion_metrics,
            "visual_details": vis_metrics,
            "audio_details": aud_metrics,
            "attendance_summary": self.tracker.get_live_summary(),
            "latest_suggestion": suggestion_dict
        }

    def complete(self):
        if self.is_completed:
            return
        self.is_completed = True
        avg_eng = self.fusion_engine.get_overall_session_average()
        db.complete_session(self.session_id, self.total_duration_sec, avg_eng)

        # Finalize and persist attendance
        final_attendance = self.tracker.finalize_attendance(self.total_duration_sec)
        for att in final_attendance:
            db.record_attendance(
                session_id=self.session_id,
                student_id=att["student_id"],
                first_seen_sec=att["first_seen_sec"],
                last_seen_sec=att["last_seen_sec"],
                total_present_sec=att["total_present_sec"],
                presence_ratio=att["presence_ratio"],
                status=att["status"],
                notes=att["notes"]
            )

active_runner: Optional[ActiveSessionRunner] = None

# --- UI & API Routes ---
@app.route("/")
def index():
    return render_template("index.html")

@app.route("/api/sessions", methods=["GET"])
def get_sessions():
    sessions = db.list_sessions()
    return jsonify({"sessions": sessions})

@app.route("/api/sessions/start", methods=["POST"])
def start_session():
    global active_runner
    data = request.json or {}
    session_id = data.get("session_id", f"SESS-{uuid.uuid4().hex[:6].upper()}")
    title = data.get("title", "Computer Vision & Cognitive Science")
    course = data.get("course", "AI-402")
    duration = float(data.get("duration_sec", 300.0))
    step = float(data.get("step_sec", 5.0))

    active_runner = ActiveSessionRunner(session_id, title, course, duration, step)
    return jsonify({
        "status": "STARTED",
        "session_id": session_id,
        "title": title,
        "course": course,
        "duration_sec": duration
    })

@app.route("/api/sessions/step", methods=["POST"])
def step_session():
    global active_runner
    if not active_runner:
        return jsonify({"error": "No active session. Please start a session first."}), 400
    res = active_runner.step()
    return jsonify(res)

@app.route("/api/sessions/run_full_sim", methods=["POST"])
def run_full_simulation():
    global active_runner
    data = request.json or {}
    session_id = data.get("session_id", f"SESS-{uuid.uuid4().hex[:6].upper()}")
    title = data.get("title", "Interactive Data Systems & Analytics")
    course = data.get("course", "CS-520")
    duration = float(data.get("duration_sec", 180.0))
    step = float(data.get("step_sec", 5.0))

    runner = ActiveSessionRunner(session_id, title, course, duration, step)
    while not runner.is_completed:
        step_res = runner.step()
        if step_res.get("status") == "COMPLETED":
            break

    active_runner = runner
    summary = db.export_session_summary(session_id)
    return jsonify({
        "status": "COMPLETED",
        "session_id": session_id,
        "summary": summary
    })

@app.route("/api/sessions/<session_id>", methods=["GET"])
def get_session_details(session_id):
    anonymize = privacy_cfg.anonymize_identifiers
    summary = db.export_session_summary(session_id)
    if not summary:
        return jsonify({"error": "Session not found"}), 404
    telemetry = db.get_session_telemetry(session_id)
    summary["telemetry"] = telemetry
    if anonymize:
        summary["attendance"] = db.get_session_attendance(session_id, anonymize=True)
    return jsonify(summary)

@app.route("/api/sessions/<session_id>/export_csv", methods=["GET"])
def export_csv(session_id):
    csv_filename = f"attendance_{session_id}.csv"
    temp_path = os.path.join(BASE_DIR, "db", csv_filename)
    db.export_attendance_csv(session_id, temp_path)
    return send_file(temp_path, as_attachment=True, download_name=csv_filename, mimetype="text/csv")

@app.route("/api/settings/privacy", methods=["POST"])
def toggle_privacy():
    global privacy_cfg
    data = request.json or {}
    privacy_cfg.anonymize_identifiers = bool(data.get("anonymize", False))
    return jsonify({
        "status": "UPDATED",
        "anonymize_identifiers": privacy_cfg.anonymize_identifiers
    })

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)

