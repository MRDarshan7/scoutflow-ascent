import json

from planner import PlannerAgent


def print_plan(title: str, plan: dict) -> None:
    print("\n" + "=" * 60)
    print(title)
    print("=" * 60)
    print(json.dumps(plan, indent=2))


def main() -> None:
    planner = PlannerAgent()

    print_plan(
        "Example 1: Track AI startups in India",
        planner.plan_goal(
            "Track AI startups in India",
            preferences=["funding", "launches", "github"],
        ),
    )

    print_plan(
        "Example 2: Track open source AI competitors",
        planner.plan_goal("Track open source AI competitors"),
    )

    print_plan(
        "Example 3: Monitor cybersecurity startups",
        planner.plan_goal("Monitor cybersecurity startups"),
    )

    print_plan(
        "Example 4: Track fintech market competitors",
        planner.plan_goal("Track fintech market competitors"),
    )


if __name__ == "__main__":
    main()
