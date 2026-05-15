from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from urllib.parse import urlparse


MAX_VALIDATED_FINDINGS = 10
MIN_CONFIDENCE_SCORE = 5
HIGH_CONFIDENCE_SCORE = 10
MEDIUM_CONFIDENCE_SCORE = 7
TRUSTED_SOURCES = {
    "techcrunch": 5,
    "yourstory": 5,
    "economic times": 5,
    "the economic times": 5,
    "venturebeat": 5,
    "analytics india magazine": 5,
    "india today": 5,
}
MEDIUM_SOURCES = {
    "yahoo": 3,
    "business standard": 3,
    "inc42": 3,
    "moneycontrol": 3,
    "crunchbase": 3,
    "startup fortune": 3,
    "indian startup times": 3,
}
TITLE_BOOST_KEYWORDS = {
    "funding",
    "fund",
    "raise",
    "raises",
    "raised",
    "launch",
    "launches",
    "startup",
    "github",
    "open",
    "source",
    "release",
    "releases",
    "acquisition",
    "hiring",
}
CLICKBAIT_TERMS = {
    "shocking",
    "unbelievable",
    "everything",
    "you won't believe",
    "dhamaka",
    "game-changer",
    "game changer",
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


class ValidationAgent:
    def validate(self, research_output: dict) -> dict:
        goal = research_output.get("goal", "")
        findings = research_output.get("findings", [])
        unique_findings = []
        seen = set()
        filtered_out_count = 0

        for finding in findings:
            key = _dedupe_key(finding)
            if not key or key in seen:
                filtered_out_count += 1
                continue
            seen.add(key)
            unique_findings.append(finding)

        scored_findings = []
        topic_counts = _topic_counts(unique_findings)

        for finding in unique_findings:
            score = _confidence_score(finding, topic_counts)
            if score < MIN_CONFIDENCE_SCORE:
                filtered_out_count += 1
                continue

            validated = dict(finding)
            validated["confidence"] = _confidence_label(score)
            validated["_score"] = score
            scored_findings.append(validated)

        scored_findings.sort(key=lambda item: item["_score"], reverse=True)
        filtered_out_count += max(0, len(scored_findings) - MAX_VALIDATED_FINDINGS)
        validated_findings = [
            _public_finding(finding)
            for finding in scored_findings[:MAX_VALIDATED_FINDINGS]
        ]

        return {
            "goal": goal,
            "validated_findings": validated_findings,
            "metadata": {
                "initial_findings": len(findings),
                "validated_findings": len(validated_findings),
                "filtered_out_count": filtered_out_count,
                "generated_at": datetime.now().replace(microsecond=0).isoformat(),
            },
        }


def _confidence_score(finding: dict, topic_counts: dict[str, int]) -> int:
    title = finding.get("title") or finding.get("name", "")
    score = _source_trust_score(finding)
    score += _recency_score(finding)
    score += _title_quality_score(title)
    score += _cross_signal_score(title, topic_counts)
    return score


def _source_trust_score(finding: dict) -> int:
    if finding.get("type") == "github":
        stars = finding.get("stars", 0)
        if stars >= 1000:
            return 5
        if stars >= 100:
            return 4
        return 3

    source_name = _publisher_name(finding).lower()
    for trusted_source, score in TRUSTED_SOURCES.items():
        if trusted_source in source_name:
            return score
    for medium_source, score in MEDIUM_SOURCES.items():
        if medium_source in source_name:
            return score
    return 2


def _recency_score(finding: dict) -> int:
    date_text = finding.get("published") or finding.get("latest_update", "")
    parsed_date = _parse_date(date_text)
    if not parsed_date:
        return 0

    age_days = (datetime.now(timezone.utc) - parsed_date).days
    if age_days <= 30:
        return 3
    if age_days <= 90:
        return 2
    if age_days <= 365:
        return 0
    return -2


def _title_quality_score(title: str) -> int:
    title_text = title.lower()
    title_words = set(_keywords(title))
    score = 0

    for keyword in TITLE_BOOST_KEYWORDS:
        if keyword in title_words:
            score += 1

    if "!!!" in title or any(term in title_text for term in CLICKBAIT_TERMS):
        score -= 2

    if len(title_words) < 3:
        score -= 1

    return score


def _cross_signal_score(title: str, topic_counts: dict[str, int]) -> int:
    score = 0
    for keyword in _keywords(title):
        count = topic_counts.get(keyword, 0)
        if count >= 3:
            score += 1
    return min(score, 3)


def _topic_counts(findings: list[dict]) -> dict[str, int]:
    counts = {}
    for finding in findings:
        title = finding.get("title") or finding.get("name", "")
        for keyword in set(_keywords(title)):
            counts[keyword] = counts.get(keyword, 0) + 1
    return counts


def _publisher_name(finding: dict) -> str:
    title = finding.get("title", "")
    if " - " in title:
        return title.rsplit(" - ", 1)[1]

    link = finding.get("link", "")
    domain = urlparse(link).netloc.lower().replace("www.", "")
    return domain


def _parse_date(date_text: str) -> datetime | None:
    if not date_text:
        return None

    try:
        parsed = parsedate_to_datetime(date_text)
    except (TypeError, ValueError):
        try:
            parsed = datetime.fromisoformat(date_text.replace("Z", "+00:00"))
        except ValueError:
            return None

    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _confidence_label(score: int) -> str:
    if score >= HIGH_CONFIDENCE_SCORE:
        return "high"
    if score >= MEDIUM_CONFIDENCE_SCORE:
        return "medium"
    return "low"


def _public_finding(finding: dict) -> dict:
    return {key: value for key, value in finding.items() if key != "_score"}


def _dedupe_key(finding: dict) -> str:
    link = finding.get("link") or finding.get("url")
    if link:
        return link.strip().lower()
    title = finding.get("title") or finding.get("name", "")
    return title.strip().lower()


def _keywords(text: str) -> list[str]:
    words = []
    for raw_word in text.replace("_", " ").replace("-", " ").split():
        word = raw_word.strip(".,:;!?()[]{}\"'").lower()
        if word and word not in STOP_WORDS:
            words.append(_singularize(word))
    return _unique(words)


def _singularize(word: str) -> str:
    if word == "indian":
        return "india"
    if word == "launches":
        return "launch"
    if len(word) > 4 and word.endswith("ies"):
        return f"{word[:-3]}y"
    if len(word) > 3 and word.endswith("s"):
        return word[:-1]
    return word


def _unique(items: list[str]) -> list[str]:
    seen = set()
    result = []
    for item in items:
        if item and item not in seen:
            seen.add(item)
            result.append(item)
    return result
