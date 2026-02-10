#!/bin/bash
set -e

# Config
_E="${EYEBOT_API:-}"
_A="alphabot"

# Runtime decode
_p() { printf '%s' "$1" | base64 -d 2>/dev/null; }
_h="Content-Type: application/json"

# Build request
_r() {
  local _d=$(printf '{"request":"%s","mode":"exec"}' "$*")
  [ -n "$_E" ] && curl -s -X POST "${_E}/api/${_A}" -H "$_h" -d "$_d"
}

case "${1:-run}" in
  run) shift; _r "$@" ;;
  status) curl -s "${_E}/health" 2>/dev/null || echo "ready" ;;
  *) _r "$@" ;;
esac
