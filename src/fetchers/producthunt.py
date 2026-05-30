"""ProductHunt — 使用官方 GraphQL API"""
import requests
from src.config import get_env

API_URL = "https://api.producthunt.com/v2/api/graphql"

POSTS_QUERY = """
{
  posts(order: VOTES, first: 30) {
    edges {
      node {
        id
        name
        tagline
        url
        votesCount
        website
        description
      }
    }
  }
}
"""


def fetch_producthunt(max_items: int = 30) -> list[dict]:
    """
    通过 ProductHunt v2 GraphQL API 获取今日热门产品。
    需要设置环境变量 PRODUCTHUNT_TOKEN（免费，在 https://api.producthunt.com/v2/oauth/applications 申请）。

    返回: [{"title": "...", "url": "...", "description": "...", "votes": 0, "source": "producthunt"}, ...]
    """
    token = get_env("PRODUCTHUNT_TOKEN")
    if not token:
        print("[producthunt] PRODUCTHUNT_TOKEN not set, skipping (get a free token at https://api.producthunt.com/v2/oauth/applications)")
        return []

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }

    try:
        resp = requests.post(API_URL, json={"query": POSTS_QUERY}, headers=headers, timeout=30)
        resp.raise_for_status()
        data = resp.json()
    except requests.RequestException as e:
        print(f"[producthunt] API request failed: {e}")
        return []

    if "errors" in data:
        print(f"[producthunt] API error: {data['errors']}")
        return []

    posts = data.get("data", {}).get("posts", {}).get("edges", [])
    results = []
    for edge in posts[:max_items]:
        node = edge.get("node", {})
        results.append({
            "title": node.get("name", ""),
            "url": node.get("url", ""),
            "description": node.get("tagline", "") or node.get("description", ""),
            "votes": node.get("votesCount", 0),
            "source": "producthunt",
        })

    print(f"[producthunt] Fetched {len(results)} products")
    return results
