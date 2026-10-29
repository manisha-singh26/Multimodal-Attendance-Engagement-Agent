"""Streamlit Web Application for Multimodal Attendance & Engagement Agent.
Enables 1-click cloud deployment via Streamlit Community Cloud or local edge serving.
"""
import streamlit as st
import pandas as pd
import numpy as np
import time
import json
import os
import uuid

from config import DB_PATH, AttendanceConfig, VisionConfig, AudioConfig, FusionConfig
from db.database import DatabaseManager
from core.attendance_tracker import AttendanceTracker
from core.vision_engine import VisionPerceptionEngine
from core.audio_engine import AudioPerceptionEngine
from core.fusion_engine import MultimodalFusionEngine
from core.teaching_agent import PedagogicalReasoningAgent
from core.simulator import ClassroomSimulator

# Page configuration
st.set_page_config(
    page_title="Classroom Intelligence Agent",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom Styling
st.markdown("""
<style>
    .metric-card {
        background-color: #1e293b;
        border-radius: 10px;
        padding: 15px;
        border: 1px solid #334155;
    }
    .badge-privacy {
        background-color: #064e3b;
        color: #34d399;
        padding: 4px 10px;
        border-radius: 12px;
        font-size: 0.75rem;
        font-weight: bold;
    }
    .badge-state {
        padding: 4px 10px;
        border-radius: 6px;
        font-weight: bold;
        font-size: 0.85rem;
    }
    .stAlert {
        border-radius: 8px;
    }
</style>
""", unsafe_allow_html=True)

# Initialize Local Database
db = DatabaseManager(DB_PATH)

# --- Sidebar Controls ---
st.sidebar.title("🎓 Classroom AI Co-Pilot")
st.sidebar.markdown('<span class="badge-privacy">🔒 100% Offline Edge Mode</span>', unsafe_allow_html=True)
st.sidebar.markdown("---")

anonymize_mode = st.sidebar.toggle("Privacy Anonymizer", value=False, help="Mask student names and IDs in visualizations and exports")

st.sidebar.subheader("Session Configuration")
course_name = st.sidebar.text_input("Course Code", value="CS-402: Computer Vision")
session_title = st.sidebar.text_input("Lecture Title", value="Visual Dynamics & Attention")
session_duration = st.sidebar.slider("Session Duration (Seconds)", min_value=30, max_value=600, value=120, step=15)
step_interval = st.sidebar.slider("Sampling Interval (Seconds)", min_value=2, max_value=10, value=5, step=1)

# Session State Storage
if "telemetry_records" not in st.session_state:
    st.session_state.telemetry_records = []
if "suggestions" not in st.session_state:
    st.session_state.suggestions = []
if "attendance_records" not in st.session_state:
    st.session_state.attendance_records = []
if "active_session_id" not in st.session_state:
    st.session_state.active_session_id = None
if "latest_visual_details" not in st.session_state:
    st.session_state.latest_visual_details = {}

def reset_session_state():
    st.session_state.telemetry_records = []
    st.session_state.suggestions = []
    st.session_state.attendance_records = []
    st.session_state.active_session_id = None
    st.session_state.latest_visual_details = {}

# Sidebar Actions
col_btn1, col_btn2 = st.sidebar.columns(2)
run_fast_sim = col_btn1.button("⚡ Run Full Sim", use_container_width=True, type="primary")
reset_btn = col_btn2.button("🔄 Reset", use_container_width=True)

if reset_btn:
    reset_session_state()
    st.rerun()

# Execution Pipeline Logic
def execute_simulation(is_live: bool = False):
    session_id = f"SESS-{uuid.uuid4().hex[:6].upper()}"
    st.session_state.active_session_id = session_id

    # Instantiate Engines
    tracker = AttendanceTracker(AttendanceConfig(window_interval_sec=step_interval))
    vision = VisionPerceptionEngine(VisionConfig())
    audio = AudioPerceptionEngine(AudioConfig())
    fusion = MultimodalFusionEngine(FusionConfig())
    agent = PedagogicalReasoningAgent(alert_cooldown_sec=25.0)
    sim = ClassroomSimulator()

    db.create_session(session_id, session_title, course_name)
    roster = sim.get_roster()
    tracker.register_roster(roster)
    for s in roster:
        db.enroll_student(s["student_id"], s["display_name"])

    telemetry = []
    suggestions = []

    progress_bar = st.progress(0, text="Analyzing classroom multimodal dynamics...")

    t = 0.0
    while t < session_duration:
        t += step_interval
        obs = sim.generate_step(t, session_duration)

        # Track Attendance
        tracker.process_frame_detections(obs["detected_student_ids"], t, step_interval)

        # Vision & Audio Perception
        vis_res = vision.process_classroom_frame(obs["visual_detections"], step_interval)
        aud_res = audio.process_audio_chunk(simulated_rms=obs["audio_rms"], duration_sec=step_interval)

        # Fusion
        fus_res = fusion.fuse_signals(t, vis_res, aud_res)

        # Agent Reasoning
        sugg = agent.evaluate_dynamics(t, fus_res, vis_res, aud_res)
        if sugg:
            s_dict = {
                "category": sugg.category,
                "severity": sugg.severity,
                "trigger_reason": sugg.trigger_reason,
                "suggestion_text": sugg.suggestion_text,
                "timestamp_sec": round(t, 1)
            }
            suggestions.append(s_dict)
            db.add_teaching_suggestion(session_id, t, sugg.category, sugg.severity, sugg.trigger_reason, sugg.suggestion_text)

        # Save Telemetry
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

        telemetry.append({
            "Time (s)": round(t, 1),
            "Composite Engagement (%)": fus_res["composite_engagement"],
            "Visual Attention (%)": fus_res["visual_attention_score"],
            "Audio Activity (%)": fus_res["audio_activity_score"],
            "State": fus_res["state_tag"],
            "Present Count": len(obs["detected_student_ids"]),
            "Acoustic State": aud_res["acoustic_state"]
        })

        st.session_state.latest_visual_details = vis_res.get("student_details", {})
        progress_bar.progress(min(1.0, t / session_duration))
        if is_live:
            time.sleep(0.05)

    progress_bar.empty()

    # Complete session
    avg_eng = fusion.get_overall_session_average()
    db.complete_session(session_id, session_duration, avg_eng)
    final_att = tracker.finalize_attendance(session_duration)

    for a in final_att:
        db.record_attendance(
            session_id=session_id,
            student_id=a["student_id"],
            first_seen_sec=a["first_seen_sec"],
            last_seen_sec=a["last_seen_sec"],
            total_present_sec=a["total_present_sec"],
            presence_ratio=a["presence_ratio"],
            status=a["status"],
            notes=a["notes"]
        )

    st.session_state.telemetry_records = telemetry
    st.session_state.suggestions = suggestions
    st.session_state.attendance_records = db.get_session_attendance(session_id, anonymize=anonymize_mode)

if run_fast_sim:
    execute_simulation(is_live=False)

# Historical sessions dropdown in sidebar
st.sidebar.markdown("---")
st.sidebar.subheader("Historical Sessions")
past_sessions = db.list_sessions()
session_options = {f"{s['session_id']} - {s['title']}": s['session_id'] for s in past_sessions}
selected_past = st.sidebar.selectbox("Load Previous Run", options=["-- Select --"] + list(session_options.keys()))

if selected_past != "-- Select --":
    past_id = session_options[selected_past]
    st.session_state.active_session_id = past_id
    raw_telemetry = db.get_session_telemetry(past_id)
    st.session_state.telemetry_records = [
        {
            "Time (s)": r["timestamp_sec"],
            "Composite Engagement (%)": r["composite_engagement"],
            "Visual Attention (%)": r["visual_attention_score"],
            "Audio Activity (%)": r["audio_activity_score"],
            "State": r["state_tag"],
            "Present Count": r["active_participants"],
            "Acoustic State": "LECTURE"
        }
        for r in raw_telemetry
    ]
    st.session_state.suggestions = db.get_session_suggestions(past_id)
    st.session_state.attendance_records = db.get_session_attendance(past_id, anonymize=anonymize_mode)

# --- Main Dashboard UI ---
st.title("Multimodal Attendance & Engagement Agent")
st.caption(f"Session: **{session_title}** ({course_name}) | Local Database: `classroom_intel.db`")

# 1. Top Metrics Cards
if st.session_state.telemetry_records:
    latest = st.session_state.telemetry_records[-1]
    att_records = st.session_state.attendance_records
    
    total_stu = len(att_records) or 10
    present_cnt = sum(1 for a in att_records if a.get("status") == "PRESENT")
    tardy_cnt = sum(1 for a in att_records if a.get("status") == "TARDY")
    absent_cnt = sum(1 for a in att_records if a.get("status") == "ABSENT")
    att_rate = round(((present_cnt + tardy_cnt) / max(1, total_stu)) * 100, 1)

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Attendance Rate", f"{att_rate}%", f"{present_cnt} Present, {tardy_cnt} Tardy")
    c2.metric("Composite Engagement", f"{latest['Composite Engagement (%)']}%", f"Visual: {latest['Visual Attention (%)']}%")
    c3.metric("Classroom State", latest["State"], f"Tracking {latest['Present Count']} active")
    c4.metric("Audio Dynamic", latest.get("Acoustic State", "NORMAL"), f"Activity: {latest['Audio Activity (%)']}%")
else:
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Attendance Rate", "--%", "Run simulation")
    c2.metric("Composite Engagement", "--%", "Visual + Audio")
    c3.metric("Classroom State", "READY", "Awaiting input")
    c4.metric("Audio Dynamic", "--", "--")

st.markdown("---")

# 2. Multimodal Fusion Timeline Chart
st.subheader("📈 Multimodal Engagement & Attention Dynamics Timeline")
if st.session_state.telemetry_records:
    df_chart = pd.DataFrame(st.session_state.telemetry_records)
    st.line_chart(
        df_chart,
        x="Time (s)",
        y=["Composite Engagement (%)", "Visual Attention (%)", "Audio Activity (%)"],
        color=["#38bdf8", "#22c55e", "#f59e0b"]
    )
else:
    st.info("💡 Click **'⚡ Run Full Sim'** in the sidebar to simulate a multi-student multimodal classroom session.")

# 3. Tabs for Deep Analytics
tab_students, tab_agent, tab_attendance = st.tabs([
    "👥 Student Behavioral Grid",
    "💡 AI Teaching Suggestions",
    "📋 Automated Attendance Log & Export"
])

with tab_students:
    st.markdown("### Real-Time Student Behavioral Attention & Posture")
    vis_details = st.session_state.latest_visual_details
    if vis_details:
        cols = st.columns(5)
        idx = 0
        for s_id, metrics in vis_details.items():
            col = cols[idx % 5]
            display_name = f"Student {s_id}" if anonymize_mode else s_id
            with col:
                st.markdown(f"""
                <div class="metric-card">
                    <h4>{display_name}</h4>
                    <p><strong>Attention:</strong> {metrics['attention_score']}%</p>
                    <p><small><strong>Pose:</strong> {metrics['state_label']}</small></p>
                    <p><small>Yaw: {metrics['yaw']}° | Pitch: {metrics['pitch']}°</small></p>
                </div>
                <br>
                """, unsafe_allow_html=True)
            idx += 1
    else:
        st.write("No active frame details yet. Run a simulation to display per-student posture and gaze metrics.")

with tab_agent:
    st.markdown("### AI Pedagogical Decision-Support Feed")
    suggs = st.session_state.suggestions
    if suggs:
        for s in reversed(suggs):
            severity = s.get("severity", "INFO")
            t_sec = s.get("timestamp_sec", 0)
            reason = s.get("trigger_reason", "")
            text = s.get("suggestion_text", "")

            if severity == "ACTION_REQUIRED":
                st.error(f"🚨 **[{severity}] @ {t_sec}s** — {reason}\n\n👉 **Pedagogical Action:** {text}")
            elif severity == "WARNING":
                st.warning(f"⚠️ **[{severity}] @ {t_sec}s** — {reason}\n\n👉 **Pedagogical Action:** {text}")
            else:
                st.info(f"💡 **[{severity}] @ {t_sec}s** — {reason}\n\n👉 **Affirmation:** {text}")
    else:
        st.write("No pedagogical triggers generated yet.")

with tab_attendance:
    st.markdown("### Automated Attendance Records (Continuous Presence Verified)")
    att = st.session_state.attendance_records
    if att:
        df_att = pd.DataFrame(att)
        # Select and format columns
        columns_to_show = ["student_id", "display_name", "status", "presence_ratio", "total_present_sec", "notes"]
        existing_cols = [c for c in columns_to_show if c in df_att.columns]
        df_display = df_att[existing_cols].copy()
        
        if "presence_ratio" in df_display.columns:
            df_display["presence_ratio"] = (df_display["presence_ratio"] * 100).round(1).astype(str) + "%"
        if "total_present_sec" in df_display.columns:
            df_display["total_present_sec"] = df_display["total_present_sec"].round(1).astype(str) + "s"

        st.dataframe(df_display, use_container_width=True)

        # Export Buttons
        col_exp1, col_exp2 = st.columns(2)
        csv_data = df_att.to_csv(index=False).encode('utf-8')
        col_exp1.download_button(
            label="📥 Download Attendance CSV",
            data=csv_data,
            file_name=f"attendance_{st.session_state.active_session_id}.csv",
            mime="text/csv",
            use_container_width=True
        )

        json_summary = json.dumps({
            "session_id": st.session_state.active_session_id,
            "telemetry": st.session_state.telemetry_records,
            "suggestions": st.session_state.suggestions,
            "attendance": att
        }, indent=2)
        col_exp2.download_button(
            label="📄 Download Full Session JSON",
            data=json_summary,
            file_name=f"summary_{st.session_state.active_session_id}.json",
            mime="application/json",
            use_container_width=True
        )
    else:
        st.write("No attendance logs recorded yet.")

