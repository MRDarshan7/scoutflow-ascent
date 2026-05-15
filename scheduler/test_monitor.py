"""Manual smoke test for the monitoring scheduler.

Run with:

    python -m scheduler.test_monitor

What it does:
  1. Creates (or reuses) a sample goal in SQLite.
  2. Runs one monitoring job synchronously.
  3. Mutates the just-stored snapshot to simulate a "previous" run with
     different signals.
  4. Runs the monitoring job again so the diff logic actually fires.
  5. Prints the resulting snapshots and alerts.

No FastAPI server is required.
"""
import json
import sqlite3

from backend.database import (
    DB_PATH,
    create_goal,
    get_all_goals,
    get_alerts,
    get_latest_snapshot,
    init_db,
)
from scheduler.monitor import run_monitoring_job


SAMPLE_QUERY = "Track AI startups in India"


def _section(title: str) -> None:
    print()
    print("=" * 80)
    print(title)
    print("=" * 80)


def _ensure_sample_goal() -> int:
    init_db()
    for goal in get_all_goals():
        if goal["query"] == SAMPLE_QUERY:
            return goal["id"]
    created = create_goal(SAMPLE_QUERY, [])
    return created["id"]


def _mutate_last_snapshot_signals(goal_id: int) -> None:
    """Drop one signal and inject a fake one so the next run produces a diff."""
    snapshot = get_latest_snapshot(goal_id)
    if snapshot is None:
        print("No snapshot to mutate.")
        return

    new_signals = list(snapshot["signals"])[:-1] + ["Synthetic Phase9 Test Signal"]

    with sqlite3.connect(DB_PATH) as connection:
        connection.execute(
            "UPDATE monitoring_snapshots SET signals = ? WHERE id = ?",
            (json.dumps(new_signals), snapshot["id"]),
        )
    print(f"Mutated snapshot {snapshot['id']} signals -> {new_signals}")


def main() -> None:
    goal_id = _ensure_sample_goal()
    print(f"Using goal_id={goal_id}")

    _section("RUN 1 (baseline)")
    run_monitoring_job(goal_id)
    snap1 = get_latest_snapshot(goal_id)
    print("Snapshot:", json.dumps({"id": snap1["id"], "signals": snap1["signals"]}, indent=2))

    _section("MUTATE PREVIOUS SNAPSHOT")
    _mutate_last_snapshot_signals(goal_id)

    _section("RUN 2 (should generate alerts)")
    run_monitoring_job(goal_id)
    snap2 = get_latest_snapshot(goal_id)
    print("Snapshot:", json.dumps({"id": snap2["id"], "signals": snap2["signals"]}, indent=2))

    _section("ALERTS")
    print(json.dumps(get_alerts(goal_id=goal_id, limit=20), indent=2))


if __name__ == "__main__":
    main()
