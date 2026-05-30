"""跨天去重 — 记录已见过的 URL，避免重复推送"""
import json
from datetime import date, timedelta
from pathlib import Path

SEEN_FILE = Path(__file__).resolve().parent.parent / "reports" / "seen_items.json"
KEEP_DAYS = 30  # 保留最近 30 天的记录


def load_seen() -> set[str]:
    """加载已见过的 URL 集合"""
    if not SEEN_FILE.exists():
        return set()
    try:
        data = json.loads(SEEN_FILE.read_text())
        return set(data.get("urls", []))
    except (json.JSONDecodeError, KeyError):
        return set()


def save_seen(items: list[dict]):
    """追加新 items 的 URL，清理过期记录"""
    today = date.today().isoformat()
    cutoff = date.today() - timedelta(days=KEEP_DAYS)

    seen = {}
    if SEEN_FILE.exists():
        try:
            data = json.loads(SEEN_FILE.read_text())
            seen = data.get("records", {})
        except (json.JSONDecodeError, KeyError):
            seen = {}

    # 追加新 URL
    for item in items:
        url = item.get("url", "")
        if url:
            seen[url] = today

    # 清理过期记录
    seen = {url: d for url, d in seen.items() if d >= cutoff.isoformat()}

    SEEN_FILE.parent.mkdir(parents=True, exist_ok=True)
    SEEN_FILE.write_text(json.dumps({
        "urls": list(seen.keys()),
        "records": seen,
    }, ensure_ascii=False, indent=2))
