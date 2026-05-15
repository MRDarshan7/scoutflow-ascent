from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from agents.insight import InsightAgent
from agents.planner import PlannerAgent
from agents.researcher import ResearchAgent
from agents.validator import ValidationAgent
from backend.database import check_connection, create_goal, get_all_goals, init_db
from backend.logging_config import configure_logging


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
    planner = PlannerAgent()
    researcher = ResearchAgent()
    validator = ValidationAgent()
    insight = InsightAgent()
    plan = planner.plan_goal(request.query, request.preferences)
    research_output = researcher.research(plan)
    validated_output = validator.validate(research_output)
    return insight.generate_insights(validated_output)
