"""飞书 Webhook 卡片消息推送"""
import json
import requests
from src.config import get_env


def send_feishu(top5: list[dict], dashboard_url: str, overview: dict = None) -> bool:
    """
    通过飞书 Webhook 发送日报卡片消息。
    top5: 前 5 个项目，每个含 title, url, cn_summary
    """
    webhook_url = get_env("FEISHU_WEBHOOK_URL")
    if not webhook_url:
        print("[feishu] FEISHU_WEBHOOK_URL not set, skipping")
        return False

    from datetime import date
    today = date.today().isoformat()
    overview = overview or {}

    elements = [
        {"tag": "div", "text": {"tag": "lark_md", "content": f"**AI 技术日报 — {today}**"}},
    ]

    # 今日概览
    overview_text = overview.get("overview", "")
    if overview_text:
        elements.append({
            "tag": "div",
            "text": {"tag": "lark_md", "content": f"📊 今日概览\n{overview_text}"},
        })

    elements.append({"tag": "hr"})

    for idx, item in enumerate(top5, 1):
        elements.append({
            "tag": "div",
            "text": {
                "tag": "lark_md",
                "content": f"{idx}. [{item['title']}]({item['url']}) — {item['cn_summary']}"
            }
        })

    elements.append({"tag": "hr"})
    elements.append({
        "tag": "div",
        "text": {"tag": "lark_md", "content": f"[查看完整日报]({dashboard_url})"}
    })

    payload = {
        "msg_type": "interactive",
        "card": {
            "header": {
                "title": {"tag": "plain_text", "content": f"AI 技术日报 — {today}"},
                "template": "blue",
            },
            "elements": elements,
        },
    }

    try:
        resp = requests.post(webhook_url, json=payload, timeout=15)
        resp.raise_for_status()
        print("[feishu] sent successfully")
        return True
    except requests.RequestException as e:
        print(f"[feishu] send failed: {e}")
        return False


def send_feishu_weekly(top5: list[dict], dashboard_url: str, overview: dict, week_range: str, total: int, counts: dict):
    """发送周报摘要卡片"""
    webhook_url = get_env("FEISHU_WEBHOOK_URL")
    if not webhook_url:
        print("[feishu] FEISHU_WEBHOOK_URL not set, skipping")
        return False

    overview_text = overview.get("overview", "")

    cat_parts = []
    for cat, n in sorted(counts.items(), key=lambda x: -x[1]):
        cat_parts.append(f"{cat} {n}")
    cat_line = " · ".join(cat_parts[:5])

    elements = [
        {"tag": "div", "text": {"tag": "lark_md", "content": f"**📊 AI 周报 | {week_range}**"}},
        {"tag": "div", "text": {"tag": "lark_md", "content": f"本周热点：{overview_text[:80]}"}},
        {"tag": "div", "text": {"tag": "lark_md", "content": f"收录 **{total}** 项 | {cat_line}"}},
        {"tag": "hr"},
    ]

    for idx, item in enumerate(top5, 1):
        score = item.get("innovation_score", 0)
        star = "🔥" if score >= 8 else "⭐" if score >= 7 else ""
        elements.append({
            "tag": "div",
            "text": {"tag": "lark_md", "content": f"{idx}. [{item['title']}]({item['url']}) — {item['cn_summary']} {star}"}
        })

    elements.append({"tag": "hr"})
    elements.append({
        "tag": "div",
        "text": {"tag": "lark_md", "content": f"[查看完整周报]({dashboard_url})"}
    })

    payload = {
        "msg_type": "interactive",
        "card": {
            "header": {
                "title": {"tag": "plain_text", "content": f"AI 周报 — {week_range}"},
                "template": "blue",
            },
            "elements": elements,
        },
    }

    try:
        resp = requests.post(webhook_url, json=payload, timeout=15)
        resp.raise_for_status()
        print("[feishu] weekly sent successfully")
        return True
    except requests.RequestException as e:
        print(f"[feishu] weekly send failed: {e}")
        return False
