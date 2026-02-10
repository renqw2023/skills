#!/bin/bash
#
# RelayPlane Skill Test Suite
# Tests all skill commands and validates output
#

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SKILL_DIR="$(dirname "$SCRIPT_DIR")"
SKILL_SCRIPT="$SKILL_DIR/relayplane.js"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
CYAN='\033[0;36m'
NC='\033[0m'

PASSED=0
FAILED=0
SKIPPED=0

pass() {
  echo -e "${GREEN}✓${NC} $1"
  ((++PASSED))
}

fail() {
  echo -e "${RED}✗${NC} $1"
  echo "  $2"
  ((++FAILED))
}

skip() {
  echo -e "${CYAN}○${NC} $1 (skipped: $2)"
  ((++SKIPPED))
}

echo "RelayPlane Skill Tests"
echo "======================"
echo ""

# ------------------------------------------------------------------------------
# T001: Skill script exists
# ------------------------------------------------------------------------------
if [[ -f "$SKILL_SCRIPT" ]]; then
  pass "T001: Skill script exists"
else
  fail "T001: Skill script exists" "File not found: $SKILL_SCRIPT"
  exit 1
fi

# ------------------------------------------------------------------------------
# T002: Help output (no args)
# ------------------------------------------------------------------------------
OUTPUT=$(node "$SKILL_SCRIPT" 2>&1)
if [[ "$OUTPUT" == *"stats"* && "$OUTPUT" == *"status"* && "$OUTPUT" == *"dashboard"* ]]; then
  pass "T002: Help output shows available commands"
else
  fail "T002: Help output shows available commands" "Missing expected commands in output"
fi

# ------------------------------------------------------------------------------
# T003: Stats command
# ------------------------------------------------------------------------------
OUTPUT=$(node "$SKILL_SCRIPT" stats 2>&1)
if [[ "$OUTPUT" == *"Statistics"* || "$OUTPUT" == *"Usage"* || "$OUTPUT" == *"requests"* ]]; then
  pass "T003: Stats command returns statistics"
else
  fail "T003: Stats command returns statistics" "Output: ${OUTPUT:0:100}"
fi

# ------------------------------------------------------------------------------
# T004: Status command
# ------------------------------------------------------------------------------
OUTPUT=$(node "$SKILL_SCRIPT" status 2>&1)
if [[ "$OUTPUT" == *"Config"* || "$OUTPUT" == *"Status"* || "$OUTPUT" == *"Telemetry"* ]]; then
  pass "T004: Status command returns configuration"
else
  fail "T004: Status command returns configuration" "Output: ${OUTPUT:0:100}"
fi

# ------------------------------------------------------------------------------
# T005: Dashboard command
# ------------------------------------------------------------------------------
OUTPUT=$(node "$SKILL_SCRIPT" dashboard 2>&1)
if [[ "$OUTPUT" == *"relayplane.com"* && "$OUTPUT" == *"dashboard"* ]]; then
  pass "T005: Dashboard command shows URL"
else
  fail "T005: Dashboard command shows URL" "Output: ${OUTPUT:0:100}"
fi

# ------------------------------------------------------------------------------
# T006: Models command
# ------------------------------------------------------------------------------
OUTPUT=$(node "$SKILL_SCRIPT" models 2>&1)
if [[ "$OUTPUT" == *"auto"* && "$OUTPUT" == *"cost"* && "$OUTPUT" == *"quality"* ]]; then
  pass "T006: Models command lists routing modes"
else
  fail "T006: Models command lists routing modes" "Output: ${OUTPUT:0:100}"
fi

# ------------------------------------------------------------------------------
# T007: Telemetry command
# ------------------------------------------------------------------------------
OUTPUT=$(node "$SKILL_SCRIPT" telemetry 2>&1)
if [[ "$OUTPUT" == *"Telemetry"* || "$OUTPUT" == *"telemetry"* ]]; then
  pass "T007: Telemetry command returns status"
else
  fail "T007: Telemetry command returns status" "Output: ${OUTPUT:0:100}"
fi

# ------------------------------------------------------------------------------
# T008: Unknown command handling
# ------------------------------------------------------------------------------
OUTPUT=$(node "$SKILL_SCRIPT" unknowncommand 2>&1)
if [[ "$OUTPUT" == *"Unknown"* || "$OUTPUT" == *"unknown"* || "$OUTPUT" == *"Available"* ]]; then
  pass "T008: Unknown command shows error"
else
  fail "T008: Unknown command shows error" "Output: ${OUTPUT:0:100}"
fi

# ------------------------------------------------------------------------------
# T009: Doctor command
# ------------------------------------------------------------------------------
OUTPUT=$(node "$SKILL_SCRIPT" doctor 2>&1)
if [[ "$OUTPUT" == *"Diagnos"* || "$OUTPUT" == *"API Key"* || "$OUTPUT" == *"Proxy"* ]]; then
  pass "T009: Doctor command shows diagnostics"
else
  fail "T009: Doctor command" "Output: ${OUTPUT:0:100}"
fi

# ------------------------------------------------------------------------------
# T010: Proxy command
# ------------------------------------------------------------------------------
OUTPUT=$(node "$SKILL_SCRIPT" proxy 2>&1 || true)
if [[ "$OUTPUT" == *"Proxy"* || "$OUTPUT" == *"Running"* || "$OUTPUT" == *"start"* ]]; then
  pass "T010: Proxy command shows status"
else
  fail "T010: Proxy command" "Output: ${OUTPUT:0:100}"
fi

# ------------------------------------------------------------------------------
# T013: Help includes new commands
# ------------------------------------------------------------------------------
OUTPUT=$(node "$SKILL_SCRIPT" 2>&1)
if [[ "$OUTPUT" == *"doctor"* && "$OUTPUT" == *"proxy"* ]]; then
  pass "T013: Help shows doctor and proxy commands"
else
  fail "T013: Help shows new commands" "Missing doctor/proxy in help output"
fi

# ------------------------------------------------------------------------------
# T011: CLI dependency check
# ------------------------------------------------------------------------------
if command -v relayplane-proxy &> /dev/null; then
  pass "T011: relayplane-proxy CLI is available"
else
  skip "T011: relayplane-proxy CLI check" "CLI not installed"
fi

# ------------------------------------------------------------------------------
# T012: relayplane CLI check  
# ------------------------------------------------------------------------------
if command -v relayplane &> /dev/null; then
  pass "T012: relayplane CLI is available"
else
  skip "T012: relayplane CLI check" "CLI not installed"
fi

# ------------------------------------------------------------------------------
# Summary
# ------------------------------------------------------------------------------
echo ""
echo "======================================"
echo "Results: $PASSED passed, $FAILED failed, $SKIPPED skipped"
echo "======================================"

if [[ $FAILED -gt 0 ]]; then
  exit 1
fi
