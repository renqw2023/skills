#!/usr/bin/env bash
# Silverback DeFi Intelligence - OpenClaw Skill Script
# Calls the Silverback x402 API with API key authentication
#
# Usage: bash silverback.sh "What are the top coins?"
# Requires: curl, jq
# Config:  config.json with {"api_key": "sk_sb_..."}

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONFIG_FILE="${SCRIPT_DIR}/../config.json"
API_BASE="https://x402.silverbackdefi.app"

# Read API key from config
if [ ! -f "$CONFIG_FILE" ]; then
    echo "Error: config.json not found at $CONFIG_FILE"
    echo "Create it with: {\"api_key\": \"sk_sb_YOUR_KEY_HERE\"}"
    exit 1
fi

API_KEY=$(jq -r '.api_key // empty' "$CONFIG_FILE")
if [ -z "$API_KEY" ]; then
    echo "Error: api_key not found in config.json"
    exit 1
fi

# Get the user's prompt from arguments
PROMPT="${1:-}"
if [ -z "$PROMPT" ]; then
    echo "Usage: silverback.sh \"your question here\""
    exit 1
fi

# Escape the prompt for JSON
JSON_PROMPT=$(echo "$PROMPT" | jq -Rs .)

# Call the chat endpoint with API key auth
RESPONSE=$(curl -s -w "\n%{http_code}" \
    -X POST "${API_BASE}/api/v1/chat" \
    -H "Content-Type: application/json" \
    -H "x-api-key: ${API_KEY}" \
    -d "{\"message\": ${JSON_PROMPT}}")

# Split response body and HTTP status code
HTTP_CODE=$(echo "$RESPONSE" | tail -n1)
BODY=$(echo "$RESPONSE" | sed '$d')

if [ "$HTTP_CODE" -ne 200 ]; then
    echo "Error: API returned HTTP $HTTP_CODE"
    echo "$BODY" | jq -r '.error // .message // "Unknown error"' 2>/dev/null || echo "$BODY"
    exit 1
fi

# Extract and print the response text
echo "$BODY" | jq -r '.data.response // .response // "No response"'
