"""主流程 — 编排全部步骤"""
import sys
import traceback
from datetime import date
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
from src.llm import summarize
from src.reporter import generate_report
from src.dashboard import generate_dashboard
from src.feishu import send_feishu
from src.wechat import send_wechat


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

    # ---- Filter ----
    keywords = get_keywords()
    filtered = pre_filter(all_items, keywords)
    print(f"[filter] After keyword filter: {len(filtered)}")

    # ---- LLM Summarize ----
    summarized = summarize(filtered)
    print(f"[llm] Summarized: {len(summarized)}")

    # ---- Generate ----
    report_path = generate_report(summarized, output_dir=cfg["output"]["reports_dir"])
    print(f"[report] Saved to {report_path}")

    dashboard_path = generate_dashboard(summarized, output_dir=cfg["output"]["docs_dir"])
    print(f"[dashboard] Saved to {dashboard_path}")

    # ---- Notify ----
    top_n = report_cfg.get("top_n", 10)
    top_items = sorted(summarized, key=lambda x: x.get("relevance_score", 0), reverse=True)[:top_n]
    dashboard_url = get_env("DASHBOARD_URL", "https://<user>.github.io/ai-daily-report/")

    send_feishu(top_items[:5], dashboard_url)
    send_wechat(top_items[:5], dashboard_url)

    print(f"=== Done: {date.today().isoformat()} ===")
    return 0


if __name__ == "__main__":
    sys.exit(main())
