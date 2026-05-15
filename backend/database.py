import json
import sqlite3
from pathlib import Path
from datetime import datetime


BASE_DIR = Path(__file__).resolve().parents[1]
STORAGE_DIR = BASE_DIR / "storage"
DB_PATH = STORAGE_DIR / "scoutflow.db"


def get_db_connection() -> sqlite3.Connection:
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def init_db() -> None:
    STORAGE_DIR.mkdir(parents=True, exist_ok=True)
    with get_db_connection() as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS goals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                query TEXT NOT NULL,
                preferences TEXT NOT NULL,
                created_at TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'active'
            )
            """
        )
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS alerts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                goal_id INTEGER,
                title TEXT,
                reason TEXT,
                severity TEXT,
                metadata TEXT,
                created_at TEXT
            )
            """
        )
        _ensure_column(connection, "alerts", "goal_id", "INTEGER")
        _ensure_column(connection, "alerts", "reason", "TEXT")
        _ensure_column(connection, "alerts", "severity", "TEXT")
        _ensure_column(connection, "alerts", "metadata", "TEXT")
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS monitoring_snapshots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                goal_id INTEGER NOT NULL,
                created_at TEXT NOT NULL,
                insights TEXT NOT NULL,
                signals TEXT NOT NULL,
                recommendations TEXT NOT NULL,
                recommended_actions TEXT NOT NULL
            )
            """
        )
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS feedback (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                alert_id INTEGER,
                feedback TEXT,
                created_at TEXT
            )
            """
        )
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS reports (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                path TEXT,
                created_at TEXT
            )
            """
        )
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_type TEXT,
                payload TEXT,
                created_at TEXT
            )
            """
        )


def create_goal(query: str, preferences: list[str]) -> dict:
    created_at = datetime.now().replace(microsecond=0).isoformat()
    status = "active"

    with get_db_connection() as connection:
        cursor = connection.execute(
            """
            INSERT INTO goals (query, preferences, created_at, status)
            VALUES (?, ?, ?, ?)
            """,
            (query, json.dumps(preferences), created_at, status),
        )
        goal_id = cursor.lastrowid

    return {
        "id": goal_id,
        "query": query,
        "preferences": preferences,
        "created_at": created_at,
        "status": status,
    }


def get_all_goals() -> list[dict]:
    with get_db_connection() as connection:
        rows = connection.execute(
            """
            SELECT id, query, preferences, created_at, status
            FROM goals
            ORDER BY created_at DESC
            """
        ).fetchall()

    return [
        {
            "id": row["id"],
            "query": row["query"],
            "preferences": json.loads(row["preferences"]),
            "created_at": row["created_at"],
            "status": row["status"],
        }
        for row in rows
    ]


def check_connection() -> None:
    with get_db_connection() as connection:
        connection.execute("SELECT 1")


def _ensure_column(
    connection: sqlite3.Connection, table: str, column: str, column_type: str
) -> None:
    """Idempotently add a column to an existing SQLite table."""
    rows = connection.execute(f"PRAGMA table_info({table})").fetchall()
    existing = {row[1] for row in rows}
    if column not in existing:
        connection.execute(f"ALTER TABLE {table} ADD COLUMN {column} {column_type}")


def get_goal_by_id(goal_id: int) -> dict | None:
    with get_db_connection() as connection:
        row = connection.execute(
            "SELECT id, query, preferences, created_at, status FROM goals WHERE id = ?",
            (goal_id,),
        ).fetchone()

    if row is None:
        return None

    return {
        "id": row["id"],
        "query": row["query"],
        "preferences": json.loads(row["preferences"]),
        "created_at": row["created_at"],
        "status": row["status"],
    }


def save_monitoring_snapshot(goal_id: int, insights: dict) -> int:
    created_at = datetime.now().replace(microsecond=0).isoformat()
    signals = insights.get("signals_detected", [])
    recommendations = insights.get("recommendations", [])
    actions = insights.get("recommended_actions", [])

    with get_db_connection() as connection:
        cursor = connection.execute(
            """
            INSERT INTO monitoring_snapshots
                (goal_id, created_at, insights, signals, recommendations, recommended_actions)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                goal_id,
                created_at,
                json.dumps(insights, default=str),
                json.dumps(signals),
                json.dumps(recommendations),
                json.dumps(actions),
            ),
        )
        return cursor.lastrowid


def get_latest_snapshot(goal_id: int, before_id: int | None = None) -> dict | None:
    with get_db_connection() as connection:
        if before_id is not None:
            row = connection.execute(
                """
                SELECT id, goal_id, created_at, insights, signals, recommendations, recommended_actions
                FROM monitoring_snapshots
                WHERE goal_id = ? AND id < ?
                ORDER BY id DESC
                LIMIT 1
                """,
                (goal_id, before_id),
            ).fetchone()
        else:
            row = connection.execute(
                """
                SELECT id, goal_id, created_at, insights, signals, recommendations, recommended_actions
                FROM monitoring_snapshots
                WHERE goal_id = ?
                ORDER BY id DESC
                LIMIT 1
                """,
                (goal_id,),
            ).fetchone()

    if row is None:
        return None

    return {
        "id": row["id"],
        "goal_id": row["goal_id"],
        "created_at": row["created_at"],
        "insights": json.loads(row["insights"]),
        "signals": json.loads(row["signals"]),
        "recommendations": json.loads(row["recommendations"]),
        "recommended_actions": json.loads(row["recommended_actions"]),
    }


def save_alert(
    goal_id: int,
    title: str,
    reason: str,
    severity: str,
    metadata: dict | None = None,
) -> dict:
    created_at = datetime.now().replace(microsecond=0).isoformat()
    payload = json.dumps(metadata or {}, default=str)

    with get_db_connection() as connection:
        cursor = connection.execute(
            """
            INSERT INTO alerts (goal_id, title, reason, severity, metadata, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (goal_id, title, reason, severity, payload, created_at),
        )
        alert_id = cursor.lastrowid

    return {
        "id": alert_id,
        "goal_id": goal_id,
        "title": title,
        "reason": reason,
        "severity": severity,
        "metadata": metadata or {},
        "created_at": created_at,
    }


def get_alerts(goal_id: int | None = None, limit: int = 50) -> list[dict]:
    with get_db_connection() as connection:
        if goal_id is None:
            rows = connection.execute(
                """
                SELECT id, goal_id, title, reason, severity, metadata, created_at
                FROM alerts
                ORDER BY id DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
        else:
            rows = connection.execute(
                """
                SELECT id, goal_id, title, reason, severity, metadata, created_at
                FROM alerts
                WHERE goal_id = ?
                ORDER BY id DESC
                LIMIT ?
                """,
                (goal_id, limit),
            ).fetchall()

    return [
        {
            "id": row["id"],
            "goal_id": row["goal_id"],
            "title": row["title"],
            "reason": row["reason"],
            "severity": row["severity"],
            "metadata": json.loads(row["metadata"]) if row["metadata"] else {},
            "created_at": row["created_at"],
        }
        for row in rows
    ]
