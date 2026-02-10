#!/usr/bin/env bash
# unlock-session.sh - Safely unlock Bitwarden vault and export session
# Usage: source unlock-session.sh [password-file]
# Or: ./unlock-session.sh --env BW_PASSWORD

set -euo pipefail

SECRETS_DIR="${HOME}/.openclaw/workspace/.secrets"
PASSWORD_SOURCE=""

# Parse arguments
if [[ "${1:-}" == "--env" && -n "${2:-}" ]]; then
    # Use environment variable
    PASSWORD_SOURCE="env:$2"
elif [[ -n "${1:-}" ]]; then
    # Use password file
    PASSWORD_SOURCE="file:$1"
elif [[ -f "${SECRETS_DIR}/bw-password.txt" ]]; then
    # Default to workspace secrets
    PASSWORD_SOURCE="file:${SECRETS_DIR}/bw-password.txt"
fi

# Attempt unlock
echo "Unlocking Bitwarden vault..." >&2

if [[ "$PASSWORD_SOURCE" == env:* ]]; then
    ENV_VAR="${PASSWORD_SOURCE#env:}"
    if [[ -z "${!ENV_VAR:-}" ]]; then
        echo "Error: Environment variable $ENV_VAR is not set" >&2
        exit 1
    fi
    # Unlock with environment variable
    SESSION_OUTPUT=$(bw unlock --passwordenv "$ENV_VAR" --raw 2>&1) || {
        echo "Error: Failed to unlock vault" >&2
        echo "$SESSION_OUTPUT" >&2
        exit 1
    }
elif [[ "$PASSWORD_SOURCE" == file:* ]]; then
    PASSFILE="${PASSWORD_SOURCE#file:}"
    if [[ ! -f "$PASSFILE" ]]; then
        echo "Error: Password file not found: $PASSFILE" >&2
        exit 1
    fi
    # Check permissions (should be 600)
    PERMS=$(stat -c %a "$PASSFILE" 2>/dev/null || stat -f %Lp "$PASSFILE" 2>/dev/null)
    if [[ "$PERMS" != "600" ]]; then
        echo "Warning: Password file permissions are $PERMS (should be 600)" >&2
        chmod 600 "$PASSFILE"
    fi
    # Unlock with password file
    SESSION_OUTPUT=$(bw unlock --passwordfile "$PASSFILE" --raw 2>&1) || {
        echo "Error: Failed to unlock vault" >&2
        echo "$SESSION_OUTPUT" >&2
        exit 1
    }
else
    # Interactive unlock
    SESSION_OUTPUT=$(bw unlock --raw 2>&1) || {
        echo "Error: Failed to unlock vault" >&2
        echo "$SESSION_OUTPUT" >&2
        exit 1
    }
fi

# Export session (output for eval)
echo "export BW_SESSION=\"${SESSION_OUTPUT}\""
echo "# Run this command to activate:" >&2
echo "# eval \"\$(./unlock-session.sh)\"" >&2
