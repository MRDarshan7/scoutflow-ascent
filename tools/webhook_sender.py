"""Outbound webhook delivery for ScoutFlow monitoring alerts.

Synchronous, single-attempt delivery. Failures are logged but never
re-raised, so monitoring runs cannot crash because a remote endpoint is
down or misconfigured.
"""
from __future__ import annotations

import logging
from urllib.parse import urlparse

import requests

from storage.webhook_store import list_webhooks


logger = logging.getLogger("scoutflow.webhook")

REQUEST_TIMEOUT_SECONDS = 5
ALERTABLE_SEVERITIES = {"medium", "high"}
SIGNAL_CHANGE_TYPES = {"signal_added", "signal_removed"}


def dispatch_alert(alert: dict, goal: dict) -> list[dict]:
    """Send an alert to every enabled webhook registered for its goal.

    Returns a list of per-webhook delivery results. Never raises.
    """
    if not _should_notify(alert):
        return []

    goal_id = alert.get("goal_id")
    if goal_id is None:
        return []

    try:
        webhooks = list_webhooks(goal_id=goal_id, enabled_only=True)
    except Exception as exc:  # pragma: no cover - defensive
        logger.exception("Failed to load webhooks for goal_id=%s: %s", goal_id, exc)
        return []

    results: list[dict] = []
    for hook in webhooks:
        result = _send_one(hook, alert, goal)
        results.append(result)
    return results


def _should_notify(alert: dict) -> bool:
    severity = str(alert.get("severity", "")).lower()
    if severity in ALERTABLE_SEVERITIES:
        return True
    change_type = (alert.get("metadata") or {}).get("change_type")
    return change_type in SIGNAL_CHANGE_TYPES


def _send_one(hook: dict, alert: dict, goal: dict) -> dict:
    url = hook.get("url", "")
    webhook_type = hook.get("type", "generic")
    if not _is_valid_url(url):
        logger.warning(
            "Skipping webhook id=%s: invalid url %r", hook.get("id"), url
        )
        return {"webhook_id": hook.get("id"), "status": "skipped", "reason": "invalid_url"}

    try:
        if webhook_type == "discord":
            payload = _discord_payload(alert, goal)
        else:
            payload = _generic_payload(alert, goal)

        response = requests.post(url, json=payload, timeout=REQUEST_TIMEOUT_SECONDS)
        ok = 200 <= response.status_code < 300
        if not ok:
            logger.warning(
                "Webhook id=%s delivery returned status=%s body=%.200s",
                hook.get("id"),
                response.status_code,
                response.text,
            )
        else:
            logger.info(
                "Webhook id=%s delivered (type=%s status=%s)",
                hook.get("id"),
                webhook_type,
                response.status_code,
            )
        return {
            "webhook_id": hook.get("id"),
            "status": "delivered" if ok else "failed",
            "http_status": response.status_code,
        }
    except Exception as exc:
        logger.exception("Webhook id=%s delivery error: %s", hook.get("id"), exc)
        return {"webhook_id": hook.get("id"), "status": "error", "error": str(exc)}


def _is_valid_url(url: str) -> bool:
    if not url:
        return False
    try:
        parsed = urlparse(url)
    except ValueError:
        return False
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def _generic_payload(alert: dict, goal: dict) -> dict:
    metadata = alert.get("metadata") or {}
    return {
        "goal_id": alert.get("goal_id"),
        "query": goal.get("query"),
        "severity": alert.get("severity"),
        "title": alert.get("title"),
        "reason": alert.get("reason"),
        "signals_added": metadata.get("added_signals", []),
        "signals_removed": metadata.get("removed_signals", []),
        "created_at": alert.get("created_at"),
    }


def _discord_payload(alert: dict, goal: dict) -> dict:
    metadata = alert.get("metadata") or {}
    added = metadata.get("added_signals") or []
    removed = metadata.get("removed_signals") or []

    lines = [
        ":rotating_light: **ScoutFlow Alert**",
        "",
        f"**Goal:** {goal.get('query', 'unknown')}",
        f"**Severity:** {alert.get('severity', 'unknown')}",
        f"**Title:** {alert.get('title', '')}",
        f"**Reason:** {alert.get('reason', '')}",
    ]
    if added:
        lines.append("**Added signals:**")
        lines.extend(f"- {item}" for item in added)
    if removed:
        lines.append("**Removed signals:**")
        lines.extend(f"- {item}" for item in removed)
    lines.append("")
    lines.append(f"_Generated: {alert.get('created_at', '')}_")

    return {"content": "\n".join(lines)}
