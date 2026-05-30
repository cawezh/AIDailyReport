"""Reddit API — 无需认证即可读取 .json 端点"""
import requests


def fetch_reddit(subreddits: list[str], per_subreddit: int = 25) -> list[dict]:
    """
    获取指定 subreddit 的热门帖子。
    返回: [{"title": "...", "url": "...", "description": "...", "score": 0, "comments": 0, "source": "reddit", "subreddit": "..."}, ...]
    """
    headers = {"User-Agent": "ai-daily-report-bot/1.0"}
    results = []

    for sub in subreddits:
        url = f"https://www.reddit.com/r/{sub}/hot.json"
        params = {"limit": per_subreddit}
        try:
            resp = requests.get(url, headers=headers, params=params, timeout=30)
            resp.raise_for_status()
            data = resp.json()

            for child in data.get("data", {}).get("children", []):
                post = child["data"]
                if post.get("stickied"):
                    continue
                results.append({
                    "title": post.get("title", ""),
                    "url": post.get("url", ""),
                    "description": post.get("selftext", "")[:300],
                    "score": post.get("score", 0),
                    "comments": post.get("num_comments", 0),
                    "source": "reddit",
                    "subreddit": sub,
                })
        except requests.RequestException:
            continue

    return results
