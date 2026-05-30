#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
获取微信 iLink Bot Token

用法:
  python3 scripts/get_wechat_token.py

流程:
  1. 从 iLink API 获取二维码链接
  2. 在浏览器中打开二维码页面
  3. 轮询等待扫码确认
  4. 输出 bot_token
"""
import sys
import time
import webbrowser

import requests

BASE = "https://ilinkai.weixin.qq.com"


def main():
    print("=== 获取微信 iLink Bot Token ===")

    # Step 1: 获取二维码
    print("\n[1/3] 请求二维码...")
    try:
        r = requests.get(f"{BASE}/ilink/bot/get_bot_qrcode?bot_type=3", timeout=15)
        r.raise_for_status()
        data = r.json()
    except requests.RequestException as e:
        print(f"  请求失败: {e}")
        sys.exit(1)

    if data.get("ret") != 0:
        print(f"  API 返回错误: {data}")
        sys.exit(1)

    qrcode = data.get("qrcode")
    qrcode_url = data.get("qrcode_img_content")

    if not qrcode or not qrcode_url:
        print(f"  响应缺少必要字段: {data}")
        sys.exit(1)

    # Step 2: 在浏览器中打开二维码
    print(f"\n[2/3] 正在打开二维码页面...")
    print(f"  URL: {qrcode_url}")
    webbrowser.open(qrcode_url)
    print(f"  请在浏览器中查看二维码，用微信扫描")

    # Step 3: 轮询等待扫码
    print(f"\n[3/3] 等待微信扫码确认...")
    print(f"  (请在 60 秒内用微信扫描二维码)\n")

    for i in range(30):
        try:
            r = requests.get(
                f"{BASE}/ilink/bot/get_qrcode_status?qrcode={qrcode}",
                timeout=10,
            )
            status = r.json()
            if status.get("status") == "confirmed":
                bot_token = status.get("bot_token")
                print(f"\n=== 扫码成功！ ===")
                print(f"\nbot_token: {bot_token}")
                print(f"\n设置环境变量:")
                print(f"  export WECHAT_BOT_TOKEN=\"{bot_token}\"")
                print(f"\n设置为 GitHub Secret:")
                print(f"  gh secret set WECHAT_BOT_TOKEN --body \"{bot_token}\"")
                return
            elif status.get("status") == "expired":
                print("\n二维码已过期，请重新运行")
                sys.exit(1)
        except requests.RequestException as e:
            print(f"  轮询出错: {e}")

        print(".", end="", flush=True)
        time.sleep(2)

    print("\n\n等待超时，请重新运行脚本")
    sys.exit(1)


if __name__ == "__main__":
    main()
