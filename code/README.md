# Multimodal Attendance & Engagement Agent

An AI-powered, privacy-preserving classroom intelligence system designed to automate attendance tracking, analyze multimodal student engagement dynamics, and provide actionable pedagogical recommendations — **operating 100% offline to protect student privacy**.

---

## 🌟 Key Capabilities

1. **Automated Continuous-Presence Attendance Tracker (`core/attendance_tracker.py`)**
   - Eliminates single-frame false positives via configurable sliding windows.
   - Requires continuous sustained presence ($t \ge \text{min\_sustained\_seconds}$) and session ratio ($r \ge 70\%$).
   - Automatically classifies participants as **PRESENT**, **TARDY** (late arrivals), or **ABSENT**.

2. **Visual Behavioral Perception Engine (`core/vision_engine.py`)**
   - Monitors head pose orientation (yaw & pitch deviations).
   - Detects screen/board gaze attention vs. downward tilt (e.g., looking at smartphone).
   - Evaluates frame-to-frame motion energy and flags prolonged physical inactivity / dozing.

3. **Audio Signal Perception Engine (`core/audio_engine.py`)**
   - Analyzes Root-Mean-Square (RMS) acoustic energy.
   - Detects vocal dynamics: distinguishes interactive Q&A discussion, continuous lecture monologue, dead silence, and ambient disruptive chatter.

4. **Multimodal Fusion Engine (`core/fusion_engine.py`)**
   - Fuses visual attention ($V_t$) and audio interactivity ($A_t$) into a composite Engagement Index $E_t \in [0, 100\%]$.
   - Dynamically flags attention drop-offs ($\ge 20\%$ sudden slump) and classifies classroom states.

5. **AI Pedagogical Reasoning Agent (`core/teaching_agent.py`)**
   - Non-intrusive decision-support agent running completely offline.
   - Provides real-time pedagogical prompts (e.g., flagging $>10$ min monologues, recommending Think-Pair-Share or formative polls when energy drops).

6. **Privacy-First Local Storage (`db/database.py`)**
   - Zero external cloud calls or data leakage.
   - Local SQLite database (`db/classroom_intel.db`) storing sessions, telemetry, suggestions, and attendance.
   - Built-in one-click anonymization hashing for student identifiers.

7. **Educator Analytics Web Dashboard (`app/server.py`)**
   - Modern, responsive local web interface.
   - Real-time multimodal timeline chart, student attention grid, live agent suggestion feed, and exportable attendance reports (CSV / JSON).

---

## 📁 Repository Structure

```
├── config.py                 # System thresholds, weights, & privacy settings
├── requirements.txt          # Python dependencies (Flask, NumPy)
├── README.md
├── run.py                    # Entry point: start web dashboard or CLI demo
├── core/
│   ├── attendance_tracker.py # Continuous presence tracking logic
│   ├── vision_engine.py      # Head pose, gaze & motion dynamics
│   ├── audio_engine.py       # Acoustic RMS, speech vs. silence/noise
│   ├── fusion_engine.py      # Multimodal weighted fusion & drop-off detection
│   ├── teaching_agent.py     # AI pedagogical decision-support agent
│   └── simulator.py          # Realistic multi-student classroom generator
├── db/
│   └── database.py           # Local SQLite storage & CSV/JSON exporter
├── app/
│   ├── server.py             # Flask application & REST API
│   ├── templates/
│   │   └── index.html        # Interactive Educator Analytics Dashboard
│   └── static/
│       ├── css/style.css     # Clean dark/light modern UI styles
│       └── js/dashboard.js   # Live charts & telemetry updates
└── tests/
    └── test_system.py        # Automated test suite (6/6 passing)
```

---

## 🚀 Quickstart

### 1. Run the Interactive Web Dashboard

Launch the local web server:

```bash
python run.py --port 5000
```

Then open your browser at:
👉 **`http://127.0.0.1:5000`**

From the dashboard you can:
- Click **"▶ Run Full Session Demo"** to simulate and analyze a complete lecture in seconds.
- Click **"⚡ Start Live Stream"** to watch the real-time telemetry, live student attention grid, and AI suggestions stream in every 5 seconds.
- Toggle **"Privacy Anonymizer"** to mask student names and IDs in real-time.
- Click **"📥 Export CSV"** or **"📄 Export JSON"** to download the official attendance and telemetry logs.

---

### 2. Run Headless CLI Simulation

You can also run an offline session simulation directly from your terminal:

```bash
python run.py --cli --duration 120
```

---

### 3. Run Automated Tests

To run the unit test suite verifying attendance math, fusion algorithms, and database storage:

```bash
python -m unittest tests/test_system.py
```

