"""Tests for the Phase-10 webhook subsystem.

Uses an isolated temporary SQLite database so the real
`storage/scoutflow.db` is never touched. The FastAPI app is exercised
via `TestClient` to verify the public webhook endpoints, and the
scheduler's alert-save -> webhook dispatch glue is tested directly
without booting the background scheduler.
"""
from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient


@pytest.fixture(autouse=True)
def isolated_db(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Redirect SQLite to a per-test temp file and init all tables."""
    test_db = tmp_path / "scoutflow_test.db"

    from backend import database as backend_db
    monkeypatch.setattr(backend_db, "DB_PATH", test_db, raising=True)
    monkeypatch.setattr(backend_db, "STORAGE_DIR", tmp_path, raising=True)

    backend_db.init_db()

    from storage import webhook_store
    webhook_store.init_webhook_table()

    yield test_db


@pytest.fixture
def client() -> TestClient:
    from backend.main import app
    return TestClient(app)


@pytest.fixture
def goal_id() -> int:
    from backend.database import create_goal
    return create_goal("Track AI startups in India", [])["id"]


# --------------------------------------------------------------------- #
# Endpoint tests
# --------------------------------------------------------------------- #

def test_register_webhook_returns_registered_payload(client: TestClient, goal_id: int):
    response = client.post(
        "/webhook/register",
        json={"goal_id": goal_id, "type": "generic", "url": "https://example.com/hook"},
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["goal_id"] == goal_id
    assert body["type"] == "generic"
    assert body["enabled"] is True
    assert body["status"] == "registered"
    assert isinstance(body["id"], int)


def test_register_webhook_rejects_unknown_goal(client: TestClient):
    response = client.post(
        "/webhook/register",
        json={"goal_id": 9999, "type": "generic", "url": "https://example.com/hook"},
    )
    assert response.status_code == 404


def test_register_webhook_rejects_bad_type(client: TestClient, goal_id: int):
    response = client.post(
        "/webhook/register",
        json={"goal_id": goal_id, "type": "slack", "url": "https://example.com/hook"},
    )
    assert response.status_code == 422


def test_list_webhooks_for_goal(client: TestClient, goal_id: int):
    client.post(
        "/webhook/register",
        json={"goal_id": goal_id, "type": "discord", "url": "https://discord.com/api/webhooks/x"},
    )
    response = client.get(f"/webhook/{goal_id}")
    assert response.status_code == 200
    items = response.json()
    assert len(items) == 1
    assert items[0]["type"] == "discord"
    assert items[0]["enabled"] is True


def test_toggle_webhook(client: TestClient, goal_id: int):
    created = client.post(
        "/webhook/register",
        json={"goal_id": goal_id, "type": "generic", "url": "https://example.com/hook"},
    ).json()

    off = client.post(f"/webhook/toggle/{created['id']}", json={"enabled": False}).json()
    assert off["enabled"] is False

    on = client.post(f"/webhook/toggle/{created['id']}", json={"enabled": True}).json()
    assert on["enabled"] is True


def test_toggle_unknown_webhook_returns_404(client: TestClient):
    response = client.post("/webhook/toggle/424242", json={"enabled": True})
    assert response.status_code == 404


# --------------------------------------------------------------------- #
# Dispatcher tests
# --------------------------------------------------------------------- #

def _alert(goal_id: int, severity: str = "high", change_type: str = "signal_added") -> dict:
    return {
        "id": 1,
        "goal_id": goal_id,
        "title": "New signal detected",
        "reason": "'Funding Growth' appeared",
        "severity": severity,
        "created_at": "2026-05-16T03:30:00",
        "metadata": {
            "change_type": change_type,
            "signal": "Funding Growth",
            "added_signals": ["Funding Growth"],
            "removed_signals": [],
        },
    }


def test_dispatch_sends_generic_webhook(goal_id: int):
    from storage.webhook_store import register_webhook
    from tools import webhook_sender

    register_webhook(goal_id, "generic", "https://example.com/hook")

    mock_response = MagicMock(status_code=200, text="ok")
    with patch.object(webhook_sender.requests, "post", return_value=mock_response) as post:
        results = webhook_sender.dispatch_alert(_alert(goal_id), {"query": "q"})

    assert post.called
    sent_payload = post.call_args.kwargs["json"]
    assert sent_payload["goal_id"] == goal_id
    assert sent_payload["severity"] == "high"
    assert sent_payload["signals_added"] == ["Funding Growth"]
    assert results[0]["status"] == "delivered"


def test_dispatch_sends_discord_webhook(goal_id: int):
    from storage.webhook_store import register_webhook
    from tools import webhook_sender

    register_webhook(goal_id, "discord", "https://discord.com/api/webhooks/x")

    mock_response = MagicMock(status_code=204, text="")
    with patch.object(webhook_sender.requests, "post", return_value=mock_response) as post:
        webhook_sender.dispatch_alert(_alert(goal_id), {"query": "Track AI startups"})

    sent_payload = post.call_args.kwargs["json"]
    assert "content" in sent_payload
    assert "ScoutFlow Alert" in sent_payload["content"]
    assert "Track AI startups" in sent_payload["content"]
    assert "Funding Growth" in sent_payload["content"]


def test_dispatch_skips_disabled_webhook(goal_id: int):
    from storage.webhook_store import register_webhook, set_webhook_enabled
    from tools import webhook_sender

    created = register_webhook(goal_id, "generic", "https://example.com/hook")
    set_webhook_enabled(created["id"], False)

    with patch.object(webhook_sender.requests, "post") as post:
        results = webhook_sender.dispatch_alert(_alert(goal_id), {"query": "q"})

    assert post.call_count == 0
    assert results == []


def test_dispatch_skips_low_severity_with_no_signal_change(goal_id: int):
    from storage.webhook_store import register_webhook
    from tools import webhook_sender

    register_webhook(goal_id, "generic", "https://example.com/hook")
    low_alert = _alert(goal_id, severity="low", change_type="noise")

    with patch.object(webhook_sender.requests, "post") as post:
        results = webhook_sender.dispatch_alert(low_alert, {"query": "q"})

    assert post.call_count == 0
    assert results == []


def test_dispatch_still_fires_on_low_severity_signal_change(goal_id: int):
    from storage.webhook_store import register_webhook
    from tools import webhook_sender

    register_webhook(goal_id, "generic", "https://example.com/hook")
    low_change = _alert(goal_id, severity="low", change_type="signal_removed")

    mock_response = MagicMock(status_code=200, text="ok")
    with patch.object(webhook_sender.requests, "post", return_value=mock_response) as post:
        results = webhook_sender.dispatch_alert(low_change, {"query": "q"})

    assert post.call_count == 1
    assert results[0]["status"] == "delivered"


def test_dispatch_handles_remote_failure_without_raising(goal_id: int):
    from storage.webhook_store import register_webhook
    from tools import webhook_sender

    register_webhook(goal_id, "generic", "https://example.com/hook")

    with patch.object(
        webhook_sender.requests, "post", side_effect=RuntimeError("network down")
    ):
        results = webhook_sender.dispatch_alert(_alert(goal_id), {"query": "q"})

    assert results[0]["status"] == "error"
    assert "network down" in results[0]["error"]


def test_dispatch_ignores_malformed_url(goal_id: int):
    from storage.webhook_store import register_webhook
    from tools import webhook_sender

    register_webhook(goal_id, "generic", "not-a-real-url")

    with patch.object(webhook_sender.requests, "post") as post:
        results = webhook_sender.dispatch_alert(_alert(goal_id), {"query": "q"})

    assert post.call_count == 0
    assert results[0]["status"] == "skipped"
    assert results[0]["reason"] == "invalid_url"


# --------------------------------------------------------------------- #
# Monitoring integration test
# --------------------------------------------------------------------- #

def test_monitor_run_triggers_webhook_and_survives_failure(goal_id: int):
    """End-to-end: run_monitoring_job persists snapshots, fires alerts, and
    a failing webhook does NOT break the monitoring pipeline."""
    from backend.database import (
        get_alerts,
        get_latest_snapshot,
        save_monitoring_snapshot,
    )
    from scheduler import monitor
    from storage.webhook_store import register_webhook
    from tools import webhook_sender

    register_webhook(goal_id, "generic", "https://example.com/hook")

    baseline_insights = {
        "goal": "Track AI startups in India",
        "signals_detected": ["Old Signal"],
        "recommendations": [],
        "recommended_actions": [],
    }
    save_monitoring_snapshot(goal_id, baseline_insights)

    fake_state = {
        "insights": {
            "goal": "Track AI startups in India",
            "summary": "test summary",
            "signals_detected": ["Funding Growth", "Hiring Expansion"],
            "business_implications": [],
            "recommendations": [],
            "recommended_actions": [],
            "supporting_findings": [],
            "metadata": {"signals_count": 2, "actions_count": 0, "recommendations_count": 0},
        }
    }

    with patch.object(monitor, "run_workflow", return_value=fake_state), patch.object(
        webhook_sender.requests, "post", side_effect=RuntimeError("remote 500")
    ) as post:
        monitor.run_monitoring_job(goal_id)

    snap = get_latest_snapshot(goal_id)
    assert snap["signals"] == ["Funding Growth", "Hiring Expansion"]

    alerts = get_alerts(goal_id=goal_id)
    assert len(alerts) >= 2
    assert post.call_count >= 1
