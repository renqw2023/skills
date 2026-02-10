#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "nova-act",
#     "pydantic>=2.0",
#     "fire",
# ]
# ///
"""
Run browser automation tasks using Amazon Nova Act.

Usage:
    uv run nova_act_runner.py --url "https://google.com/flights" --task "Find flights from SFO to NYC and return the options"
"""

import json
import os
import sys

from pydantic import BaseModel


class TaskResult(BaseModel):
    """Generic result schema for any browser task."""
    summary: str
    details: list[str]


def run(url: str, task: str) -> None:
    """
    Run a browser automation task with Nova Act.

    Args:
        url: Starting URL to navigate to
        task: Task to perform and return results (e.g., "Find flights from SFO to NYC and return the options")
    """
    api_key = os.environ.get("NOVA_ACT_API_KEY")
    if not api_key:
        print("Error: NOVA_ACT_API_KEY environment variable not set", file=sys.stderr)
        sys.exit(1)

    from nova_act import NovaAct

    try:
        with NovaAct(starting_page=url) as nova:
            # act_get performs the task AND extracts results in one call
            result = nova.act_get(task, schema=TaskResult.model_json_schema())

            # Parse and output
            task_result = TaskResult.model_validate(result.parsed_response)
            print(json.dumps(task_result.model_dump(), indent=2))

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


def main():
    import fire
    fire.Fire(run)


if __name__ == "__main__":
    main()
