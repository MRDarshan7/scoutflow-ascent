import requests


GITHUB_API = "https://api.github.com"
HEADERS = {
    "Accept": "application/vnd.github+json",
    "User-Agent": "ScoutFlow-Hackathon",
}


def get_repo_info(owner: str, repo: str) -> dict:
    url = f"{GITHUB_API}/repos/{owner}/{repo}"

    try:
        response = requests.get(url, headers=HEADERS, timeout=10)
        if response.status_code in (403, 429):
            return {"error": "GitHub API rate limit reached"}
        if response.status_code == 404:
            return {"error": "Repository not found"}
        response.raise_for_status()
        data = response.json()
    except requests.RequestException as exc:
        return {"error": str(exc)}

    return {
        "name": data.get("name", ""),
        "stars": data.get("stargazers_count", 0),
        "forks": data.get("forks_count", 0),
        "open_issues": data.get("open_issues_count", 0),
        "latest_update": data.get("updated_at", ""),
    }


def search_repositories(query: str) -> list[dict]:
    url = f"{GITHUB_API}/search/repositories"
    params = {"q": query, "sort": "stars", "order": "desc", "per_page": 5}

    try:
        response = requests.get(url, headers=HEADERS, params=params, timeout=10)
        if response.status_code in (403, 429):
            return [{"error": "GitHub API rate limit reached"}]
        response.raise_for_status()
        data = response.json()
    except requests.RequestException as exc:
        return [{"error": str(exc)}]

    results = []
    for item in data.get("items", [])[:5]:
        results.append(
            {
                "name": item.get("name", ""),
                "full_name": item.get("full_name", ""),
                "stars": item.get("stargazers_count", 0),
                "forks": item.get("forks_count", 0),
                "open_issues": item.get("open_issues_count", 0),
                "latest_update": item.get("updated_at", ""),
                "url": item.get("html_url", ""),
            }
        )

    return results
