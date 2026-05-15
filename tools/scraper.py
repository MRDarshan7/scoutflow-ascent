from bs4 import BeautifulSoup
import requests


def scrape_article(url: str) -> dict:
    try:
        from newspaper import Article

        article = Article(url)
        article.download()
        article.parse()

        try:
            article.nlp()
        except Exception:
            pass

        if article.title or article.text:
            return {
                "title": article.title or "",
                "text": article.text or "",
                "authors": article.authors or [],
                "publish_date": article.publish_date.isoformat()
                if article.publish_date
                else "",
                "summary": article.summary or "",
            }
    except Exception:
        pass

    try:
        response = requests.get(url, timeout=10, headers={"User-Agent": "ScoutFlow-Hackathon"})
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")
        title = soup.title.string.strip() if soup.title and soup.title.string else ""
        text = soup.get_text(separator="\n", strip=True)
        return {
            "title": title,
            "text": text[:5000],
            "authors": [],
            "publish_date": "",
            "summary": "",
        }
    except requests.RequestException as exc:
        return {
            "title": "",
            "text": "",
            "authors": [],
            "publish_date": "",
            "summary": "",
            "error": str(exc),
        }
