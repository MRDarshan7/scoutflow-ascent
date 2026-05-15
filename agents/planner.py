from datetime import datetime

from tools.gemini_helper import refine_plan_with_gemini


class PlannerAgent:
    def plan_goal(self, goal_query: str, preferences: list[str] | None = None) -> dict:
        query_text = _normalize(goal_query)
        targets = []
        monitoring_focus = []
        research_context = []

        if _contains_any(query_text, ["startup", "company", "founder"]):
            targets.extend(["funding", "launches", "hiring"])
            monitoring_focus.extend(["startup growth", "expansion", "market movement"])

        if _contains_any(query_text, ["github", "open source", "repo", "code"]):
            targets.extend(["github", "releases", "engineering_activity"])
            monitoring_focus.extend(
                ["repository activity", "contributor growth", "release cadence"]
            )

        if _contains_any(query_text, ["competitor", "market", "industry"]):
            targets.extend(["acquisitions", "pricing", "launches", "market_share", "availability"])
            monitoring_focus.extend(
                ["competitor movement", "market shifts", "product launches"]
            )

        if _contains_any(query_text, ["ai", "machine learning", "llm"]):
            research_context.extend(
                ["AI product launches", "model releases", "ecosystem movement"]
            )

        if preferences:
            targets.extend(preferences)

        targets = _unique(targets)
        sources = _sources_for_targets(targets)
        research_queries = _generate_research_queries(goal_query, query_text, targets)
        monitoring_focus = _unique(monitoring_focus + research_context)
        source_priority = _source_priority(query_text, sources)
        priority = "high" if _is_high_priority(query_text) else "medium"

        plan = {
            "goal": goal_query,
            "targets": targets,
            "sources": sources,
            "research_queries": research_queries,
            "monitoring_focus": monitoring_focus,
            "entities": [],
            "source_priority": source_priority,
            "priority": priority,
            "generated_at": datetime.now().replace(microsecond=0).isoformat(),
        }
        return _apply_gemini_plan_refinement(goal_query, plan)


def _sources_for_targets(targets: list[str]) -> list[str]:
    sources = []

    for target in targets:
        if target in {
            "funding",
            "launches",
            "hiring",
            "acquisitions",
            "pricing",
            "releases",
            "market_share",
            "availability",
        }:
            sources.extend(["google_news", "rss"])
        if target in {"github", "engineering_activity"}:
            sources.append("github")

    return _unique(sources)


def _generate_research_queries(goal: str, query_text: str, targets: list[str]) -> list[str]:
    subject = _query_subject(goal, query_text)
    queries = []

    for target in targets:
        if target == "github":
            queries.append(f"{subject} GitHub")
            queries.append(f"{subject} repository activity")
        elif target == "engineering_activity":
            queries.append(f"{subject} engineering activity")
        elif target == "releases":
            queries.append(f"{subject} releases")
        else:
            queries.append(f"{subject} {_target_search_phrase(target)}")

    return _unique(queries)[:8]


def _apply_gemini_plan_refinement(goal_query: str, plan: dict) -> dict:
    refinement = refine_plan_with_gemini(goal_query, plan)
    if not refinement:
        return plan

    refined_plan = dict(plan)
    refined_plan["targets"] = _unique(
        plan["targets"] + _string_list(refinement.get("extra_targets", []))
    )
    refined_plan["research_queries"] = _unique(
        plan["research_queries"] + _string_list(refinement.get("extra_queries", []))
    )[:8]
    refined_plan["monitoring_focus"] = _unique(
        plan["monitoring_focus"] + _string_list(refinement.get("monitoring_focus", []))
    )
    refined_plan["entities"] = _unique(_string_list(refinement.get("entities", [])))
    refined_plan["sources"] = _unique(plan["sources"] + _sources_for_targets(refined_plan["targets"]))
    refined_plan["source_priority"] = _source_priority(
        _normalize(goal_query), refined_plan["sources"]
    )
    return refined_plan


def _target_search_phrase(target: str) -> str:
    return target.replace("_", " ")


def _query_subject(goal: str, query_text: str) -> str:
    words = []
    stop_words = {
        "track",
        "monitor",
        "watch",
        "find",
        "research",
        "tell",
        "latest",
        "the",
        "a",
        "an",
        "for",
        "about",
        "on",
    }

    for word in goal.replace("-", " ").split():
        clean_word = word.strip(".,:;!?()[]{}\"'").lower()
        if clean_word and clean_word not in stop_words:
            words.append(word.strip(".,:;!?()[]{}\"'"))

    if _contains_any(query_text, ["ai", "machine learning", "llm"]) and not any(
        word.lower() in {"ai", "machine", "learning", "llm"} for word in words
    ):
        words.insert(0, "AI")

    return " ".join(words[:6]) if words else goal.strip()


def _source_priority(query_text: str, sources: list[str]) -> dict:
    scores = {source: 5 for source in sources}

    if _contains_any(query_text, ["github", "open source", "repo", "code"]):
        scores["github"] = 10
        if "google_news" in scores:
            scores["google_news"] = 7
        if "rss" in scores:
            scores["rss"] = 6

    if _contains_any(query_text, ["startup", "company", "founder", "market", "competitor", "industry"]):
        if "google_news" in scores:
            scores["google_news"] = max(scores["google_news"], 8)
        if "rss" in scores:
            scores["rss"] = max(scores["rss"], 7)
        if "github" in scores and scores["github"] < 10:
            scores["github"] = 6

    return dict(sorted(scores.items(), key=lambda item: item[1], reverse=True))


def _is_high_priority(query_text: str) -> bool:
    return any(keyword in query_text for keyword in ["startup", "competitor", "market"])


def _contains_any(text: str, keywords: list[str]) -> bool:
    return any(keyword in text for keyword in keywords)


def _normalize(text: str) -> str:
    return text.lower().strip()


def _unique(items: list[str]) -> list[str]:
    seen = set()
    result = []

    for item in items:
        clean_item = item.strip().lower()
        if clean_item and clean_item not in seen:
            seen.add(clean_item)
            result.append(clean_item)

    return result


def _string_list(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item).strip() for item in value if str(item).strip()]
