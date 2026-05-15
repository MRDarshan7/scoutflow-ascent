"""Shared state for the ScoutFlow LangGraph workflow.

The state is intentionally simple: every node reads what it needs and
writes its own output bucket. No agent logic lives here.
"""
from typing import TypedDict


class ScoutFlowState(TypedDict, total=False):
    query: str
    preferences: list[str]
    plan: dict
    research: dict
    validated: dict
    insights: dict
    errors: list[str]
