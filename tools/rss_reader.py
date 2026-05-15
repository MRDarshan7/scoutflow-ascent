from urllib.parse import quote_plus

import feedparser


def fetch_rss_feed(url: str, limit: int | None = None) -> list[dict]:
    try:
        feed = feedparser.parse(url)
    except Exception:
        return []

    if getattr(feed, "bozo", False) and not feed.entries:
        return []

    entries = feed.entries[:limit] if limit else feed.entries
    results = []

    for entry in entries:
        results.append(
            {
                "title": entry.get("title", ""),
                "link": entry.get("link", ""),
                "published": entry.get("published", ""),
                "source": "rss",
            }
        )

    return results


def search_google_news(query: str) -> list[dict]:
    search_query = quote_plus(query)
    url = f"https://news.google.com/rss/search?q={search_query}"
    return fetch_rss_feed(url, limit=10)
