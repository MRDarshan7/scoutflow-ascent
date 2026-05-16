"""ScoutFlow continuous-monitoring scheduler.

Lightweight in-process APScheduler that re-runs the existing LangGraph
workflow for saved goals on a recurring interval, persists each run as a
`monitoring_snapshots` row, diffs the new signals against the previous
snapshot, and writes any meaningful changes into the `alerts` table.

Hackathon-friendly: no Celery, no Redis, no queues. The scheduler runs
inside the FastAPI process and is started/stopped by the app lifespan.
"""
from __future__ import annotations

import logging
from datetime import datetime

from apscheduler.schedulers.background import BackgroundScheduler

from backend.config import settings
from backend.database import (
    get_goal_by_id,
    get_latest_snapshot,
    save_alert,
    save_monitoring_snapshot,
)
from tools.webhook_sender import dispatch_alert
from workflow.graph import run_workflow


logger = logging.getLogger("scoutflow.scheduler")

_scheduler: BackgroundScheduler | None = None


def _job_id(goal_id: int) -> str:
    return f"monitor:{goal_id}"


def _interval_minutes() -> int:
    return max(1, int(settings.monitor_interval_minutes))


def start_scheduler() -> None:
    """Initialize the scheduler. Safe to call once at app startup."""
    global _scheduler
    if _scheduler is not None and _scheduler.running:
        return

    _scheduler = BackgroundScheduler(daemon=True)
    _scheduler.start()
    logger.info(
        "Monitoring scheduler initialized (default interval=%s min)",
        _interval_minutes(),
    )


def shutdown_scheduler() -> None:
    global _scheduler
    if _scheduler is None:
        return
    try:
        _scheduler.shutdown(wait=False)
    except Exception as exc:  # pragma: no cover - defensive
        logger.warning("Scheduler shutdown error: %s", exc)
    _scheduler = None


def _require_scheduler() -> BackgroundScheduler:
    if _scheduler is None or not _scheduler.running:
        start_scheduler()
    assert _scheduler is not None
    return _scheduler


def start_monitor(goal_id: int, interval_minutes: int | None = None) -> dict:
    """Start (or replace) a recurring monitoring job for a goal."""
    goal = get_goal_by_id(goal_id)
    if goal is None:
        raise LookupError(f"goal_id {goal_id} not found")

    scheduler = _require_scheduler()
    minutes = max(1, int(interval_minutes)) if interval_minutes else _interval_minutes()
    job_id = _job_id(goal_id)

    scheduler.add_job(
        run_monitoring_job,
        trigger="interval",
        minutes=minutes,
        id=job_id,
        kwargs={"goal_id": goal_id},
        replace_existing=True,
        next_run_time=datetime.now(),  # run once immediately for instant feedback
        max_instances=1,
        coalesce=True,
    )
    logger.info("Monitor started for goal_id=%s every %s min", goal_id, minutes)

    job = scheduler.get_job(job_id)
    return {
        "goal_id": goal_id,
        "query": goal["query"],
        "interval_minutes": minutes,
        "next_run": _format_time(job.next_run_time if job else None),
        "status": "active",
    }


def stop_monitor(goal_id: int) -> dict:
    scheduler = _require_scheduler()
    job_id = _job_id(goal_id)
    job = scheduler.get_job(job_id)
    if job is None:
        return {"goal_id": goal_id, "status": "inactive"}

    scheduler.remove_job(job_id)
    logger.info("Monitor stopped for goal_id=%s", goal_id)
    return {"goal_id": goal_id, "status": "stopped"}


def list_active_monitors() -> list[dict]:
    scheduler = _require_scheduler()
    active: list[dict] = []
    for job in scheduler.get_jobs():
        if not job.id.startswith("monitor:"):
            continue
        goal_id = int(job.id.split(":", 1)[1])
        goal = get_goal_by_id(goal_id)
        active.append(
            {
                "goal_id": goal_id,
                "query": goal["query"] if goal else None,
                "next_run": _format_time(job.next_run_time),
                "trigger": str(job.trigger),
            }
        )
    return active


def run_monitoring_job(goal_id: int) -> None:
    """Run the existing LangGraph workflow once, persist the snapshot, emit alerts."""
    goal = get_goal_by_id(goal_id)
    if goal is None:
        logger.warning("Monitor job aborted: goal_id=%s not found", goal_id)
        return

    logger.info("Monitor run started: goal_id=%s query=%r", goal_id, goal["query"])

    try:
        final_state = run_workflow(goal["query"], goal.get("preferences"))
    except Exception as exc:  # pragma: no cover - defensive
        logger.exception("Workflow failed for goal_id=%s: %s", goal_id, exc)
        return

    insights = final_state.get("insights") or {}
    if not insights:
        logger.warning("Monitor run produced no insights for goal_id=%s", goal_id)
        return

    previous = get_latest_snapshot(goal_id)
    snapshot_id = save_monitoring_snapshot(goal_id, insights)
    logger.info("Snapshot saved: id=%s goal_id=%s", snapshot_id, goal_id)

    if previous is not None:
        alerts = detect_changes(goal_id, goal["query"], previous, insights)
        for alert in alerts:
            saved = save_alert(
                goal_id=goal_id,
                title=alert["title"],
                reason=alert["reason"],
                severity=alert["severity"],
                metadata=alert.get("metadata"),
            )
            logger.info(
                "Alert raised: id=%s goal_id=%s severity=%s title=%r",
                saved["id"],
                goal_id,
                saved["severity"],
                saved["title"],
            )
            try:
                dispatch_alert(saved, goal)
            except Exception as exc:  # pragma: no cover - belt and braces
                logger.exception(
                    "Webhook dispatch failed for alert_id=%s: %s", saved["id"], exc
                )


def detect_changes(
    goal_id: int, query: str, previous: dict, current_insights: dict
) -> list[dict]:
    """Compare signals between previous snapshot and current insights."""
    prev_signals = {s for s in previous.get("signals", []) if isinstance(s, str)}
    new_signals = {
        s
        for s in current_insights.get("signals_detected", [])
        if isinstance(s, str)
    }
    if prev_signals == new_signals:
        return []

    added = sorted(new_signals - prev_signals)
    removed = sorted(prev_signals - new_signals)
    alerts: list[dict] = []

    for signal in added:
        alerts.append(
            {
                "title": "New signal detected",
                "reason": f"'{signal}' appeared in monitoring for: {query}",
                "severity": _severity_for_change(len(added), len(removed)),
                "metadata": {
                    "change_type": "signal_added",
                    "signal": signal,
                    "added_signals": added,
                    "removed_signals": removed,
                    "previous_snapshot_id": previous.get("id"),
                },
            }
        )

    for signal in removed:
        alerts.append(
            {
                "title": "Signal cleared",
                "reason": f"'{signal}' is no longer present in monitoring for: {query}",
                "severity": "low",
                "metadata": {
                    "change_type": "signal_removed",
                    "signal": signal,
                    "added_signals": added,
                    "removed_signals": removed,
                    "previous_snapshot_id": previous.get("id"),
                },
            }
        )

    return alerts


def _severity_for_change(added_count: int, removed_count: int) -> str:
    total = added_count + removed_count
    if total >= 3:
        return "high"
    if total == 2:
        return "medium"
    return "low" if removed_count and not added_count else "medium"


def _format_time(value) -> str | None:
    if value is None:
        return None
    try:
        return value.replace(microsecond=0).isoformat()
    except Exception:  # pragma: no cover - defensive
        return str(value)
