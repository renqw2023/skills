#!/usr/bin/env bash
# create-login-item.sh - Interactive helper to create login items
# Usage: ./create-login-item.sh

set -euo pipefail

echo "=== Create Bitwarden Login Item ==="

read -rp "Item name: " name
read -rp "Username: " username
read -rsp "Password (leave empty to generate): " password_input
echo ""

if [[ -z "$password_input" ]]; then
    read -rp "Password length [16]: " length
    length=${length:-16}
    password=$(bw generate --length "$length" --uppercase --lowercase --numbers)
    echo "Generated password: $password"
fi

read -rp "URI (optional): " uri
read -rp "Notes (optional): " notes

# Build JSON
json=$(bw get template item | jq \
    --arg name "$name" \
    --arg username "$username" \
    --arg password "${password:-$password_input}" \
    --arg uri "$uri" \
    --arg notes "$notes" \
    '.name = $name | .login.username = $username | .login.password = $password | .notes = $notes | if $uri != "" then .login.uris = [{"uri": $uri, "match": null}] else . end')

# Confirm
echo ""
echo "Creating item:"
echo "$json" | jq '{name, username: .login.username, password: .login.password, notes}'

read -rp "Confirm creation? [y/N]: " confirm

if [[ "$confirm" != "y" && "$confirm" != "Y" ]]; then
    echo "Cancelled."
    exit 0
fi

# Create
result=$(echo "$json" | bw encode | bw create item)
echo "Created item with ID: $(echo "$result" | jq -r '.id')"
