"""GitHub Search API"""
import requests
from datetime import datetime, timedelta

SEARCH_URL = "https://api.github.com/search/repositories"


def fetch_github_search(queries: list[str], per_query: int = 10) -> list[dict]:
    """
    对每个查询词搜索仓库，按 star 排序。
    返回: [{"title": "owner/repo", "url": "...", "description": "...", "stars": 0, "language": "...", "source": "github_search", "query": "..."}, ...]
    """
    headers = {"Accept": "application/vnd.github.v3+json"}
    results = []

    # 搜索最近 7 天更新的仓库
    since = (datetime.utcnow() - timedelta(days=7)).strftime("%Y-%m-%d")

    for query in queries:
        params = {
            "q": f"{query} pushed:>={since}",
            "sort": "stars",
            "order": "desc",
            "per_page": per_query,
        }
        try:
            resp = requests.get(SEARCH_URL, headers=headers, params=params, timeout=30)
            resp.raise_for_status()
            data = resp.json()

            for item in data.get("items", []):
                results.append({
                    "title": item["full_name"],
                    "url": item["html_url"],
                    "description": item.get("description") or "",
                    "stars": item.get("stargazers_count", 0),
                    "language": item.get("language") or "",
                    "source": "github_search",
                    "query": query,
                    "topics": item.get("topics", []),
                    "updated_at": item.get("updated_at", ""),
                })
        except requests.RequestException:
            continue  # 单个查询失败不影响整体

    return _deduplicate(results)


def _deduplicate(items: list[dict]) -> list[dict]:
    seen = set()
    unique = []
    for item in items:
        if item["url"] not in seen:
            seen.add(item["url"])
            unique.append(item)
    return unique
