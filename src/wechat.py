"""微信个人号 iLink Bot API 推送"""
import json
import random
import base64
from datetime import date
import requests
from pathlib import Path
from src.config import get_env

ILINK_BASE = "https://ilinkai.weixin.qq.com"
STATE_FILE = Path(__file__).resolve().parent.parent / ".wechat_state.json"


def _make_headers(token: str) -> dict:
    """生成 iLink API 请求头，每次请求 X-WECHAT-UIN 随机防重放"""
    rand_uin = base64.b64encode(str(random.randint(0, 2**32 - 1)).encode()).decode()
    return {
        "Content-Type": "application/json",
        "AuthorizationType": "ilink_bot_token",
        "Authorization": f"Bearer {token}",
        "X-WECHAT-UIN": rand_uin,
    }


def _load_state() -> dict:
    """加载本地状态：最近对话用户的 context_token"""
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text())
    return {"users": {}}  # {"user_id": {"context_token": "...", "timestamp": 0}}


def _save_state(state: dict):
    STATE_FILE.write_text(json.dumps(state, ensure_ascii=False))


def _fetch_recent_contexts(token: str) -> dict[str, str]:
    """
    调用 getupdates 获取最近消息，抽取每个用户的 context_token。
    返回: {"user_id": "context_token", ...}
    """
    state = _load_state()
    fresh = {}

    try:
        get_updates_buf = ""
        for _ in range(5):  # 最多拉 5 页
            resp = requests.post(
                f"{ILINK_BASE}/ilink/bot/getupdates",
                json={"get_updates_buf": get_updates_buf},
                headers=_make_headers(token),
                timeout=30,
            )
            resp.raise_for_status()
            data = resp.json()
            get_updates_buf = data.get("get_updates_buf", get_updates_buf)

            for msg in data.get("msgs", []):
                uid = msg.get("from_user_id", "")
                if uid:
                    fresh[uid] = msg.get("context_token", "")

            if not data.get("msgs"):
                break
    except requests.RequestException as e:
        print(f"[wechat] getupdates error: {e}")

    # 合并：用新数据更新旧状态
    for uid, ctx in fresh.items():
        state["users"][uid] = {
            "context_token": ctx,
            "timestamp": state.get("users", {}).get(uid, {}).get("timestamp", 0) or 0,
        }

    _save_state(state)
    return {uid: info["context_token"] for uid, info in state["users"].items() if info["context_token"]}


def send_wechat(top5: list[dict], dashboard_url: str) -> bool:
    """
    通过 iLink Bot API 向最近对话过的用户推送日报。
    仅能回复 24h 内有过互动的用户。
    """
    bot_token = get_env("WECHAT_BOT_TOKEN")
    client_id = get_env("WECHAT_CLIENT_ID")

    if not bot_token:
        print("[wechat] WECHAT_BOT_TOKEN not set, skipping")
        return False

    if not client_id:
        # 尝试从 getupdates 中提取 client_id
        print("[wechat] WECHAT_CLIENT_ID not set, skipping (set to your bot ID, e.g. xxx@im.bot)")
        return False

    # 获取最近有对话的用户
    user_contexts = _fetch_recent_contexts(bot_token)
    if not user_contexts:
        print("[wechat] no recent users to push to")
        return False

    # 组装日报摘要
    lines = [f"AI 技术日报 ({date.today().isoformat()})", ""]
    for i, item in enumerate(top5, 1):
        title = item["title"]
        summary = item.get("cn_summary", "")[:50]
        lines.append(f"{i}. {title}")
        lines.append(f"   {summary}")
        lines.append("")
    lines.append(f"查看完整日报: {dashboard_url}")
    full_text = "\n".join(lines).strip()

    sent = 0
    for user_id, context_token in user_contexts.items():
        try:
            payload = {
                "msg": {
                    "to_user_id": user_id,
                    "client_id": client_id,
                    "message_type": 2,       # BOT
                    "message_state": 2,      # FINISH
                    "context_token": context_token,
                    "item_list": [
                        {
                            "type": 1,       # TEXT
                            "text_item": {"text": full_text},
                        }
                    ],
                }
            }
            resp = requests.post(
                f"{ILINK_BASE}/ilink/bot/sendmessage",
                json=payload,
                headers=_make_headers(bot_token),
                timeout=15,
            )
            data = resp.json()
            if data.get("errcode", 0) == 0:
                sent += 1
            else:
                print(f"[wechat] send to {user_id} failed: {data}")
        except requests.RequestException as e:
            print(f"[wechat] send error for {user_id}: {e}")

    print(f"[wechat] sent to {sent} users")
    return sent > 0
