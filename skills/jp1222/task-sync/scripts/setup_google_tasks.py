#!/usr/bin/env python3
"""
重新授权 Google Tasks 权限 (手动授权模式)
"""

import os
from google_auth_oauthlib.flow import InstalledAppFlow
from google.oauth2.credentials import Credentials
import json

# 最小权限：仅 Google Tasks 读写
SCOPES = [
    'https://www.googleapis.com/auth/tasks'
]

CREDENTIALS_FILE = os.path.expanduser("~/.openclaw/google-workspace/credentials.json")
TOKEN_FILE = os.path.expanduser("~/.openclaw/google-workspace/token.json")

def main():
    print("\n🔑 重新授权 Google Tasks 权限\n")

    if not os.path.exists(CREDENTIALS_FILE):
        print(f"❌ 未找到凭证文件: {CREDENTIALS_FILE}")
        return

    # 删除旧 token
    if os.path.exists(TOKEN_FILE):
        print("🗑️ 删除旧的 Token...")
        os.remove(TOKEN_FILE)

    # 创建 flow
    flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_FILE, SCOPES)

    # 获取授权 URL
    auth_url, _ = flow.authorization_url(prompt='consent')

    print("="*60)
    print("🔗 请访问以下 URL 进行授权：")
    print("="*60)
    print(auth_url)
    print("="*60)
    print("\n授权后，页面会显示一个授权码")
    print("请复制那个授权码\n")

    # 等待用户输入授权码
    code = input("请输入授权码: ").strip()

    # 用授权码换取 token
    flow.fetch_token(code=code)
    creds = flow.credentials

    # 保存新 token
    token_data = {
        "token": creds.token,
        "refresh_token": creds.refresh_token,
        "token_uri": creds.token_uri,
        "client_id": creds.client_id,
        "client_secret": creds.client_secret,
        "scopes": creds.scopes,
        "expiry": creds.expiry.isoformat() if creds.expiry else None
    }

    with open(TOKEN_FILE, 'w') as f:
        json.dump(token_data, f, indent=2)

    print(f"\n✅ 授权成功！Token 已保存到: {TOKEN_FILE}")

if __name__ == "__main__":
    main()
