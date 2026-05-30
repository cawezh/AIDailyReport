"""ProductHunt Trending 页面解析"""
import requests
from bs4 import BeautifulSoup


def fetch_producthunt(max_items: int = 30) -> list[dict]:
    """
    抓取 ProductHunt 首页热门产品。
    返回: [{"title": "...", "url": "...", "description": "...", "votes": 0, "source": "producthunt"}, ...]
    """
    url = "https://www.producthunt.com/"
    headers = {"User-Agent": "Mozilla/5.0"}
    resp = requests.get(url, headers=headers, timeout=30)
    resp.raise_for_status()

    soup = BeautifulSoup(resp.text, "html.parser")
    results = []

    for item in soup.find_all("div", attrs={"data-test": "post-item"})[:max_items]:
        title_el = item.find("a", attrs={"data-test": "post-name"})
        desc_el = item.find("a", attrs={"data-test": "post-tagline"})
        vote_el = item.find("span", attrs={"data-test": "vote-button"})

        if not title_el:
            continue

        results.append({
            "title": title_el.text.strip(),
            "url": "https://www.producthunt.com" + (title_el.get("href") or ""),
            "description": desc_el.text.strip() if desc_el else "",
            "votes": _parse_votes(vote_el.text if vote_el else "0"),
            "source": "producthunt",
        })

    return results


def _parse_votes(text: str) -> int:
    import re
    nums = re.findall(r"\d+", text)
    return int(nums[0]) if nums else 0
