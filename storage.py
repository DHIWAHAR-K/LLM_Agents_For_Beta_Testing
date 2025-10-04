from __future__ import annotations

import json
import sqlite3
import time
import uuid
from typing import Any

from config import settings
from schemas import Action, Persona


def init_db() -> None:
    with sqlite3.connect(settings.db_path) as conn:
        cursor = conn.cursor()
        
        # Sessions table for run metadata
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS sessions(
                session_id TEXT PRIMARY KEY,
                persona_name TEXT,
                scenario TEXT,
                start_ts REAL,
                end_ts REAL,
                status TEXT,
                version TEXT,
                model_name TEXT,
                seed INTEGER
            )
            """
        )
        
        # Runs table with session_id linkage
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS runs(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT,
                turn_number INTEGER,
                ts REAL,
                persona TEXT,
                observation TEXT,
                action_json TEXT,
                latency REAL,
                oracle_pass INTEGER,
                FOREIGN KEY(session_id) REFERENCES sessions(session_id)
            )
            """
        )
        
        # Events table for tracking system events
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS events(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT,
                ts REAL,
                event_type TEXT,
                event_data TEXT,
                FOREIGN KEY(session_id) REFERENCES sessions(session_id)
            )
            """
        )
        
        conn.commit()


def start_session(
    persona: Persona, 
    scenario: str, 
    version: str = "unknown", 
    model_name: str = "gpt-4o-mini",
    seed: int | None = None
) -> str:
    """Start a new session and return session_id."""
    session_id = str(uuid.uuid4())
    with sqlite3.connect(settings.db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """INSERT INTO sessions(session_id, persona_name, scenario, start_ts, status, version, model_name, seed)
               VALUES (?,?,?,?,?,?,?,?)""",
            (
                session_id,
                persona.name,
                scenario,
                time.time(),
                "running",
                version,
                model_name,
                seed or settings.seed,
            ),
        )
        conn.commit()
    return session_id


def end_session(session_id: str, status: str = "completed") -> None:
    """Mark session as complete."""
    with sqlite3.connect(settings.db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """UPDATE sessions SET end_ts=?, status=? WHERE session_id=?""",
            (time.time(), status, session_id),
        )
        conn.commit()


def log_step(
    session_id: str,
    turn_number: int,
    persona: Persona,
    observation: str,
    action: Action,
    latency: float | None,
    oracle_pass: bool = True,
) -> None:
    """Log a single turn."""
    with sqlite3.connect(settings.db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """INSERT INTO runs(session_id, turn_number, ts, persona, observation, action_json, latency, oracle_pass)
                     VALUES (?,?,?,?,?,?,?,?)""",
            (
                session_id,
                turn_number,
                time.time(),
                persona.model_dump_json(),
                observation,
                json.dumps(action.model_dump()),
                float(latency or 0.0),
                1 if oracle_pass else 0,
            ),
        )
        conn.commit()


def log_event(session_id: str, event_type: str, event_data: dict[str, Any]) -> None:
    """Log a system event."""
    with sqlite3.connect(settings.db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """INSERT INTO events(session_id, ts, event_type, event_data)
               VALUES (?,?,?,?)""",
            (session_id, time.time(), event_type, json.dumps(event_data)),
        )
        conn.commit()


# Query helpers
def get_runs(filter_spec: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    """Fetch runs matching filter criteria."""
    with sqlite3.connect(settings.db_path) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        query = "SELECT * FROM runs"
        params = []
        
        if filter_spec:
            conditions = []
            if "session_id" in filter_spec:
                conditions.append("session_id=?")
                params.append(filter_spec["session_id"])
            if "persona_name" in filter_spec:
                conditions.append("json_extract(persona, '$.name')=?")
                params.append(filter_spec["persona_name"])
            if "oracle_pass" in filter_spec:
                conditions.append("oracle_pass=?")
                params.append(1 if filter_spec["oracle_pass"] else 0)
            
            if conditions:
                query += " WHERE " + " AND ".join(conditions)
        
        query += " ORDER BY ts"
        cursor.execute(query, params)
        return [dict(row) for row in cursor.fetchall()]


def get_turns(run_id: str) -> list[dict[str, Any]]:
    """Get all turns for a specific run (session)."""
    return get_runs({"session_id": run_id})


def get_events(run_id: str) -> list[dict[str, Any]]:
    """Get all events for a specific session."""
    with sqlite3.connect(settings.db_path) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM events WHERE session_id=? ORDER BY ts",
            (run_id,),
        )
        return [dict(row) for row in cursor.fetchall()]


def get_session(session_id: str) -> dict[str, Any] | None:
    """Get session metadata."""
    with sqlite3.connect(settings.db_path) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM sessions WHERE session_id=?",
            (session_id,),
        )
        row = cursor.fetchone()
        return dict(row) if row else None


def get_all_sessions(status: str | None = None) -> list[dict[str, Any]]:
    """Get all sessions, optionally filtered by status."""
    with sqlite3.connect(settings.db_path) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        if status:
            cursor.execute(
                "SELECT * FROM sessions WHERE status=? ORDER BY start_ts DESC",
                (status,),
            )
        else:
            cursor.execute("SELECT * FROM sessions ORDER BY start_ts DESC")
        
        return [dict(row) for row in cursor.fetchall()]
