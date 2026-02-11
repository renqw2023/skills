#!/usr/bin/env python3
"""Parse Claude Code stream-json output and post to a chat platform.

Reads JSON lines from stdin (Claude Code's --output-format stream-json),
formats them into human-readable messages, and posts via a platform adapter.

Features:
  - Platform abstraction (discord by default, extensible)
  - Smart file content preview (first/last lines for large files)
  - Bash command stdout capture
  - Rate limiting (25 posts/60s with batching)
  - Cumulative cost tracking
  - Noise filtering (--skip-reads via SKIP_READS env)
  - End-of-session summary
  - Raw stream logging for session resume
"""

import json
import sys
import os
import time

# ---------------------------------------------------------------------------
# Platform setup — load the appropriate adapter (discord, slack, etc.)
# ---------------------------------------------------------------------------
# Add scripts/ dir to path so platforms package is importable
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from platforms import get_platform

platform = get_platform()  # reads PLATFORM env var, defaults to "discord"

# ---------------------------------------------------------------------------
# Configuration from environment
# ---------------------------------------------------------------------------
skip_reads = os.environ.get("SKIP_READS", "false").lower() == "true"
relay_dir = os.environ.get("RELAY_DIR", "")

# ---------------------------------------------------------------------------
# Rate limiter — max 25 posts per 60 seconds, with batching on overflow
# ---------------------------------------------------------------------------
RATE_LIMIT = 25
RATE_WINDOW = 60  # seconds

_post_times = []      # timestamps of recent posts
_batch_queue = []     # messages queued while rate-limited


def _flush_batch():
    """Post all queued messages as a single combined message."""
    global _batch_queue
    if not _batch_queue:
        return
    count = len(_batch_queue)
    combined = f"**[batched {count} events]**\n" + "\n---\n".join(_batch_queue)
    _batch_queue = []
    platform.post(combined)
    _post_times.append(time.time())


def _prune_window():
    """Remove timestamps older than the rate window."""
    global _post_times
    cutoff = time.time() - RATE_WINDOW
    _post_times = [t for t in _post_times if t > cutoff]


def post(msg, name=None):
    """Rate-limited post. Batches messages when the limit is hit."""
    # In replay mode, skip rate limiting but add small delay to avoid Discord 429s
    if is_replay:
        time.sleep(0.5)
        platform.post(msg, name)
        return

    _prune_window()

    if len(_post_times) >= RATE_LIMIT:
        _batch_queue.append(msg)
        return

    # If there were batched messages waiting, flush them first
    if _batch_queue:
        _flush_batch()

    platform.post(msg, name)
    _post_times.append(time.time())


# ---------------------------------------------------------------------------
# Cost tracking — accumulate across all tool calls
# ---------------------------------------------------------------------------
cumulative_cost = 0.0

# ---------------------------------------------------------------------------
# Session stats — for end summary
# ---------------------------------------------------------------------------
files_created = []
files_edited = []
bash_commands = []
tools_used = {}  # tool_name -> count

# ---------------------------------------------------------------------------
# Stream logging for session resume
# ---------------------------------------------------------------------------
stream_log = None
is_replay = os.environ.get("REPLAY_MODE", "false").lower() == "true"
if relay_dir and not is_replay:
    stream_path = os.path.join(relay_dir, "stream.jsonl")
    try:
        stream_log = open(stream_path, "a")
    except OSError:
        pass

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def format_file_preview(content):
    """Format file content with smart truncation.

    - <=30 lines: show first 15 lines + "... (N more lines)" if needed
    - >30 lines: show first 10 + "..." + last 5 lines
    Returns (preview_str, total_lines).
    """
    lines = content.split("\n")
    total = len(lines)

    if total <= 15:
        preview = content
    elif total <= 30:
        preview = "\n".join(lines[:15]) + f"\n... ({total - 15} more lines)"
    else:
        head = "\n".join(lines[:10])
        tail = "\n".join(lines[-5:])
        preview = f"{head}\n... ({total - 15} more lines) ...\n{tail}"

    return preview, total


def truncate(s, limit):
    """Truncate string to limit chars with ellipsis indicator."""
    if len(s) <= limit:
        return s
    return s[:limit] + "…(truncated)"


# ---------------------------------------------------------------------------
# Main event loop
# ---------------------------------------------------------------------------
# Track the last tool_use name so we can correlate tool_results with their tool
_last_tool_name = None

for line in sys.stdin:
    line = line.strip()
    if not line:
        continue

    # Skip non-JSON lines (ANSI artifacts from unbuffer)
    if not line.startswith("{"):
        continue

    # Log raw line for session resume
    if stream_log:
        stream_log.write(line + "\n")
        stream_log.flush()

    try:
        evt = json.loads(line)
    except json.JSONDecodeError:
        continue

    etype = evt.get("type", "")

    # --- System init ---
    if etype == "system" and evt.get("subtype") == "init":
        model = evt.get("model", "unknown")
        mode = evt.get("permissionMode", "default")
        post(f"⚙️ Model: `{model}` | Mode: `{mode}`")

    # --- Assistant messages (tool calls + text) ---
    elif etype == "assistant":
        msg = evt.get("message", {})

        # Track cost from usage metadata if present
        usage = msg.get("usage", {})
        if usage:
            input_cost = usage.get("input_tokens", 0) * 0.000003   # $3/M input
            output_cost = usage.get("output_tokens", 0) * 0.000015  # $15/M output
            cumulative_cost += input_cost + output_cost

        for block in msg.get("content", []):
            if not isinstance(block, dict):
                continue
            if block.get("type") == "text":
                text = block["text"].strip()
                if text:
                    post(f"💬 {text}")

            elif block.get("type") == "tool_use":
                tool = block.get("name", "?")
                inp = block.get("input", {})

                # Track tool usage counts
                tools_used[tool] = tools_used.get(tool, 0) + 1
                _last_tool_name = tool

                if tool == "Write":
                    fp = inp.get("file_path", "?")
                    content = inp.get("content", "")
                    preview, total = format_file_preview(content)
                    # Truncate preview for Discord message limits
                    preview = truncate(preview, 800)
                    post(f"📝 **Write** `{fp}` ({total} lines)\n```\n{preview}\n```")

                elif tool in ("Edit", "MultiEdit"):
                    fp = inp.get("file_path", "?")
                    post(f"✏️ **{tool}** `{fp}`")

                elif tool == "Bash":
                    cmd = truncate(inp.get("command", "?"), 300)
                    post(f"🖥️ **Bash** `{cmd}`")
                    bash_commands.append(cmd)

                elif tool == "Read":
                    fp = inp.get("file_path", "?")
                    if not skip_reads:
                        post(f"👁️ **Read** `{fp}`")

                elif tool == "WebSearch":
                    query = inp.get("query", "?")
                    post(f"🔍 **Search** `{query}`")

                elif tool == "WebFetch":
                    url = inp.get("url", "?")
                    post(f"🌐 **Fetch** `{url}`")

                else:
                    post(f"🔧 **{tool}**")

    # --- User events (tool results, bash output) ---
    elif etype == "user":
        # Handle tool_use_result (file create/update confirmations)
        result = evt.get("tool_use_result", {})
        if result and isinstance(result, dict):
            rtype = result.get("type", "")
            fp = result.get("filePath", "")
            if rtype == "create" and fp:
                files_created.append(fp)
                post(f"✅ Created `{fp}`")
            elif rtype == "update" and fp:
                files_edited.append(fp)
                post(f"✅ Updated `{fp}`")

        # Handle bash command output from tool_result content blocks
        msg = evt.get("message", {})
        for block in msg.get("content", []):
            if not isinstance(block, dict):
                continue
            if block.get("type") == "tool_result":
                for sub in block.get("content", []):
                    if not isinstance(sub, dict):
                        continue
                    if sub.get("type") == "text" and _last_tool_name == "Bash":
                        stdout = sub.get("text", "").strip()
                        if stdout:
                            stdout = truncate(stdout, 800)
                            post(f"📤 **Output** ```\n{stdout}\n```")

    # --- Result (session complete) ---
    elif etype == "result":
        success = not evt.get("is_error", False)
        duration = evt.get("duration_ms", 0) / 1000
        cost = evt.get("total_cost_usd", 0)
        # Use the authoritative cost from the result if available, else our estimate
        final_cost = cost if cost else cumulative_cost
        result_text = truncate(evt.get("result", ""), 300)
        turns = evt.get("num_turns", 0)

        icon = "✅" if success else "❌"
        status = "Completed" if success else "Failed"

        # --- End summary block ---
        summary_parts = [f"{icon} **{status}** | {turns} turns | {duration:.1f}s | ${final_cost:.4f}"]

        if result_text:
            summary_parts.append(f"> {result_text}")

        summary_parts.append("")  # blank line before summary
        summary_parts.append("📊 **Session Summary**")

        if files_created:
            unique_created = sorted(set(files_created))
            summary_parts.append(f"  📝 Created: {len(unique_created)} file(s)")
            for f in unique_created[:10]:
                summary_parts.append(f"    • `{f}`")
            if len(unique_created) > 10:
                summary_parts.append(f"    • ... and {len(unique_created) - 10} more")

        if files_edited:
            unique_edited = sorted(set(files_edited))
            summary_parts.append(f"  ✏️ Edited: {len(unique_edited)} file(s)")
            for f in unique_edited[:10]:
                summary_parts.append(f"    • `{f}`")
            if len(unique_edited) > 10:
                summary_parts.append(f"    • ... and {len(unique_edited) - 10} more")

        if bash_commands:
            summary_parts.append(f"  🖥️ Bash commands: {len(bash_commands)}")

        if tools_used:
            tool_summary = ", ".join(f"{k}: {v}" for k, v in sorted(tools_used.items()))
            summary_parts.append(f"  🔧 Tools: {tool_summary}")

        summary_parts.append(f"  💰 Total cost: ${final_cost:.4f}")

        post("\n".join(summary_parts))

    # Periodically flush batched messages (after each event, check if window opened)
    _prune_window()
    if _batch_queue and len(_post_times) < RATE_LIMIT:
        _flush_batch()

# Flush any remaining batched messages
if _batch_queue:
    _flush_batch()

# Close stream log
if stream_log:
    stream_log.close()

print("RELAY_DONE", flush=True)
