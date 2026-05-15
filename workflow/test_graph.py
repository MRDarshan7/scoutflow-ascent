"""Manual integration test for the LangGraph workflow.

Run with:

    python -m workflow.test_graph

It executes the full pipeline (planner -> research -> validation ->
insight) for a couple of representative queries and pretty-prints every
intermediate state bucket so you can verify Gemini-enhanced quality is
preserved.
"""
import json
import sys

from workflow.graph import run_workflow


SAMPLE_QUERIES = [
    {
        "query": "Tell me about the latest GPU market, major players, pricing trends, AI demand, and what changes are happening recently",
        "preferences": [],
    },
    {
        "query": "Tell about the latest stock market trends in india",
        "preferences": [],
    },
    {
        "query": "Track AI startups in India",
        "preferences": ["funding", "launches"],
    },
]


def _section(title: str) -> None:
    print()
    print("=" * 80)
    print(title)
    print("=" * 80)


def _dump(obj: object) -> None:
    print(json.dumps(obj, indent=2, ensure_ascii=False, default=str))


def run(query: str, preferences: list[str]) -> None:
    _section(f"QUERY: {query}")
    state = run_workflow(query, preferences)

    _section("PLAN")
    _dump(state.get("plan", {}))

    _section("RESEARCH")
    _dump(state.get("research", {}))

    _section("VALIDATED")
    _dump(state.get("validated", {}))

    _section("INSIGHTS (final /insights response)")
    _dump(state.get("insights", {}))


def main() -> None:
    queries = SAMPLE_QUERIES
    if len(sys.argv) > 1:
        queries = [{"query": " ".join(sys.argv[1:]), "preferences": []}]

    for item in queries:
        run(item["query"], item["preferences"])


if __name__ == "__main__":
    main()
