#!/home/ubuntu/.openclaw/workspace/venv/bin/python3
"""
TickTick OAuth 设置脚本
首次运行需要手动授权
"""

import json
import os
import requests
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
import webbrowser

CREDENTIALS_FILE = os.path.expanduser("~/.openclaw/workspace/ticktick_creds.json")
TOKEN_FILE = os.path.expanduser("~/.openclaw/workspace/ticktick_token.json")

def load_credentials():
    """加载凭证"""
    with open(CREDENTIALS_FILE) as f:
        return json.load(f)

def save_token(token_data):
    """保存 token"""
    with open(TOKEN_FILE, 'w') as f:
        json.dump(token_data, f, indent=2)
    print(f"✅ Token 已保存到: {TOKEN_FILE}")

def get_authorization_code(creds):
    """获取授权码 - 需要用户手动授权"""
    auth_url = "https://ticktick.com/oauth/authorize"
    params = {
        "client_id": creds['client_id'],
        "response_type": "code",
        "scope": "tasks:read tasks:write",
        "redirect_uri": creds['redirect_uri']
    }
    
    # 构建完整 URL
    full_url = f"{auth_url}?client_id={params['client_id']}&response_type=code&scope={params['scope']}&redirect_uri={params['redirect_uri']}"
    
    print("\n" + "="*60)
    print("🔗 请访问以下 URL 进行授权：")
    print("="*60)
    print(full_url)
    print("="*60)
    print("\n授权后，浏览器会跳转到一个 URL，类似：")
    print(f"{creds['redirect_uri']}?code=XXXXXX")
    print("\n请复制 'code=' 后面的授权码")
    print("="*60 + "\n")
    
    # 等待用户输入授权码
    auth_code = input("请输入授权码 (code 参数的值): ").strip()
    return auth_code

def exchange_code_for_token(creds, auth_code):
    """用授权码换取 access token"""
    token_url = "https://ticktick.com/oauth/token"
    
    data = {
        "client_id": creds['client_id'],
        "client_secret": creds['client_secret'],
        "code": auth_code,
        "grant_type": "authorization_code",
        "redirect_uri": creds['redirect_uri'],
        "scope": "tasks:read tasks:write"
    }
    
    print("\n🔄 正在获取 Access Token...")
    
    response = requests.post(token_url, data=data)
    
    if response.status_code == 200:
        token_data = response.json()
        print("✅ 成功获取 Token!")
        return token_data
    else:
        print(f"❌ 获取 Token 失败: {response.status_code}")
        print(f"响应: {response.text}")
        return None

def refresh_token(creds, refresh_token_value):
    """刷新 access token"""
    token_url = "https://ticktick.com/oauth/token"
    
    data = {
        "client_id": creds['client_id'],
        "client_secret": creds['client_secret'],
        "refresh_token": refresh_token_value,
        "grant_type": "refresh_token"
    }
    
    response = requests.post(token_url, data=data)
    
    if response.status_code == 200:
        return response.json()
    else:
        print(f"❌ 刷新 Token 失败: {response.status_code}")
        return None

def main():
    print("\n🚀 TickTick OAuth 设置向导\n")
    
    # 加载凭证
    creds = load_credentials()
    print(f"📋 Client ID: {creds['client_id'][:10]}...")
    
    # 检查是否已有 token
    if os.path.exists(TOKEN_FILE):
        print("\n⚠️ 发现已有的 Token 文件")
        choice = input("是否重新授权? (y/n): ").strip().lower()
        if choice != 'y':
            print("保持现有 Token，退出。")
            return
    
    # 获取授权码
    auth_code = get_authorization_code(creds)
    
    if not auth_code:
        print("❌ 未获取到授权码")
        return
    
    # 换取 token
    token_data = exchange_code_for_token(creds, auth_code)
    
    if token_data:
        # 添加时间戳
        token_data['created_at'] = os.popen('date -Iseconds').read().strip()
        save_token(token_data)
        print("\n🎉 设置完成！现在可以运行 sync_tasks.py 了")
    else:
        print("\n❌ 设置失败，请检查凭证和网络连接")

if __name__ == "__main__":
    main()
