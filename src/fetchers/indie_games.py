"""itch.io 独立游戏 Trending"""
import requests
from bs4 import BeautifulSoup


def fetch_indie_games(max_items: int = 20) -> list[dict]:
    """
    抓取 itch.io 热门独立游戏。
    返回: [{"title": "...", "url": "...", "description": "...", "score": 0, "source": "itch.io"}, ...]
    """
    url = "https://itch.io/games/top-rated"
    headers = {"User-Agent": "Mozilla/5.0"}
    resp = requests.get(url, headers=headers, timeout=30)
    resp.raise_for_status()

    soup = BeautifulSoup(resp.text, "html.parser")
    results = []

    for cell in soup.find_all("div", class_="game_cell")[:max_items]:
        title_el = cell.find("a", class_="title")
        desc_el = cell.find("div", class_="game_text")
        if not title_el:
            continue

        results.append({
            "title": title_el.text.strip(),
            "url": title_el.get("href", ""),
            "description": desc_el.text.strip()[:200] if desc_el else "",
            "score": 0,
            "source": "itch.io",
        })

    return results
