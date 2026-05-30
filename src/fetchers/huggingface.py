"""HuggingFace Models Trending"""
import requests
from bs4 import BeautifulSoup


def fetch_huggingface(max_items: int = 20) -> list[dict]:
    """
    抓取 HuggingFace Models Trending 页面。
    返回: [{"title": "...", "url": "...", "description": "...", "downloads": 0, "source": "huggingface"}, ...]
    """
    url = "https://huggingface.co/models?sort=trending"
    headers = {"User-Agent": "Mozilla/5.0"}
    resp = requests.get(url, headers=headers, timeout=30)
    resp.raise_for_status()

    soup = BeautifulSoup(resp.text, "html.parser")
    results = []

    for article in soup.find_all("article")[:max_items]:
        link = article.find("a")
        if not link:
            continue
        title = link.get("href", "").strip("/")
        desc_el = article.find("p")
        description = desc_el.text.strip()[:200] if desc_el else ""

        results.append({
            "title": title,
            "url": f"https://huggingface.co/{title}",
            "description": description,
            "downloads": 0,
            "source": "huggingface",
        })

    return results
