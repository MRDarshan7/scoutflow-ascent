"""FastAPI routes for webhook registration and management."""
from fastapi import APIRouter, HTTPException

from backend.database import get_goal_by_id
from models.webhook_models import WebhookRegisterRequest, WebhookToggleRequest
from storage.webhook_store import (
    get_webhook,
    list_webhooks,
    register_webhook,
    set_webhook_enabled,
)


router = APIRouter(prefix="/webhook", tags=["webhooks"])


@router.post("/register")
def register(request: WebhookRegisterRequest) -> dict:
    if get_goal_by_id(request.goal_id) is None:
        raise HTTPException(status_code=404, detail=f"goal_id {request.goal_id} not found")
    try:
        created = register_webhook(request.goal_id, request.type, request.url)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    return {
        "id": created["id"],
        "goal_id": created["goal_id"],
        "type": created["type"],
        "enabled": created["enabled"],
        "status": "registered",
    }


@router.get("/{goal_id}")
def list_for_goal(goal_id: int) -> list[dict]:
    return list_webhooks(goal_id=goal_id)


@router.post("/toggle/{webhook_id}")
def toggle(webhook_id: int, request: WebhookToggleRequest) -> dict:
    updated = set_webhook_enabled(webhook_id, request.enabled)
    if updated is None:
        raise HTTPException(status_code=404, detail=f"webhook_id {webhook_id} not found")
    return updated
