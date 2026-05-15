import json
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from agents.planner import PlannerAgent
from agents.researcher import ResearchAgent


def print_result(title: str, result: dict) -> None:
    print("\n" + "=" * 60)
    print(title)
    print("=" * 60)
    print(json.dumps(result, indent=2))
    print(f"\nTotal findings: {result['metadata']['total_findings']}")


def run_example(query: str) -> None:
    planner = PlannerAgent()
    researcher = ResearchAgent()
    plan = planner.plan_goal(query)
    result = researcher.research(plan)
    print_result(query, result)


def main() -> None:
    run_example("Track AI startups in India")
    run_example("Track open source AI competitors")
    run_example("Monitor cybersecurity startups")


if __name__ == "__main__":
    main()
