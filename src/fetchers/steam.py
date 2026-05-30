"""Steam — 通过 Steam Store API 获取热门/新游戏"""
import requests
from datetime import datetime, timedelta

STEAM_FEATURED_URL = "https://store.steampowered.com/api/featuredcategories"
STEAM_APP_URL = "https://store.steampowered.com/api/appdetails"
STEAM_SEARCH_URL = "https://store.steampowered.com/api/storesearch"


def fetch_steam(max_items: int = 20) -> list[dict]:
    """
    通过 Steam Store API 获取热门游戏和新游戏。
    无需 API Key。

    返回: [{"title": "...", "url": "...", "description": "...", "score": 0, "source": "steam"}, ...]
    """
    results = []

    try:
        resp = requests.get(STEAM_FEATURED_URL, timeout=15)
        resp.raise_for_status()
        data = resp.json()
    except requests.RequestException as e:
        print(f"[steam] API request failed: {e}")
        return []

    # 从 featured_categories 中提取游戏
    seen_ids = set()

    # 1. 特惠游戏 (specials)
    specials = data.get("specials", {}).get("items", [])
    for item in specials[:max_items]:
        app_id = item.get("id")
        if not app_id or app_id in seen_ids:
            continue
        seen_ids.add(app_id)
        results.append(_make_item(item, app_id, "热门特惠"))
        if len(results) >= max_items:
            break

    # 2. 热销游戏 (top_sellers)
    if len(results) < max_items:
        top_sellers = data.get("top_sellers", {}).get("items", [])
        for item in top_sellers[:max_items]:
            app_id = item.get("id")
            if not app_id or app_id in seen_ids:
                continue
            seen_ids.add(app_id)
            results.append(_make_item(item, app_id, "热销"))
            if len(results) >= max_items:
                break

    # 3. 新品 (new_releases)
    if len(results) < max_items:
        new_releases = data.get("new_releases", {}).get("items", [])
        for item in new_releases[:max_items]:
            app_id = item.get("id")
            if not app_id or app_id in seen_ids:
                continue
            seen_ids.add(app_id)
            results.append(_make_item(item, app_id, "新品"))
            if len(results) >= max_items:
                break

    print(f"[steam] Fetched {len(results)} games")
    return results


def _make_item(item: dict, app_id: int, tag: str) -> dict:
    """构建标准 item 格式"""
    name = item.get("name", "")
    # Steam 游戏页 URL
    url = f"https://store.steampowered.com/app/{app_id}/"

    # 折扣信息
    discount_pct = item.get("discount_percent", 0) or 0
    original = item.get("original_price", 0) or 0
    final = item.get("final_price", 0) or 0

    # 价格描述
    price_str = ""
    if original > 0:
        if discount_pct > 0:
            price_str = f"折后{final/100:.2f}元(原{original/100:.2f}元, -{discount_pct}%)"
        else:
            price_str = f"{original/100:.2f}元"

    description = f"{tag}游戏"
    if price_str:
        description += f" | {price_str}"

    return {
        "title": name,
        "url": url,
        "description": description,
        "score": item.get("rating", 0),
        "source": "steam",
        "categories": ["game"],
        "matched_keywords": ["steam-game"],
    }
