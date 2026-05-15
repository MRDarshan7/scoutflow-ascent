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
                title TEXT,
                created_at TEXT
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
