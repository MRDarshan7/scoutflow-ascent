import sqlite3
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parents[1]
STORAGE_DIR = BASE_DIR / "storage"
DB_PATH = STORAGE_DIR / "scoutflow.db"


def init_db() -> None:
    STORAGE_DIR.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(DB_PATH) as connection:
        connection.execute("PRAGMA database_list")


def check_connection() -> None:
    with sqlite3.connect(DB_PATH) as connection:
        connection.execute("SELECT 1")
