from datetime import datetime, timezone

from tools.github_monitor import search_repositories
from tools.rss_reader import fetch_rss_feed, search_google_news


TECHCRUNCH_RSS_URL = "https://techcrunch.com/feed/"
MAX_FINDINGS = 15
NEWS_MIN_SCORE = 2
RSS_MIN_SCORE = 2
GITHUB_MIN_SCORE = 2
GITHUB_MIN_STARS = 5
GITHUB_RECENT_YEAR = 2024
NOISY_GITHUB_WORDS = {
    "track",
    "monitor",
    "watch",
    "competitor",
    "competitors",
    "market",
    "industry",
    "github",
    "repository",
    "repositories",
    "repo",
    "repos",
    "activity",
}
STOP_WORDS = {
    "a",
    "an",
    "and",
    "are",
    "for",
    "from",
    "in",
    "of",
    "on",
    "the",
    "to",
    "with",
}
KEYWORD_EXPANSIONS = {
    "ai": ["artificial", "intelligence", "llm", "model"],
    "startup": ["startups", "founder", "venture"],
    "startups": ["startup", "founder", "venture"],
    "india": ["indian"],
    "funding": ["fund", "funding", "funded", "raise", "raises", "raised", "investment"],
    "hiring": ["hire", "hiring", "jobs", "talent"],
    "launches": ["launch", "launches", "launched", "unveils", "announces"],
    "releases": ["release", "releases", "released"],
    "github": ["github", "repo", "repository"],
    "engineering_activity": ["engineering", "developer", "contributors", "commits"],
    "acquisitions": ["acquisition", "acquires", "acquired", "merger"],
    "pricing": ["pricing", "price", "plans"],
}


class ResearchAgent:
    def research(self, plan: dict) -> dict:
        goal = plan.get("goal", "")
        queries = plan.get("research_queries", [])
        targets = plan.get("targets", [])
        sources = _ordered_sources(plan.get("sources", []), plan.get("source_priority", {}))
        relevance_terms = _relevance_terms(goal, targets, queries)
        candidates = []
        seen = set()
        queries_executed = []
        sources_used = []
        filtered_out_count = 0
        rss_fetched = False

        for query in queries:
            for source in sources:
                if source == "google_news":
                    results = search_google_news(query)
                    queries_executed.append(query)
                    sources_used.append("google_news")
                    filtered_out_count += _add_news_findings(
                        candidates, seen, results, "google_news", relevance_terms, NEWS_MIN_SCORE
                    )

                elif source == "rss" and not rss_fetched:
                    results = fetch_rss_feed(TECHCRUNCH_RSS_URL, limit=10)
                    queries_executed.append(TECHCRUNCH_RSS_URL)
                    sources_used.append("rss")
                    rss_fetched = True
                    filtered_out_count += _add_news_findings(
                        candidates, seen, results, "rss", relevance_terms, RSS_MIN_SCORE
                    )

                elif source == "github" and _is_github_query(query):
                    github_query = _clean_github_query(query)
                    if not github_query:
                        continue

                    results = search_repositories(github_query)
                    queries_executed.append(github_query)
                    sources_used.append("github")
                    filtered_out_count += _add_github_findings(
                        candidates, seen, results, relevance_terms
                    )

        candidates.sort(key=lambda item: item["relevance_score"], reverse=True)
        findings = [_public_finding(item) for item in candidates[:MAX_FINDINGS]]

        return {
            "goal": goal,
            "findings": findings,
            "metadata": {
                "queries_executed": _unique(queries_executed),
                "sources_used": _unique(sources_used),
                "total_findings": len(findings),
                "filtered_out_count": filtered_out_count,
                "generated_at": datetime.now().replace(microsecond=0).isoformat(),
            },
        }


def _add_news_findings(
    findings: list[dict],
    seen: set[str],
    results: list[dict],
    source_name: str,
    relevance_terms: dict,
    min_score: int,
) -> int:
    filtered_out_count = 0

    for item in results:
        title = item.get("title", "")
        link = item.get("link", "")
        key = _dedupe_key(title, link)
        score = _relevance_score(title, relevance_terms)

        if not key or key in seen or score < min_score:
            filtered_out_count += 1
            continue

        seen.add(key)
        findings.append(
            {
                "type": "news",
                "title": title,
                "link": link,
                "source": source_name,
                "published": item.get("published", ""),
                "relevance_score": score,
            }
        )

    return filtered_out_count


def _add_github_findings(
    findings: list[dict], seen: set[str], results: list[dict], relevance_terms: dict
) -> int:
    filtered_out_count = 0

    for item in results:
        if item.get("error"):
            filtered_out_count += 1
            continue

        name = item.get("full_name") or item.get("name", "")
        url = item.get("url", "")
        key = _dedupe_key(name, url)
        score = _relevance_score(name, relevance_terms)

        if (
            not key
            or key in seen
            or score < GITHUB_MIN_SCORE
            or not _github_matches_core_terms(name, relevance_terms)
            or item.get("stars", 0) <= GITHUB_MIN_STARS
            or not _recent_enough(item.get("latest_update", ""))
        ):
            filtered_out_count += 1
            continue

        seen.add(key)
        findings.append(
            {
                "type": "github",
                "name": name,
                "stars": item.get("stars", 0),
                "url": url,
                "latest_update": item.get("latest_update", ""),
                "relevance_score": score + min(item.get("stars", 0), 1000) // 100,
            }
        )

    return filtered_out_count


def _relevance_terms(goal: str, targets: list[str], queries: list[str]) -> dict:
    exact_terms = _keywords(goal)
    target_terms = _unique([term for target in targets for term in _keywords(target)])
    query_terms = _unique([term for query in queries for term in _keywords(query)])
    expanded_terms = []

    for term in exact_terms + target_terms + query_terms:
        expanded_terms.extend(KEYWORD_EXPANSIONS.get(term, []))

    return {
        "exact": _unique(exact_terms),
        "target": _unique(target_terms),
        "partial": _unique(query_terms + expanded_terms),
    }


def _relevance_score(text: str, relevance_terms: dict) -> int:
    text_words = set(_keywords(text))
    text_blob = " ".join(text_words)
    score = 0

    for term in relevance_terms["exact"]:
        if term in text_words:
            score += 3

    for term in relevance_terms["target"]:
        if term in text_words:
            score += 2

    for term in relevance_terms["partial"]:
        if term in text_words:
            score += 1
        elif len(term) > 3 and term in text_blob:
            score += 1

    return score


def _clean_github_query(query: str) -> str:
    keywords = [
        keyword
        for keyword in _keywords(query)
        if keyword not in NOISY_GITHUB_WORDS
    ]
    return " ".join(_unique(keywords[:5]))


def _github_matches_core_terms(name: str, relevance_terms: dict) -> bool:
    name_words = set(_keywords(name))
    exact_matches = name_words.intersection(relevance_terms["exact"])

    if "ai" in relevance_terms["exact"]:
        ai_terms = {"ai", "llm", "model", "agent", "machine", "learning"}
        return bool(name_words.intersection(ai_terms)) or len(exact_matches) >= 2

    return len(exact_matches) >= 1


def _recent_enough(latest_update: str) -> bool:
    try:
        updated_at = datetime.fromisoformat(latest_update.replace("Z", "+00:00"))
    except ValueError:
        return False

    return updated_at.astimezone(timezone.utc).year >= GITHUB_RECENT_YEAR


def _public_finding(finding: dict) -> dict:
    return {key: value for key, value in finding.items() if key != "relevance_score"}


def _keywords(text: str) -> list[str]:
    words = []

    for raw_word in text.replace("_", " ").replace("-", " ").split():
        word = raw_word.strip(".,:;!?()[]{}\"'").lower()
        if not word or word in STOP_WORDS:
            continue
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


def _ordered_sources(sources: list[str], source_priority: dict) -> list[str]:
    return sorted(
        _unique(sources),
        key=lambda source: source_priority.get(source, 0),
        reverse=True,
    )


def _is_github_query(query: str) -> bool:
    query_text = query.lower()
    return any(
        keyword in query_text
        for keyword in ["github", "repository", "engineering", "open source", "repo"]
    )


def _dedupe_key(title: str, link: str) -> str:
    if link:
        return link.strip().lower()
    return title.strip().lower()


def _unique(items: list[str]) -> list[str]:
    seen = set()
    result = []

    for item in items:
        if item and item not in seen:
            seen.add(item)
            result.append(item)

    return result
