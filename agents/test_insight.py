import json
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from agents.insight import InsightAgent
from agents.planner import PlannerAgent
from agents.researcher import ResearchAgent
from agents.validator import ValidationAgent


def print_result(title: str, insight_output: dict) -> None:
    print("\n" + "=" * 60)
    print(title)
    print("=" * 60)
    print(json.dumps(insight_output, indent=2))


def run_example(query: str) -> None:
    planner = PlannerAgent()
    researcher = ResearchAgent()
    validator = ValidationAgent()
    insight = InsightAgent()

    plan = planner.plan_goal(query)
    research_output = researcher.research(plan)
    validated_output = validator.validate(research_output)
    insight_output = insight.generate_insights(validated_output)

    print_result(query, insight_output)


def main() -> None:
    run_example("Track AI startups in India")
    run_example("Track open source AI competitors")
    run_example("Track latest indie game startups")


if __name__ == "__main__":
    main()
