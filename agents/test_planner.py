import json
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from agents.planner import PlannerAgent


def print_plan(title: str, plan: dict) -> None:
    print("\n" + "=" * 60)
    print(title)
    print("=" * 60)
    print(json.dumps(plan, indent=2))


def main() -> None:
    planner = PlannerAgent()

    print_plan(
        "Example 1: Tell about latest GPU market",
        planner.plan_goal("Tell about latest GPU market"),
    )

    print_plan(
        "Example 2: Track AI startups in India",
        planner.plan_goal(
            "Track AI startups in India",
            preferences=["funding", "launches", "github"],
        ),
    )

    print_plan(
        "Example 3: Monitor fintech competitors in Southeast Asia",
        planner.plan_goal("Monitor fintech competitors in Southeast Asia"),
    )


if __name__ == "__main__":
    main()
