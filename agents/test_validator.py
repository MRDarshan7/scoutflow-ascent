import json
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from agents.planner import PlannerAgent
from agents.researcher import ResearchAgent
from agents.validator import ValidationAgent


def print_result(title: str, research_output: dict, validation_output: dict) -> None:
    print("\n" + "=" * 60)
    print(title)
    print("=" * 60)
    print(
        f"Research findings: {research_output['metadata']['total_findings']} | "
        f"Validated findings: {validation_output['metadata']['validated_findings']} | "
        f"Filtered out: {validation_output['metadata']['filtered_out_count']}"
    )
    print(json.dumps(validation_output, indent=2))


def run_example(query: str) -> None:
    planner = PlannerAgent()
    researcher = ResearchAgent()
    validator = ValidationAgent()

    plan = planner.plan_goal(query)
    research_output = researcher.research(plan)
    validation_output = validator.validate(research_output)

    print_result(query, research_output, validation_output)


def main() -> None:
    run_example("Track AI startups in India")
    run_example("Track open source AI competitors")
    run_example("Monitor cybersecurity startups")


if __name__ == "__main__":
    main()
