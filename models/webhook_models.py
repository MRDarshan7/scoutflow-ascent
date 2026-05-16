"""Pydantic models for the webhook subsystem."""
from typing import Literal

from pydantic import BaseModel, Field


WebhookType = Literal["generic", "discord"]


class WebhookRegisterRequest(BaseModel):
    goal_id: int
    type: WebhookType
    url: str = Field(..., min_length=1)


class WebhookToggleRequest(BaseModel):
    enabled: bool


class WebhookResponse(BaseModel):
    id: int
    goal_id: int
    type: WebhookType
    url: str
    enabled: bool
    created_at: str
