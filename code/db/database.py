"""Local SQLite Storage & Privacy Layer for Classroom Intelligence.
Ensures zero-cloud, 100% offline data retention with built-in export capabilities.
"""
import sqlite3
import hashlib
import json
import csv
import os
from datetime import datetime
from typing import List, Dict, Any, Optional

class DatabaseManager:
    def __init__(self, db_path: str):
        self.db_path = db_path
        os.makedirs(os.path.dirname(os.path.abspath(db_path)), exist_ok=True)
        self._init_db()

    def get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Sessions table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS sessions (
                    session_id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    course_name TEXT NOT NULL,
                    instructor_name TEXT,
                    start_time TEXT NOT NULL,
                    end_time TEXT,
                    duration_sec REAL DEFAULT 0.0,
                    avg_engagement REAL DEFAULT 0.0,
                    status TEXT DEFAULT 'ACTIVE'
                )
            """)

            # Students roster table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS students (
                    student_id TEXT PRIMARY KEY,
                    display_name TEXT NOT NULL,
                    anonymized_hash TEXT NOT NULL,
                    enrolled_date TEXT NOT NULL
                )
            """)

            # Attendance records
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS attendance_records (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL,
                    student_id TEXT NOT NULL,
                    first_seen_sec REAL,
                    last_seen_sec REAL,
                    total_present_sec REAL DEFAULT 0.0,
                    presence_ratio REAL DEFAULT 0.0,
                    status TEXT NOT NULL, -- 'PRESENT', 'TARDY', 'ABSENT'
                    notes TEXT,
                    FOREIGN KEY(session_id) REFERENCES sessions(session_id),
                    FOREIGN KEY(student_id) REFERENCES students(student_id),
                    UNIQUE(session_id, student_id)
                )
            """)

            # Time-series multimodal engagement telemetry
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS engagement_telemetry (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL,
                    timestamp_sec REAL NOT NULL,
                    visual_attention_score REAL NOT NULL,
                    audio_activity_score REAL NOT NULL,
                    composite_engagement REAL NOT NULL,
                    active_participants INTEGER DEFAULT 0,
                    state_tag TEXT,
                    student_metrics_json TEXT,
                    FOREIGN KEY(session_id) REFERENCES sessions(session_id)
                )
            """)

            # AI Pedagogical Suggestions
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS teaching_suggestions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL,
                    timestamp_sec REAL NOT NULL,
                    category TEXT NOT NULL, -- 'PACING', 'INTERACTION', 'DROP_OFF', 'NOISE'
                    severity TEXT NOT NULL, -- 'INFO', 'WARNING', 'ACTION_REQUIRED'
                    trigger_reason TEXT NOT NULL,
                    suggestion_text TEXT NOT NULL,
                    acknowledged INTEGER DEFAULT 0,
                    FOREIGN KEY(session_id) REFERENCES sessions(session_id)
                )
            """)
            conn.commit()

    @staticmethod
    def hash_identifier(identifier: str) -> str:
        return hashlib.sha256(identifier.encode('utf-8')).hexdigest()[:12]

    # --- Student Roster Management ---
    def enroll_student(self, student_id: str, display_name: str) -> str:
        anon_hash = self.hash_identifier(student_id)
        with self.get_connection() as conn:
            conn.execute("""
                INSERT OR REPLACE INTO students (student_id, display_name, anonymized_hash, enrolled_date)
                VALUES (?, ?, ?, ?)
            """, (student_id, display_name, anon_hash, datetime.now().isoformat()))
            conn.commit()
        return student_id

    def get_all_students(self) -> List[Dict[str, Any]]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM students ORDER BY display_name")
            return [dict(row) for row in cursor.fetchall()]

    # --- Session Management ---
    def create_session(self, session_id: str, title: str, course_name: str, instructor_name: str = "Instructor") -> str:
        with self.get_connection() as conn:
            conn.execute("""
                INSERT OR REPLACE INTO sessions (session_id, title, course_name, instructor_name, start_time, status)
                VALUES (?, ?, ?, ?, ?, 'ACTIVE')
            """, (session_id, title, course_name, instructor_name, datetime.now().isoformat()))
            conn.commit()
        return session_id

    def complete_session(self, session_id: str, duration_sec: float, avg_engagement: float):
        with self.get_connection() as conn:
            conn.execute("""
                UPDATE sessions 
                SET end_time = ?, duration_sec = ?, avg_engagement = ?, status = 'COMPLETED'
                WHERE session_id = ?
            """, (datetime.now().isoformat(), duration_sec, avg_engagement, session_id))
            conn.commit()

    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM sessions WHERE session_id = ?", (session_id,))
            row = cursor.fetchone()
            return dict(row) if row else None

    def list_sessions(self) -> List[Dict[str, Any]]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM sessions ORDER BY start_time DESC")
            return [dict(row) for row in cursor.fetchall()]

    # --- Attendance Recording ---
    def record_attendance(self, session_id: str, student_id: str, first_seen_sec: float, 
                          last_seen_sec: float, total_present_sec: float, presence_ratio: float, 
                          status: str, notes: str = ""):
        with self.get_connection() as conn:
            conn.execute("""
                INSERT OR REPLACE INTO attendance_records 
                (session_id, student_id, first_seen_sec, last_seen_sec, total_present_sec, presence_ratio, status, notes)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (session_id, student_id, first_seen_sec, last_seen_sec, total_present_sec, presence_ratio, status, notes))
            conn.commit()

    def get_session_attendance(self, session_id: str, anonymize: bool = False) -> List[Dict[str, Any]]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT a.*, s.display_name, s.anonymized_hash
                FROM attendance_records a
                JOIN students s ON a.student_id = s.student_id
                WHERE a.session_id = ?
                ORDER BY s.display_name
            """, (session_id,))
            rows = cursor.fetchall()
            results = []
            for r in rows:
                item = dict(r)
                if anonymize:
                    item["student_id"] = f"Anon_{item['anonymized_hash']}"
                    item["display_name"] = f"Participant_{item['anonymized_hash']}"
                results.append(item)
            return results

    # --- Telemetry & Suggestions ---
    def record_telemetry(self, session_id: str, timestamp_sec: float, visual_score: float,
                         audio_score: float, composite_score: float, active_count: int,
                         state_tag: str, student_metrics: Dict[str, Any] = None):
        metrics_json = json.dumps(student_metrics or {})
        with self.get_connection() as conn:
            conn.execute("""
                INSERT INTO engagement_telemetry 
                (session_id, timestamp_sec, visual_attention_score, audio_activity_score, composite_engagement, active_participants, state_tag, student_metrics_json)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (session_id, timestamp_sec, visual_score, audio_score, composite_score, active_count, state_tag, metrics_json))
            conn.commit()

    def get_session_telemetry(self, session_id: str) -> List[Dict[str, Any]]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM engagement_telemetry 
                WHERE session_id = ? 
                ORDER BY timestamp_sec ASC
            """, (session_id,))
            rows = cursor.fetchall()
            telemetry = []
            for r in rows:
                d = dict(r)
                if d.get("student_metrics_json"):
                    d["student_metrics"] = json.loads(d["student_metrics_json"])
                telemetry.append(d)
            return telemetry

    def add_teaching_suggestion(self, session_id: str, timestamp_sec: float, category: str,
                                severity: str, trigger_reason: str, suggestion_text: str) -> int:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO teaching_suggestions 
                (session_id, timestamp_sec, category, severity, trigger_reason, suggestion_text, acknowledged)
                VALUES (?, ?, ?, ?, ?, ?, 0)
            """, (session_id, timestamp_sec, category, severity, trigger_reason, suggestion_text))
            conn.commit()
            return cursor.lastrowid

    def get_session_suggestions(self, session_id: str) -> List[Dict[str, Any]]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM teaching_suggestions 
                WHERE session_id = ? 
                ORDER BY timestamp_sec DESC
            """, (session_id,))
            return [dict(row) for row in cursor.fetchall()]

    # --- Export Helpers ---
    def export_session_summary(self, session_id: str) -> Dict[str, Any]:
        session = self.get_session(session_id)
        if not session:
            return {}
        attendance = self.get_session_attendance(session_id)
        telemetry = self.get_session_telemetry(session_id)
        suggestions = self.get_session_suggestions(session_id)

        total_enrolled = len(attendance)
        present_count = sum(1 for a in attendance if a["status"] == "PRESENT")
        tardy_count = sum(1 for a in attendance if a["status"] == "TARDY")
        absent_count = sum(1 for a in attendance if a["status"] == "ABSENT")

        attendance_rate = ((present_count + tardy_count) / total_enrolled * 100.0) if total_enrolled > 0 else 0.0

        return {
            "session": session,
            "metrics": {
                "total_enrolled": total_enrolled,
                "present_count": present_count,
                "tardy_count": tardy_count,
                "absent_count": absent_count,
                "attendance_rate_percent": round(attendance_rate, 1),
                "avg_engagement_score": round(session.get("avg_engagement", 0.0), 1),
                "total_suggestions_given": len(suggestions)
            },
            "attendance": attendance,
            "telemetry_samples_count": len(telemetry),
            "suggestions": suggestions
        }

    def export_attendance_csv(self, session_id: str, output_path: str):
        records = self.get_session_attendance(session_id)
        with open(output_path, mode="w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["Student ID", "Name", "Status", "Presence Ratio (%)", "Total Present (Sec)", "First Seen (Sec)", "Last Seen (Sec)", "Notes"])
            for r in records:
                writer.writerow([
                    r["student_id"],
                    r["display_name"],
                    r["status"],
                    f"{round(r['presence_ratio'] * 100, 1)}%",
                    round(r["total_present_sec"], 1),
                    round(r["first_seen_sec"], 1) if r["first_seen_sec"] is not None else "N/A",
                    round(r["last_seen_sec"], 1) if r["last_seen_sec"] is not None else "N/A",
                    r["notes"] or ""
                ])

