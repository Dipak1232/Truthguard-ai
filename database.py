from __future__ import annotations

import json
import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


BASE_DIR = Path(__file__).resolve().parent


def _database_path() -> Path:
    configured_path = os.environ.get("TRUTHGUARD_DB_PATH")
    path = Path(configured_path) if configured_path else BASE_DIR / "data" / "truthguard.db"
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def _connection() -> sqlite3.Connection:
    connection = sqlite3.connect(_database_path())
    connection.row_factory = sqlite3.Row
    return connection


def initialize_database() -> None:
    with _connection() as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS scans (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                scan_type TEXT NOT NULL CHECK(scan_type IN ('news', 'video')),
                input_name TEXT NOT NULL,
                result TEXT NOT NULL,
                confidence REAL NOT NULL,
                risk TEXT NOT NULL CHECK(risk IN ('Low', 'Medium', 'High')),
                details TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )
        connection.execute("CREATE INDEX IF NOT EXISTS idx_scans_type ON scans(scan_type)")
        connection.execute("CREATE INDEX IF NOT EXISTS idx_scans_result ON scans(result)")
        connection.execute("CREATE INDEX IF NOT EXISTS idx_scans_created ON scans(created_at DESC)")


def create_scan(
    scan_type: str,
    input_name: str,
    result: str,
    confidence: float,
    risk: str,
    details: dict[str, Any],
) -> int:
    created_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    with _connection() as connection:
        cursor = connection.execute(
            """
            INSERT INTO scans (scan_type, input_name, result, confidence, risk, details, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (scan_type, input_name, result, confidence, risk, json.dumps(details), created_at),
        )
        return int(cursor.lastrowid)


def get_history(scan_type: str = "all", result: str = "all", search: str = "") -> list[dict[str, Any]]:
    filters: list[str] = []
    parameters: list[str] = []
    if scan_type in {"news", "video"}:
        filters.append("scan_type = ?")
        parameters.append(scan_type)
    if result and result != "all":
        filters.append("result = ?")
        parameters.append(result)
    if search.strip():
        filters.append("input_name LIKE ?")
        parameters.append(f"%{search.strip()[:120]}%")
    where_clause = f"WHERE {' AND '.join(filters)}" if filters else ""
    query = f"""
        SELECT id, scan_type, input_name, result, confidence, risk, details, created_at
        FROM scans
        {where_clause}
        ORDER BY id DESC
        LIMIT 250
    """
    with _connection() as connection:
        rows = connection.execute(query, parameters).fetchall()
    return [dict(row) for row in rows]


def get_scan(scan_id: int) -> dict[str, Any] | None:
    with _connection() as connection:
        row = connection.execute(
            """
            SELECT id, scan_type, input_name, result, confidence, risk, details, created_at
            FROM scans WHERE id = ? LIMIT 1
            """,
            (scan_id,),
        ).fetchone()
    if row is None:
        return None
    scan = dict(row)
    try:
        scan["details"] = json.loads(scan["details"])
    except (TypeError, json.JSONDecodeError):
        return None
    return scan


def delete_scan(scan_id: int) -> bool:
    with _connection() as connection:
        cursor = connection.execute("DELETE FROM scans WHERE id = ?", (scan_id,))
        return cursor.rowcount > 0


def clear_scans() -> None:
    with _connection() as connection:
        connection.execute("DELETE FROM scans")


def get_statistics() -> dict[str, Any]:
    with _connection() as connection:
        total = connection.execute("SELECT COUNT(*) AS count FROM scans").fetchone()["count"]
        by_type_rows = connection.execute(
            "SELECT scan_type, COUNT(*) AS count FROM scans GROUP BY scan_type"
        ).fetchall()
        by_result_rows = connection.execute(
            "SELECT result, COUNT(*) AS count FROM scans GROUP BY result"
        ).fetchall()
        activity_rows = connection.execute(
            """
            SELECT substr(created_at, 1, 10) AS day, COUNT(*) AS count
            FROM scans
            GROUP BY substr(created_at, 1, 10)
            ORDER BY day DESC
            LIMIT 7
            """
        ).fetchall()

    by_type = {row["scan_type"]: row["count"] for row in by_type_rows}
    by_result = {row["result"]: row["count"] for row in by_result_rows}
    activity = [dict(row) for row in reversed(activity_rows)]
    return {
        "total_scans": total,
        "news_scans": by_type.get("news", 0),
        "video_scans": by_type.get("video", 0),
        "likely_reliable": by_result.get("Likely Reliable", 0),
        "potentially_misleading": by_result.get("Potentially Misleading", 0),
        "likely_authentic": by_result.get("Likely Authentic", 0),
        "potential_deepfake": by_result.get("Potential Deepfake", 0) + by_result.get("Potential AI-Generated Video", 0),
        "potential_ai_generated": by_result.get("Potential AI-Generated Video", 0),
        "activity": activity,
    }
