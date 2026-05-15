"""LangGraph orchestration for ScoutFlow.

This module wires the existing agents into a linear LangGraph state
machine. It does NOT reimplement any agent logic. Each node simply:

    state -> existing agent -> state

The output of `run_workflow` for the `insights` key is byte-for-byte the
same as calling the agents manually (see `backend/main.py` history),
which preserves the Gemini-enhanced quality and the deterministic /
quota-aware fallback chain in `tools/gemini_helper.py`.
"""
from langgraph.graph import StateGraph, START, END

from agents.insight import InsightAgent
from agents.planner import PlannerAgent
from agents.researcher import ResearchAgent
from agents.validator import ValidationAgent

from workflow.state import ScoutFlowState


def planner_node(state: ScoutFlowState) -> dict:
    plan = PlannerAgent().plan_goal(
        state.get("query", ""),
        state.get("preferences"),
    )
    return {"plan": plan}


def research_node(state: ScoutFlowState) -> dict:
    research = ResearchAgent().research(state.get("plan", {}))
    return {"research": research}


def validation_node(state: ScoutFlowState) -> dict:
    validated = ValidationAgent().validate(state.get("research", {}))
    return {"validated": validated}


def insight_node(state: ScoutFlowState) -> dict:
    insights = InsightAgent().generate_insights(state.get("validated", {}))
    return {"insights": insights}


def build_graph():
    graph = StateGraph(ScoutFlowState)
    graph.add_node("planner", planner_node)
    graph.add_node("research", research_node)
    graph.add_node("validation", validation_node)
    graph.add_node("insight", insight_node)

    graph.add_edge(START, "planner")
    graph.add_edge("planner", "research")
    graph.add_edge("research", "validation")
    graph.add_edge("validation", "insight")
    graph.add_edge("insight", END)

    return graph.compile()


# Compile once at import time so each request reuses the same graph.
_compiled_graph = build_graph()


def run_workflow(query: str, preferences: list[str] | None = None) -> ScoutFlowState:
    """Run the full ScoutFlow pipeline through LangGraph.

    Returns the final state dict. The caller usually only needs
    `state["insights"]` which has the same shape as the previous
    `InsightAgent.generate_insights(...)` return value.
    """
    initial_state: ScoutFlowState = {
        "query": query,
        "preferences": preferences or [],
        "errors": [],
    }
    return _compiled_graph.invoke(initial_state)
