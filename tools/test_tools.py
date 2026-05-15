from github_monitor import get_repo_info, search_repositories
from rss_reader import fetch_rss_feed, search_google_news
from scraper import scrape_article


def print_section(title: str) -> None:
    print("\n" + "=" * 60)
    print(title)
    print("=" * 60)


def print_items(items: list[dict], limit: int = 3) -> None:
    for item in items[:limit]:
        print(item)


def main() -> None:
    print_section("RSS Feed")
    rss_results = fetch_rss_feed("https://techcrunch.com/feed/", limit=3)
    print_items(rss_results)

    print_section("Google News RSS")
    news_results = search_google_news("AI startup India")
    print_items(news_results)

    print_section("GitHub Repo Info")
    print(get_repo_info("microsoft", "vscode"))

    print_section("GitHub Repository Search")
    repo_results = search_repositories("AI startup")
    print_items(repo_results)

    print_section("Web Scraper")
    article = scrape_article("https://example.com")
    print(
        {
            "title": article.get("title", ""),
            "text_preview": article.get("text", "")[:300],
            "authors": article.get("authors", []),
            "publish_date": article.get("publish_date", ""),
            "summary": article.get("summary", "")[:300],
            "error": article.get("error", ""),
        }
    )


if __name__ == "__main__":
    main()
