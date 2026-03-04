"""
storage.py
Persistance des runs de tests en SQLite.
Fonctions : init_db(), save_run(), list_runs(), get_run()
"""
import json
import os
import sqlite3
import datetime

DB_PATH = os.path.join(os.path.dirname(__file__), "runs.db")


def _connect():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Crée la table si elle n'existe pas."""
    with _connect() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS runs (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                api         TEXT    NOT NULL,
                timestamp   TEXT    NOT NULL,
                passed      INTEGER NOT NULL,
                failed      INTEGER NOT NULL,
                errors      INTEGER NOT NULL DEFAULT 0,
                error_rate  REAL    NOT NULL,
                availability REAL   NOT NULL DEFAULT 1.0,
                latency_avg REAL    NOT NULL,
                latency_p95 REAL    NOT NULL,
                tests_json  TEXT    NOT NULL
            )
        """)
        conn.commit()


def save_run(run: dict) -> int:
    """Enregistre un run et retourne son id."""
    init_db()
    summary = run["summary"]
    tests_json = json.dumps(run["tests"], ensure_ascii=False)
    with _connect() as conn:
        cur = conn.execute(
            """
            INSERT INTO runs
              (api, timestamp, passed, failed, errors,
               error_rate, availability, latency_avg, latency_p95, tests_json)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                run["api"],
                run["timestamp"],
                summary["passed"],
                summary["failed"],
                summary.get("errors", 0),
                summary["error_rate"],
                summary.get("availability", 1.0),
                summary["latency_ms_avg"],
                summary["latency_ms_p95"],
                tests_json,
            ),
        )
        conn.commit()
        return cur.lastrowid


def list_runs(limit: int = 50) -> list[dict]:
    """Retourne les `limit` derniers runs (plus récent d'abord)."""
    init_db()
    with _connect() as conn:
        rows = conn.execute(
            """
            SELECT id, api, timestamp, passed, failed, errors,
                   error_rate, availability, latency_avg, latency_p95
            FROM runs
            ORDER BY id DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
    return [dict(r) for r in rows]


def get_run(run_id: int) -> dict | None:
    """Retourne le run complet (avec tests_json) ou None."""
    init_db()
    with _connect() as conn:
        row = conn.execute(
            "SELECT * FROM runs WHERE id = ?", (run_id,)
        ).fetchone()
    if row is None:
        return None
    data = dict(row)
    data["tests"] = json.loads(data.pop("tests_json"))
    return data
