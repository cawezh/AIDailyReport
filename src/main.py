"""主流程 — 周一~周六日报(5项)，周日周报(分析池内所有项目)"""
import sys
import json
from datetime import date, timedelta
from pathlib import Path
from src.config import get_keywords, get_sources, get_env
from src.fetchers import (
    fetch_github_trending, fetch_github_search, fetch_hackernews,
    fetch_reddit, fetch_producthunt, fetch_huggingface,
    fetch_indie_games, fetch_arxiv, fetch_steam,
)
from src.filter import pre_filter
from src.dedup import load_seen, save_seen
from src.llm import summarize, generate_overview, analyze_weekly
from src.reporter import generate_report
from src.dashboard import save_daily_data, update_manifest, generate_index_html, _pick_l1
from src.feishu import send_feishu, send_feishu_weekly
from src.wechat import send_wechat, send_wechat_weekly

ROOT = Path(__file__).resolve().parent.parent
POOL_FILE = ROOT / "reports" / "weekly_pool.json"


# ── Fetch ───────────────────────────────────────────────────

def _fetch_all() -> list[dict]:
    cfg = get_sources()["sources"]
    all_items = []

    def _run(name, fn, **kw):
        print(f"[fetch] {name}...")
        try: return fn(**kw)
        except Exception as e: print(f"[fetch] {name} failed: {e}"); return []

    if cfg.get("github_trending",{}).get("enabled"): all_items.extend(_run("GitHub Trending", fetch_github_trending, max_items=cfg["github_trending"].get("max_items",25)))
    if cfg.get("github_search",{}).get("enabled"): all_items.extend(_run("GitHub Search", fetch_github_search, queries=cfg["github_search"].get("queries",[]), per_query=cfg["github_search"].get("per_query",10)))
    if cfg.get("hackernews",{}).get("enabled"): all_items.extend(_run("Hacker News", fetch_hackernews, max_items=cfg["hackernews"].get("max_items",20)))
    if cfg.get("reddit",{}).get("enabled"): all_items.extend(_run("Reddit", fetch_reddit, subreddits=cfg["reddit"].get("subreddits",[]), per_subreddit=cfg["reddit"].get("per_subreddit",15)))
    if cfg.get("producthunt",{}).get("enabled"): all_items.extend(_run("ProductHunt", fetch_producthunt, max_items=cfg["producthunt"].get("max_items",20)))
    if cfg.get("huggingface",{}).get("enabled"): all_items.extend(_run("HuggingFace", fetch_huggingface, max_items=cfg["huggingface"].get("max_items",20)))
    if cfg.get("indie_games",{}).get("enabled"): all_items.extend(_run("itch.io", fetch_indie_games, max_items=cfg["indie_games"].get("max_items",20)))
    if cfg.get("arxiv",{}).get("enabled"): all_items.extend(_run("arXiv", fetch_arxiv, max_items=cfg["arxiv"].get("max_items",20)))
    if cfg.get("steam",{}).get("enabled"): all_items.extend(_run("Steam", fetch_steam, max_items=cfg["steam"].get("max_items",20)))

    print(f"[fetch] Total raw items: {len(all_items)}")
    return all_items


# ── Pool ────────────────────────────────────────────────────

def _week_key() -> str:
    d = date.today()
    return d.strftime("%G-W%V")

def _load_pool() -> dict:
    if not POOL_FILE.exists(): return {"week": _week_key(), "items": [], "daily_picks": {}}
    data = json.loads(POOL_FILE.read_text())
    if data.get("week") != _week_key(): return {"week": _week_key(), "items": [], "daily_picks": {}}
    return data

def _save_pool(data: dict):
    POOL_FILE.parent.mkdir(parents=True, exist_ok=True)
    POOL_FILE.write_text(json.dumps(data, ensure_ascii=False))


# ── Daily (Mon-Sat) ─────────────────────────────────────────

def _pick_daily(summarized: list[dict]) -> list[dict]:
    """每 L1 取 1 项，共 5 项"""
    picks = []
    for l1 in ['游戏', 'AI', '互联网', '产品', '科研']:
        items = [it for it in summarized if _pick_l1(it) == l1]
        items.sort(key=lambda x: x.get("relevance_score", 0), reverse=True)
        if items: picks.append(items[0])
    return picks


def run_daily():
    print("=== AI Daily ===")
    today = date.today().isoformat()

    items = _fetch_all()
    items = [it for it in items if it["url"] not in load_seen()]
    print(f"[dedup] {len(items)} new items remaining")

    if not items:
        print("[daily] No new items today")
        return

    filtered = pre_filter(items, get_keywords())
    print(f"[filter] {len(filtered)} after keyword filter")
    if not filtered: return

    summarized = summarize(filtered)
    print(f"[llm] Summarized: {len(summarized)}")

    daily_picks = _pick_daily(summarized)
    print(f"[curate] {len(daily_picks)} picks (1 per category)")
    if not daily_picks: return

    save_seen(daily_picks)

    # 推送（链接带日期 hash，直接跳到当天）
    base_url = get_env("DASHBOARD_URL", "https://cawezh.github.io/AIDailyReport/")
    url = f"{base_url}#{today}"
    send_feishu(daily_picks, url)
    send_wechat(daily_picks, url)

    # 存入周池
    pool = _load_pool()
    existing = {it["url"] for it in pool["items"]}
    for it in daily_picks:
        if it["url"] not in existing: pool["items"].append(it)
    pool["daily_picks"][today] = [it["title"] for it in daily_picks]
    _save_pool(pool)

    # Dashboard
    save_daily_data(daily_picks)
    update_manifest(daily_picks)
    generate_index_html()

    print(f"[daily] {len(daily_picks)} picks · Pool {len(pool['items'])} items")
    print(f"=== Done: {today} ===")


# ── Weekly (Sunday) ─────────────────────────────────────────

def run_weekly():
    print("=== AI Weekly ===")
    today = date.today()
    week = _week_key()
    cfg = get_sources()

    pool = _load_pool()
    items = pool.get("items", [])
    print(f"[weekly] Pool: {len(items)} items")

    if not items:
        print("[weekly] No items this week, fallback to daily")
        run_daily()
        return

    # 去重
    seen = set()
    unique = []
    for it in sorted(items, key=lambda x: x.get("relevance_score", 0), reverse=True):
        if it["url"] not in seen:
            unique.append(it); seen.add(it["url"])
    items = unique
    print(f"[weekly] {len(items)} unique items")

    # 深度分析每个项目
    items = analyze_weekly(items)
    print(f"[weekly] Deep analyzed: {len(items)} items")

    # 周报
    week_start = today - timedelta(days=today.weekday())
    week_end = today
    week_range = f"{week_start.strftime('%m.%d')} - {week_end.strftime('%m.%d')}"
    overview = generate_overview(items)

    report_path = generate_report(items, output_dir=cfg["output"]["reports_dir"], overview=overview, week_label=week_range)
    print(f"[report] {report_path}")

    # Dashboard — 周报用 week key 单独页面
    save_daily_data(items, overview=overview, key=week)
    update_manifest(items, overview=overview, key=week, weekly=True)
    generate_index_html()

    # 推送周报
    base_url = get_env("DASHBOARD_URL", "https://cawezh.github.io/AIDailyReport/")
    url = f"{base_url}#{week}"
    l1_order = ['游戏', 'AI', '互联网', '产品', '科研']
    top5 = []
    for l1 in l1_order:
        l1_items = [it for it in items if _pick_l1(it) == l1]
        l1_items.sort(key=lambda x: x.get("relevance_score", 0), reverse=True)
        if l1_items: top5.append(l1_items[0])

    counts = {}
    for it in items:
        pc = it.get("primary_category", "other")
        counts[pc] = counts.get(pc, 0) + 1

    send_feishu_weekly(top5, url, overview, week_range, len(items), counts)
    send_wechat_weekly(top5, url, overview, week_range, len(items), counts)

    # 清空池
    _save_pool({"week": week, "items": [], "daily_picks": {}})
    print(f"=== Week {week} done ===")


# ── Entry ──────────────────────────────────────────────────

def main():
    today = date.today()
    today_str = today.isoformat()

    if get_env("FORCE_RUN") != "1":
        pool = _load_pool()
        if today_str in pool.get("daily_picks", {}):
            print(f"[guard] Already ran today ({today_str}), skipping")
            return

    if today.weekday() == 6:
        run_weekly()
    else:
        run_daily()


if __name__ == "__main__":
    sys.exit(main())
