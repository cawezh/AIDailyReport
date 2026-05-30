"""主流程 — 周一~周六轻推 Top 5，周日生成深度周报"""
import sys
import json
from datetime import date, timedelta
from pathlib import Path
from src.config import get_keywords, get_sources, get_env
from src.fetchers import (
    fetch_github_trending,
    fetch_github_search,
    fetch_hackernews,
    fetch_reddit,
    fetch_producthunt,
    fetch_huggingface,
    fetch_indie_games,
    fetch_arxiv,
    fetch_steam,
)
from src.filter import pre_filter
from src.llm import summarize, generate_overview
from src.reporter import generate_report
from src.dashboard import save_daily_data, update_manifest, generate_index_html, _pick_l1, L2_RULES
from src.feishu import send_feishu, send_feishu_weekly
from src.wechat import send_wechat, send_wechat_weekly

ROOT = Path(__file__).resolve().parent.parent
POOL_FILE = ROOT / "reports" / "weekly_pool.json"
SEEN_WEEKLY_FILE = ROOT / "reports" / "seen_weekly.json"


def _fetch_all() -> list[dict]:
    """拉取所有数据源"""
    cfg = get_sources()
    sources_cfg = cfg["sources"]
    all_items = []

    def _run(name, fn, **kw):
        print(f"[fetch] {name}...")
        try:
            return fn(**kw)
        except Exception as e:
            print(f"[fetch] {name} failed: {e}")
            return []

    if sources_cfg.get("github_trending", {}).get("enabled"):
        all_items.extend(_run("GitHub Trending", fetch_github_trending, max_items=sources_cfg["github_trending"].get("max_items", 25)))
    if sources_cfg.get("github_search", {}).get("enabled"):
        all_items.extend(_run("GitHub Search", fetch_github_search, queries=sources_cfg["github_search"].get("queries", []), per_query=sources_cfg["github_search"].get("per_query", 10)))
    if sources_cfg.get("hackernews", {}).get("enabled"):
        all_items.extend(_run("Hacker News", fetch_hackernews, max_items=sources_cfg["hackernews"].get("max_items", 30)))
    if sources_cfg.get("reddit", {}).get("enabled"):
        all_items.extend(_run("Reddit", fetch_reddit, subreddits=sources_cfg["reddit"].get("subreddits", []), per_subreddit=sources_cfg["reddit"].get("per_subreddit", 25)))
    if sources_cfg.get("producthunt", {}).get("enabled"):
        all_items.extend(_run("ProductHunt", fetch_producthunt, max_items=sources_cfg["producthunt"].get("max_items", 20)))
    if sources_cfg.get("huggingface", {}).get("enabled"):
        all_items.extend(_run("HuggingFace", fetch_huggingface, max_items=sources_cfg["huggingface"].get("max_items", 20)))
    if sources_cfg.get("indie_games", {}).get("enabled"):
        all_items.extend(_run("itch.io", fetch_indie_games, max_items=sources_cfg["indie_games"].get("max_items", 20)))
    if sources_cfg.get("arxiv", {}).get("enabled"):
        all_items.extend(_run("arXiv", fetch_arxiv, max_items=sources_cfg["arxiv"].get("max_items", 20)))
    if sources_cfg.get("steam", {}).get("enabled"):
        all_items.extend(_run("Steam", fetch_steam, max_items=sources_cfg["steam"].get("max_items", 20)))

    print(f"[fetch] Total raw items: {len(all_items)}")
    return all_items


# ── Weekly Pool ────────────────────────────────────────────

def _week_key() -> str:
    """返回 ISO 周标识，如 '2026-W22'"""
    d = date.today()
    return d.strftime("%G-W%V")


def _load_pool() -> dict:
    """加载本周 pool"""
    if not POOL_FILE.exists():
        return {"week": _week_key(), "items": [], "daily_top5": {}}
    data = json.loads(POOL_FILE.read_text())
    if data.get("week") != _week_key():
        # 新的一周
        return {"week": _week_key(), "items": [], "daily_top5": {}}
    return data


def _save_pool(data: dict):
    POOL_FILE.parent.mkdir(parents=True, exist_ok=True)
    POOL_FILE.write_text(json.dumps(data, ensure_ascii=False))


def _load_seen_weekly() -> set[str]:
    if not SEEN_WEEKLY_FILE.exists():
        return set()
    data = json.loads(SEEN_WEEKLY_FILE.read_text())
    if data.get("week") != _week_key():
        return set()
    return set(data.get("urls", []))


def _save_seen_weekly(urls: set):
    SEEN_WEEKLY_FILE.parent.mkdir(parents=True, exist_ok=True)
    SEEN_WEEKLY_FILE.write_text(json.dumps({"week": _week_key(), "urls": list(urls)}, ensure_ascii=False))


def _curate_daily(items: list[dict]) -> list[dict]:
    """精选日报：每 L1 最多 5 项，每 L2 最多 1 项"""

    # 按 L1 分组
    l1_buckets = {}
    for it in items:
        l1 = _pick_l1(it)
        l1_buckets.setdefault(l1, []).append(it)

    curated = []
    for l1, pool in l1_buckets.items():
        # 按 L2 规则分组
        assigned = set()
        l2_groups = {}
        for rule_l1, l2_name, fn in L2_RULES:
            if rule_l1 != l1:
                continue
            matched = []
            for i, it in enumerate(pool):
                if i not in assigned and fn(it):
                    matched.append(it)
                    assigned.add(i)
            if matched:
                matched.sort(key=lambda x: x.get("relevance_score", 0), reverse=True)
                l2_groups[l2_name] = matched

        # 每个 L2 取 Top 1
        for l2_name, group in l2_groups.items():
            if group:
                curated.append(group[0])

        # 如果该 L1 精选数量不足 5，从剩余中补齐
        l1_picks = [c for c in curated if _pick_l1(c) == l1]
        if len(l1_picks) < 5:
            unassigned = [it for i, it in enumerate(pool) if i not in assigned]
            unassigned.sort(key=lambda x: x.get("relevance_score", 0), reverse=True)
            for it in unassigned:
                if len([c for c in curated if _pick_l1(c) == l1]) >= 5:
                    break
                curated.append(it)

    # 整体排重 + 按 relevance 排序
    seen = set()
    result = []
    for it in sorted(curated, key=lambda x: x.get("relevance_score", 0), reverse=True):
        if it["url"] not in seen:
            result.append(it)
            seen.add(it["url"])
    return result


# ── Daily (Mon-Sat) ─────────────────────────────────────────

def run_daily():
    print("=== AI Daily Light ===")
    today = date.today().isoformat()

    items = _fetch_all()

    # 周内去重
    seen = _load_seen_weekly()
    before = len(items)
    items = [it for it in items if it["url"] not in seen]
    print(f"[dedup] Removed {before - len(items)} seen-this-week, {len(items)} remaining")

    if not items:
        print("[daily] No new items today")
        return

    # 关键词预筛选
    keywords = get_keywords()
    filtered = pre_filter(items, keywords)
    print(f"[filter] After keyword filter: {len(filtered)}")

    if not filtered:
        print("[daily] Nothing matched keywords today")
        return

    # LLM 摘要
    summarized = summarize(filtered)
    print(f"[llm] Summarized: {len(summarized)}")

    # 更新周内已见
    for it in summarized:
        seen.add(it["url"])
    _save_seen_weekly(seen)

    # 推送：每 L1 各取 1 个 Top（游戏/AI/互联网/产品/科研）
    l1_order = ['游戏', 'AI', '互联网', '产品', '科研']
    top5 = []
    for l1 in l1_order:
        l1_items = [it for it in summarized if _pick_l1(it) == l1]
        l1_items.sort(key=lambda x: x.get("relevance_score", 0), reverse=True)
        if l1_items:
            top5.append(l1_items[0])
    print(f"[push] Selected {len(top5)} items (1 per category)")

    # 精选日报展示 (每 L1 最多 5 项，每 L2 最多 1 项)
    curated = _curate_daily(summarized)
    print(f"[curate] Daily highlights: {len(curated)} items")

    # 推送
    dashboard_url = get_env("DASHBOARD_URL", "https://cawezh.github.io/AIDailyReport/")
    send_feishu(top5, dashboard_url)
    send_wechat(top5, dashboard_url)

    # 存入本周 pool（完整数据）
    pool = _load_pool()
    existing_urls = {it["url"] for it in pool["items"]}
    for it in summarized:
        if it["url"] not in existing_urls:
            pool["items"].append(it)
    pool["daily_top5"][today] = [it["title"] for it in top5]
    _save_pool(pool)

    # 生成精选 Dashboard
    overview = generate_overview(curated)
    data_path = save_daily_data(curated, overview=overview)
    print(f"[dashboard] Saved curated data to {data_path}")
    update_manifest(curated, overview=overview)
    generate_index_html()
    print("[dashboard] Generated SPA index")

    print(f"[daily] Top 5 pushed, pool has {len(pool['items'])} items, dashboard shows {len(curated)} picks")
    print(f"=== Done: {today} ===")


# ── Weekly (Sunday) ────────────────────────────────────────

def run_weekly():
    print("=== AI Weekly Report ===")
    today = date.today()
    week = _week_key()
    cfg = get_sources()

    # 加载本周 pool
    pool = _load_pool()
    items = pool.get("items", [])

    # 如果今天还有新抓取的数据，也加入
    fresh = _fetch_all()
    seen = _load_seen_weekly()
    fresh = [it for it in fresh if it["url"] not in seen]
    if fresh:
        keywords = get_keywords()
        fresh = pre_filter(fresh, keywords)
        if fresh:
            fresh = summarize(fresh)
            existing = {it["url"] for it in items}
            for it in fresh:
                if it["url"] not in existing:
                    items.append(it)

    print(f"[weekly] Pool: {len(items)} items")

    if not items:
        print("[weekly] No items this week, nothing to report")
        return

    # 去重 + 按 relevance 排序
    seen_urls = set()
    unique = []
    for it in sorted(items, key=lambda x: x.get("relevance_score", 0), reverse=True):
        if it["url"] not in seen_urls:
            unique.append(it)
            seen_urls.add(it["url"])
    items = unique
    print(f"[weekly] Deduplicated: {len(items)} unique items")

    # 周报概览
    overview = generate_overview(items)
    print(f"[overview] {overview.get('overview', '')}")

    # 生成周报
    week_start = today - timedelta(days=today.weekday())
    week_end = today
    week_range = f"{week_start.strftime('%m.%d')} - {week_end.strftime('%m.%d')}"

    report_path = generate_report(items, output_dir=cfg["output"]["reports_dir"], overview=overview, week_label=week_range)
    print(f"[report] Saved to {report_path}")

    # Dashboard
    data_path = save_daily_data(items, overview=overview)
    print(f"[dashboard] Saved data to {data_path}")
    manifest_path = update_manifest(items, overview=overview)
    print(f"[dashboard] Updated manifest at {manifest_path}")
    generate_index_html()
    print("[dashboard] Generated SPA index")

    # 推送周报摘要：每 L1 各取 1 个 Top
    dashboard_url = get_env("DASHBOARD_URL", "https://cawezh.github.io/AIDailyReport/")
    l1_order = ['游戏', 'AI', '互联网', '产品', '科研']
    top5 = []
    for l1 in l1_order:
        l1_items = [it for it in items if _pick_l1(it) == l1]
        l1_items.sort(key=lambda x: x.get("relevance_score", 0), reverse=True)
        if l1_items:
            top5.append(l1_items[0])
    counts = {}
    for it in items:
        pc = it.get("primary_category", "other")
        counts[pc] = counts.get(pc, 0) + 1

    send_feishu_weekly(top5, dashboard_url, overview, week_range, len(items), counts)
    send_wechat_weekly(top5, dashboard_url, overview, week_range, len(items), counts)

    # 清空 pool
    _save_pool({"week": week, "items": [], "daily_top5": {}})
    _save_seen_weekly(set())

    print(f"=== Week {week} done ===")


# ── Entry ──────────────────────────────────────────────────

def main():
    today = date.today()
    # Sunday = 6
    if today.weekday() == 6:
        run_weekly()
    else:
        run_daily()


if __name__ == "__main__":
    sys.exit(main())
