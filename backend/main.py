from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from agents.insight import InsightAgent
from agents.planner import PlannerAgent
from agents.researcher import ResearchAgent
from agents.validator import ValidationAgent
from backend.database import (
    check_connection,
    create_goal,
    get_alerts,
    get_all_goals,
    init_db,
)
from backend.logging_config import configure_logging
from scheduler.monitor import (
    list_active_monitors,
    shutdown_scheduler,
    start_monitor,
    start_scheduler,
    stop_monitor,
)
from workflow.graph import run_workflow


configure_logging()

app = FastAPI(title="ScoutFlow API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class GoalCreate(BaseModel):
    query: str
    preferences: list[str]


class PlanRequest(BaseModel):
    query: str
    preferences: list[str] | None = None


@app.on_event("startup")
def startup() -> None:
    init_db()
    start_scheduler()


@app.on_event("shutdown")
def shutdown() -> None:
    shutdown_scheduler()


@app.get("/")
def root() -> dict[str, str]:
    return {"name": "ScoutFlow", "status": "running"}


@app.get("/health")
def health() -> dict[str, str]:
    check_connection()
    return {"status": "ok", "database": "connected"}


@app.post("/goal")
def add_goal(goal: GoalCreate) -> dict:
    return create_goal(goal.query, goal.preferences)


@app.get("/goals")
def list_goals() -> list[dict]:
    return get_all_goals()


@app.post("/plan")
def plan_goal(request: PlanRequest) -> dict:
    planner = PlannerAgent()
    return planner.plan_goal(request.query, request.preferences)


@app.post("/research")
def research_goal(request: PlanRequest) -> dict:
    planner = PlannerAgent()
    researcher = ResearchAgent()
    plan = planner.plan_goal(request.query, request.preferences)
    return researcher.research(plan)


@app.post("/validate")
def validate_goal(request: PlanRequest) -> dict:
    planner = PlannerAgent()
    researcher = ResearchAgent()
    validator = ValidationAgent()
    plan = planner.plan_goal(request.query, request.preferences)
    research_output = researcher.research(plan)
    return validator.validate(research_output)


@app.post("/insights")
def generate_insights(request: PlanRequest) -> dict:
    final_state = run_workflow(request.query, request.preferences)
    return final_state.get("insights", {})


class MonitorStartRequest(BaseModel):
    interval_minutes: int | None = None


@app.post("/monitor/start/{goal_id}")
def monitor_start(goal_id: int, request: MonitorStartRequest | None = None) -> dict:
    interval = request.interval_minutes if request else None
    try:
        return start_monitor(goal_id, interval)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@app.post("/monitor/stop/{goal_id}")
def monitor_stop(goal_id: int) -> dict:
    return stop_monitor(goal_id)


@app.get("/monitor/active")
def monitor_active() -> list[dict]:
    return list_active_monitors()


@app.get("/alerts")
def list_alerts(limit: int = 50) -> list[dict]:
    return get_alerts(limit=limit)


@app.get("/alerts/{goal_id}")
def list_alerts_for_goal(goal_id: int, limit: int = 50) -> list[dict]:
    return get_alerts(goal_id=goal_id, limit=limit)
