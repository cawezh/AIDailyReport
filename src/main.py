"""主流程 — 编排全部步骤"""
import sys
import json
from datetime import date
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
)
from src.filter import pre_filter
from src.dedup import load_seen, save_seen
from src.llm import summarize
from src.reporter import generate_report
from src.dashboard import generate_dashboard
from src.feishu import send_feishu
from src.wechat import send_wechat

CACHE_FILE = Path(__file__).resolve().parent.parent / "reports" / "daily_cache.json"


def _load_cache() -> list[dict]:
    """加载当天已缓存的 items"""
    if not CACHE_FILE.exists():
        return []
    try:
        data = json.loads(CACHE_FILE.read_text())
        today = date.today().isoformat()
        if data.get("date") == today:
            return data.get("items", [])
    except (json.JSONDecodeError, KeyError):
        pass
    return []


def _save_cache(items: list[dict]):
    """保存当天所有 items 到缓存"""
    CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
    json.dump({"date": date.today().isoformat(), "items": items}, CACHE_FILE.open("w"), ensure_ascii=False)


def main():
    print("=== AI Daily Report ===")
    cfg = get_sources()
    sources_cfg = cfg["sources"]
    report_cfg = cfg["report"]

    # ---- Fetch ----
    all_items = []

    if sources_cfg.get("github_trending", {}).get("enabled"):
        print("[fetch] GitHub Trending...")
        try:
            all_items.extend(fetch_github_trending(max_items=sources_cfg["github_trending"].get("max_items", 25)))
        except Exception as e:
            print(f"[fetch] GitHub Trending failed: {e}")

    if sources_cfg.get("github_search", {}).get("enabled"):
        print("[fetch] GitHub Search...")
        try:
            all_items.extend(fetch_github_search(
                queries=sources_cfg["github_search"].get("queries", []),
                per_query=sources_cfg["github_search"].get("per_query", 10),
            ))
        except Exception as e:
            print(f"[fetch] GitHub Search failed: {e}")

    if sources_cfg.get("hackernews", {}).get("enabled"):
        print("[fetch] Hacker News...")
        try:
            all_items.extend(fetch_hackernews(max_items=sources_cfg["hackernews"].get("max_items", 100)))
        except Exception as e:
            print(f"[fetch] Hacker News failed: {e}")

    if sources_cfg.get("reddit", {}).get("enabled"):
        print("[fetch] Reddit...")
        try:
            all_items.extend(fetch_reddit(
                subreddits=sources_cfg["reddit"].get("subreddits", []),
                per_subreddit=sources_cfg["reddit"].get("per_subreddit", 25),
            ))
        except Exception as e:
            print(f"[fetch] Reddit failed: {e}")

    if sources_cfg.get("producthunt", {}).get("enabled"):
        print("[fetch] ProductHunt...")
        try:
            all_items.extend(fetch_producthunt(max_items=sources_cfg["producthunt"].get("max_items", 30)))
        except Exception as e:
            print(f"[fetch] ProductHunt failed: {e}")

    if sources_cfg.get("huggingface", {}).get("enabled"):
        print("[fetch] HuggingFace...")
        try:
            all_items.extend(fetch_huggingface(max_items=sources_cfg["huggingface"].get("max_items", 20)))
        except Exception as e:
            print(f"[fetch] HuggingFace failed: {e}")

    if sources_cfg.get("indie_games", {}).get("enabled"):
        print("[fetch] itch.io...")
        try:
            all_items.extend(fetch_indie_games(max_items=sources_cfg["indie_games"].get("max_items", 20)))
        except Exception as e:
            print(f"[fetch] itch.io failed: {e}")

    print(f"[fetch] Total raw items: {len(all_items)}")

    # ---- Dedup (避免重复处理已见过的数据) ----
    seen_urls = load_seen()
    before = len(all_items)
    all_items = [it for it in all_items if it["url"] not in seen_urls]
    print(f"[dedup] Removed {before - len(all_items)} already-seen items, {len(all_items)} remaining")

    if not all_items:
        print("[dedup] No new items, using cached data")
        cached = _load_cache()
        if cached:
            _gen_dashboard_and_notify(cached, cfg, report_cfg)
        return

    # ---- Filter ----
    keywords = get_keywords()
    filtered = pre_filter(all_items, keywords)
    print(f"[filter] After keyword filter: {len(filtered)}")

    if not filtered:
        print("[llm] No new items to summarize, using cached data")
        cached = _load_cache()
        if cached:
            _gen_dashboard_and_notify(cached, cfg, report_cfg)
        return

    # ---- LLM Summarize ----
    summarized = summarize(filtered)
    print(f"[llm] Summarized: {len(summarized)}")

    # ---- Save seen + Merge with cache ----
    save_seen(summarized)
    cached = _load_cache()
    seen_urls = {it["url"] for it in cached}
    merged = cached + [it for it in summarized if it["url"] not in seen_urls]
    _save_cache(merged)
    print(f"[cache] Merged: {len(cached)} cached + {len(summarized)} new = {len(merged)} total")

    # ---- Generate & Notify (with merged/all data) ----
    _gen_dashboard_and_notify(merged, cfg, report_cfg)


def _gen_dashboard_and_notify(items: list[dict], cfg: dict, report_cfg: dict):
    """用完整 items 生成 dashboard 和推送"""

    # ---- Generate ----
    report_path = generate_report(items, output_dir=cfg["output"]["reports_dir"])
    print(f"[report] Saved to {report_path}")

    dashboard_path = generate_dashboard(items, output_dir=cfg["output"]["docs_dir"])
    print(f"[dashboard] Saved to {dashboard_path}")

    # ---- Notify ----
    top_n = report_cfg.get("top_n", 10)
    top_items = sorted(items, key=lambda x: x.get("relevance_score", 0), reverse=True)[:top_n]
    dashboard_url = get_env("DASHBOARD_URL", "https://<user>.github.io/ai-daily-report/")

    send_feishu(top_items[:5], dashboard_url)
    send_wechat(top_items[:5], dashboard_url)

    print(f"=== Done: {date.today().isoformat()} ===")


if __name__ == "__main__":
    sys.exit(main())
