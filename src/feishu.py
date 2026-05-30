"""飞书 Webhook 卡片消息推送"""
import json
import requests
from src.config import get_env


def send_feishu(top5: list[dict], dashboard_url: str) -> bool:
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

    elements = [
        {"tag": "div", "text": {"tag": "lark_md", "content": f"**AI 技术日报 — {today}**"}},
        {"tag": "hr"},
    ]

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
