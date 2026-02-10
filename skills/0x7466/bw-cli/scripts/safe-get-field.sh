#!/usr/bin/env bash
# safe-get-field.sh - Safely retrieve a specific field from Bitwarden
# Usage: ./safe-get-field.sh <item-name-or-id> <field>
# Fields: password, username, totp, notes, uri

set -euo pipefail

ITEM="${1:-}"
FIELD="${2:-password}"

if [[ -z "$ITEM" ]]; then
    echo "Usage: $0 <item-name-or-id> [field]" >&2
    echo "Fields: password, username, totp, notes, uri" >&2
    exit 1
fi

# Check if we have a session
if [[ -z "${BW_SESSION:-}" ]]; then
    echo "Error: BW_SESSION not set. Run 'bw unlock' first." >&2
    exit 1
fi

# Map field to bw command
case "$FIELD" in
    password|username|totp|notes|uri)
        bw get "$FIELD" "$ITEM" --quiet 2>/dev/null || {
            echo "Error: Could not retrieve $FIELD for '$ITEM'" >&2
            exit 1
        }
        ;;
    *)
        echo "Error: Unknown field '$FIELD'" >&2
        exit 1
        ;;
esac
