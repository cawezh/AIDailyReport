"""微信公众号模板消息推送"""
import requests
from src.config import get_env

WECHAT_TOKEN_URL = "https://api.weixin.qq.com/cgi-bin/token"
WECHAT_SEND_URL = "https://api.weixin.qq.com/cgi-bin/message/template/send"


def send_wechat(top5: list[dict], dashboard_url: str) -> bool:
    """
    通过公众号模板消息推送日报。
    top5: 取前 5 个项目生成摘要文本
    """
    appid = get_env("WECHAT_APPID")
    secret = get_env("WECHAT_APPSECRET")
    template_id = get_env("WECHAT_TEMPLATE_ID")

    if not all([appid, secret, template_id]):
        print("[wechat] credentials not fully set, skipping")
        return False

    # 1. 获取 access_token
    try:
        resp = requests.get(WECHAT_TOKEN_URL, params={
            "grant_type": "client_credential",
            "appid": appid,
            "secret": secret,
        }, timeout=15)
        resp.raise_for_status()
        access_token = resp.json().get("access_token")
        if not access_token:
            print(f"[wechat] get token failed: {resp.text}")
            return False
    except requests.RequestException as e:
        print(f"[wechat] get token error: {e}")
        return False

    # 2. 获取粉丝列表（发送给所有关注者）
    sent = 0
    try:
        next_openid = ""
        while True:
            user_resp = requests.get(
                "https://api.weixin.qq.com/cgi-bin/user/get",
                params={
                    "access_token": access_token,
                    "next_openid": next_openid,
                },
                timeout=15,
            )
            user_resp.raise_for_status()
            user_data = user_resp.json()
            openids = user_data.get("data", {}).get("openid", [])

            for openid in openids:
                summary = "\n".join(
                    f"{i+1}. {item['title']} — {item['cn_summary'][:30]}"
                    for i, item in enumerate(top5)
                )
                payload = {
                    "touser": openid,
                    "template_id": template_id,
                    "url": dashboard_url,
                    "data": {
                        "first": {"value": "AI 技术日报已更新", "color": "#173177"},
                        "keyword1": {"value": str(len(top5)), "color": "#173177"},
                        "keyword2": {"value": summary, "color": "#173177"},
                        "remark": {"value": "点击查看完整日报", "color": "#173177"},
                    },
                }
                r = requests.post(
                    WECHAT_SEND_URL,
                    params={"access_token": access_token},
                    json=payload,
                    timeout=10,
                )
                if r.json().get("errmsg") == "ok":
                    sent += 1

            total = user_data.get("total", 0)
            count = user_data.get("count", 0)
            if count < 10000:
                break
            next_openid = user_data.get("next_openid", "")

        print(f"[wechat] sent to {sent} users")
        return sent > 0
    except requests.RequestException as e:
        print(f"[wechat] send error: {e}")
        return False
