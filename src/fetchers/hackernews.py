"""Hacker News API"""
import requests

TOP_STORIES_URL = "https://hacker-news.firebaseio.com/v0/topstories.json"
ITEM_URL = "https://hacker-news.firebaseio.com/v0/item/{}.json"


def fetch_hackernews(max_items: int = 100) -> list[dict]:
    """
    获取 HN 首页前 N 条。
    返回: [{"title": "...", "url": "...", "description": "", "points": 0, "comments": 0, "source": "hackernews"}, ...]
    """
    headers = {"Accept": "application/json"}
    resp = requests.get(TOP_STORIES_URL, headers=headers, timeout=30)
    resp.raise_for_status()
    story_ids = resp.json()[:max_items]

    results = []
    for sid in story_ids:
        try:
            r = requests.get(ITEM_URL.format(sid), headers=headers, timeout=10)
            r.raise_for_status()
            item = r.json()
            if item and item.get("type") == "story":
                results.append({
                    "title": item.get("title", ""),
                    "url": item.get("url") or f"https://news.ycombinator.com/item?id={sid}",
                    "description": "",
                    "points": item.get("score", 0),
                    "comments": item.get("descendants", 0),
                    "source": "hackernews",
                })
        except requests.RequestException:
            continue

    return results
