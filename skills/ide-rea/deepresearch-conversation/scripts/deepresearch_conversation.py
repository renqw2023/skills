import os
import sys
import requests
import json
import argparse


def ppt_outline_generate(api_key: str, parse_data:dict):
    url = "https://qianfan.baidubce.com/v2/agent/deepresearch/run"
    headers = {
        "Authorization": "Bearer %s" % api_key,
        "X-Appbuilder-From": "openclaw",
        "Content-Type": "application/json"
    }
    headers.setdefault('Accept', 'text/event-stream')
    headers.setdefault('Cache-Control', 'no-cache')
    headers.setdefault('Connection', 'keep-alive')

    with requests.post(url, headers=headers, json=parse_data, stream=True) as response:
        response.raise_for_status()
        for line in response.iter_lines():
            line = line.decode('utf-8')
            if line and line.startswith("data:"):
                data_str = line[5:].strip()
                yield json.loads(data_str)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python deepresearch_conversation.py <requestBody>")
        sys.exit(1)

    requestBody = sys.argv[1]
    parse_data = {}
    try:
        parse_data = json.loads(requestBody)
        print(f"success parse request body: {parse_data}")
    except json.JSONDecodeError as e:
        print(f"JSON parse error: {e}")

    if "query" not in parse_data:
        print("Error: query must be present in request body.")
        sys.exit(1)

    api_key = os.getenv("BAIDU_API_KEY")
    if not api_key:
        print("Error: BAIDU_API_KEY must be set in environment.")
        sys.exit(1)
    try:
        results = ppt_outline_generate(api_key, parse_data)
        for result in results:
            print(json.dumps(result, ensure_ascii=False, indent=2))
    except Exception as e:
        print(f"Error: {str(e)}")
        sys.exit(1)
