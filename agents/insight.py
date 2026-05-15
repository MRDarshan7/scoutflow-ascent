from datetime import datetime

from tools.gemini_helper import refine_insights_with_gemini


MAX_SUPPORTING_FINDINGS = 5
SIGNAL_RULES = {
    "Funding Growth": {
        "keywords": {"raise", "raises", "raised", "funding", "investment", "million", "capital", "fund"},
        "implication": "Increased market competition likely as companies gain resources to expand.",
        "recommendation": "Monitor funding-heavy competitors and track how they deploy capital.",
    },
    "Hiring Expansion": {
        "keywords": {"hiring", "hire", "jobs", "team", "talent", "recruitment"},
        "implication": "Companies may be scaling products, sales, or entering new markets.",
        "recommendation": "Track hiring patterns for clues about expansion priorities.",
    },
    "Product Expansion": {
        "keywords": {"launch", "launches", "launched", "release", "released", "new", "product", "debut", "unveils"},
        "implication": "Accelerated innovation and faster release cycles are likely.",
        "recommendation": "Watch product launches and compare feature direction against your roadmap.",
    },
    "Engineering Momentum": {
        "keywords": {"github", "repository", "open", "source", "release", "developer", "contributors", "model"},
        "implication": "Open-source or engineering activity suggests fast product iteration.",
        "recommendation": "Watch release cadence, contributors, and repository activity for technical momentum.",
    },
    "Market Consolidation": {
        "keywords": {"acquire", "acquires", "acquired", "acquisition", "merge", "merger"},
        "implication": "Market consolidation may shift competitive positioning and customer choices.",
        "recommendation": "Track acquisitions and partnership moves that could reshape the market.",
    },
}
STOP_WORDS = {
    "a",
    "an",
    "and",
    "are",
    "for",
    "from",
    "in",
    "is",
    "of",
    "on",
    "the",
    "to",
    "with",
}


class InsightAgent:
    def generate_insights(self, validated_output: dict) -> dict:
        goal = validated_output.get("goal", "")
        findings = validated_output.get("validated_findings", [])
        signals = _detect_signals(findings)
        business_implications = _implications_for_signals(signals)
        recommendations = _recommendations_for_signals(signals)
        supporting_findings = findings[:MAX_SUPPORTING_FINDINGS]

        insight_output = {
            "goal": goal,
            "summary": _summary(goal, signals, findings),
            "signals_detected": signals,
            "business_implications": business_implications,
            "recommendations": recommendations,
            "supporting_findings": supporting_findings,
            "metadata": {
                "signals_count": len(signals),
                "recommendations_count": len(recommendations),
                "generated_at": datetime.now().replace(microsecond=0).isoformat(),
            },
        }
        return _apply_gemini_insight_refinement(validated_output, insight_output)


def _detect_signals(findings: list[dict]) -> list[str]:
    signal_scores = {}

    for finding in findings:
        text = _finding_text(finding)
        words = set(_keywords(text))

        for signal, rule in SIGNAL_RULES.items():
            matches = words.intersection(rule["keywords"])
            if matches:
                signal_scores[signal] = signal_scores.get(signal, 0) + len(matches)

    ordered_signals = sorted(signal_scores, key=signal_scores.get, reverse=True)
    return ordered_signals


def _apply_gemini_insight_refinement(validated_output: dict, insight_output: dict) -> dict:
    refinement = refine_insights_with_gemini(validated_output, insight_output)
    if not refinement:
        return insight_output

    refined_output = dict(insight_output)

    signals = _valid_signal_labels(
        _first_present(refinement, ["signals", "signals_detected", "contextual_signals"])
    )
    if signals:
        refined_output["signals_detected"] = signals
        refined_output["metadata"] = dict(refined_output["metadata"])
        refined_output["metadata"]["signals_count"] = len(signals)

    summary = _first_present(refinement, ["summary", "contextual_summary", "analyst_summary"])
    if isinstance(summary, str) and summary.strip():
        refined_output["summary"] = summary.strip()

    implications = _string_list(
        _first_present(refinement, ["business_implications", "implications"])
    )
    if implications:
        refined_output["business_implications"] = implications

    recommendations = _string_list(
        _first_present(refinement, ["recommendations", "recommended_actions", "actions"])
    )
    if recommendations:
        refined_output["recommendations"] = recommendations
        refined_output["metadata"] = dict(refined_output["metadata"])
        refined_output["metadata"]["recommendations_count"] = len(recommendations)

    return refined_output


def _valid_signal_labels(value: object) -> list[str]:
    labels = []
    banned = {
        "future transformation",
        "technology revolution",
        "business excellence",
    }

    if not isinstance(value, list):
        return []

    for item in value:
        label = _string_from_item(item, ["label", "signal", "name", "title"])
        word_count = len(label.split())
        if not label or not 2 <= word_count <= 5:
            continue
        if label.lower() in banned:
            continue
        labels.append(label)

    return _unique(labels)[:5]


def _implications_for_signals(signals: list[str]) -> list[str]:
    return _unique([SIGNAL_RULES[signal]["implication"] for signal in signals])


def _recommendations_for_signals(signals: list[str]) -> list[str]:
    recommendations = [SIGNAL_RULES[signal]["recommendation"] for signal in signals]

    if signals:
        recommendations.append("Review high-confidence findings weekly to spot changes early.")

    return _unique(recommendations)


def _summary(goal: str, signals: list[str], findings: list[dict]) -> str:
    if not findings:
        return f"ScoutFlow did not find enough validated evidence to generate strong insights for: {goal}."

    if not signals:
        return f"ScoutFlow found validated activity for {goal}, but no strong business signal pattern emerged yet."

    signal_text = _human_join([signal.lower() for signal in signals])
    return (
        f"ScoutFlow detected {signal_text} signals across validated findings for {goal}. "
        "These signals suggest the space is active and worth continued monitoring."
    )


def _finding_text(finding: dict) -> str:
    return " ".join(
        [
            finding.get("title", ""),
            finding.get("name", ""),
            finding.get("source", ""),
        ]
    )


def _keywords(text: str) -> list[str]:
    words = []
    for raw_word in text.replace("_", " ").replace("-", " ").split():
        word = raw_word.strip(".,:;!?()[]{}\"'").lower()
        if word and word not in STOP_WORDS:
            words.append(_singularize(word))
    return _unique(words)


def _singularize(word: str) -> str:
    if word == "launches":
        return "launch"
    if word == "raises":
        return "raise"
    if word == "releases":
        return "release"
    if len(word) > 4 and word.endswith("ies"):
        return f"{word[:-3]}y"
    if len(word) > 3 and word.endswith("s"):
        return word[:-1]
    return word


def _human_join(items: list[str]) -> str:
    if len(items) == 1:
        return items[0]
    if len(items) == 2:
        return f"{items[0]} and {items[1]}"
    return f"{', '.join(items[:-1])}, and {items[-1]}"


def _unique(items: list[str]) -> list[str]:
    seen = set()
    result = []
    for item in items:
        if item and item not in seen:
            seen.add(item)
            result.append(item)
    return result


def _string_list(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return [
        text
        for item in value
        if (text := _string_from_item(item, ["text", "summary", "recommendation", "implication", "action"]))
    ]


def _first_present(source: dict, keys: list[str]) -> object:
    for key in keys:
        if key in source:
            return source[key]
    return []


def _string_from_item(item: object, preferred_keys: list[str]) -> str:
    if isinstance(item, str):
        return item.strip()

    if isinstance(item, dict):
        for key in preferred_keys:
            value = item.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()

    return ""
