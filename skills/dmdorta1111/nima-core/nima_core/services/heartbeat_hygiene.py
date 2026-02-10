#!/usr/bin/env python3
"""
HEARTBEAT.md Hygiene — Auto-archive completed tasks to keep context lean.

Runs during heartbeat or standalone. If HEARTBEAT.md exceeds MAX_BYTES,
extracts completed sections and moves them to a daily archive file.

Keeps agent context small by ensuring HEARTBEAT.md stays a task list,
not a changelog.

Usage:
    python3 -m nima_core.services.heartbeat_hygiene          # check + fix
    python3 -m nima_core.services.heartbeat_hygiene --check   # check only
    python3 -m nima_core.services.heartbeat_hygiene --force   # archive even if under limit

Programmatic:
    from nima_core.services.heartbeat_hygiene import HeartbeatHygiene
    
    hygiene = HeartbeatHygiene(workspace="/path/to/workspace")
    result = hygiene.run()
    print(result["message"])

Author: NIMA Project
"""

import os
import re
import sys
import logging
from datetime import datetime
from pathlib import Path
from typing import Tuple

logger = logging.getLogger(__name__)

DEFAULT_MAX_BYTES = 2048  # 2KB limit


class HeartbeatHygiene:
    """Keeps HEARTBEAT.md lean by auto-archiving completed sections."""

    def __init__(
        self,
        workspace: str | Path | None = None,
        max_bytes: int = DEFAULT_MAX_BYTES,
    ):
        if workspace:
            self.workspace = Path(workspace)
        else:
            self.workspace = Path(
                os.environ.get("OPENCLAW_WORKSPACE",
                               Path(__file__).resolve().parents[2])
            )
        self.heartbeat_path = self.workspace / "HEARTBEAT.md"
        self.archive_dir = self.workspace / "memory" / "archives"
        self.max_bytes = max_bytes

    def run(self, check_only: bool = False, force: bool = False) -> dict:
        """
        Main routine. Returns dict with:
            size_before, size_after, archived, archive_file, message
        """
        result = {
            "size_before": 0,
            "size_after": 0,
            "archived": False,
            "archive_file": None,
            "message": "",
        }

        if not self.heartbeat_path.exists():
            result["message"] = "HEARTBEAT.md not found"
            logger.debug(result["message"])
            return result

        content = self.heartbeat_path.read_text(encoding="utf-8")
        result["size_before"] = len(content.encode("utf-8"))

        # Check if under limit
        if result["size_before"] <= self.max_bytes and not force:
            result["size_after"] = result["size_before"]
            result["message"] = (
                f"✅ HEARTBEAT.md is clean "
                f"({result['size_before']}B / {self.max_bytes}B limit)"
            )
            logger.debug(result["message"])
            return result

        # Extract completed sections
        clean_content, archived_content = self._extract_completed(content)

        if not archived_content.strip():
            result["size_after"] = result["size_before"]
            result["message"] = (
                f"⚠️ HEARTBEAT.md is {result['size_before']}B "
                f"(over {self.max_bytes}B) but no completed sections "
                f"found to archive. Manual cleanup needed."
            )
            logger.warning(result["message"])
            return result

        result["size_after"] = len(clean_content.encode("utf-8"))

        if check_only:
            saved = result["size_before"] - result["size_after"]
            result["message"] = (
                f"🔍 Would archive {saved}B of completed tasks"
            )
            return result

        # Write archive
        self.archive_dir.mkdir(parents=True, exist_ok=True)
        today = datetime.now().strftime("%Y-%m-%d")
        archive_file = self.archive_dir / f"HEARTBEAT_ARCHIVE_{today}.md"

        # Append to existing archive if present
        if archive_file.exists():
            existing = archive_file.read_text(encoding="utf-8")
            full_archive = (
                existing.rstrip() + "\n\n" + archived_content + "\n"
            )
        else:
            full_archive = (
                f"# HEARTBEAT Archive — {today}\n"
                f"*Auto-archived by heartbeat_hygiene.py*\n\n"
                f"{archived_content}\n"
            )

        # Atomic writes
        tmp_hb = self.heartbeat_path.with_suffix(".md.tmp")
        tmp_ar = archive_file.with_suffix(".md.tmp")

        try:
            tmp_hb.write_text(clean_content, encoding="utf-8")
            tmp_ar.write_text(full_archive, encoding="utf-8")

            tmp_ar.replace(archive_file)
            tmp_hb.replace(self.heartbeat_path)

            result["archived"] = True
            result["archive_file"] = str(archive_file)
            saved = result["size_before"] - result["size_after"]
            result["message"] = (
                f"🧹 Archived {saved}B of completed tasks → "
                f"{archive_file.name} "
                f"({result['size_after']}B remaining)"
            )
            logger.info(result["message"])
        except Exception as e:
            tmp_hb.unlink(missing_ok=True)
            tmp_ar.unlink(missing_ok=True)
            result["message"] = f"❌ Archive failed: {e}"
            logger.error(result["message"])

        return result

    def _extract_completed(
        self, content: str
    ) -> Tuple[str, str]:
        """
        Split content into (clean, archived).
        Completed = sections with ✅, DONE, COMPLETE markers or all [x].
        """
        lines = content.split("\n")
        keep_lines: list[str] = []
        archive_lines: list[str] = []

        section_header = ""
        section_body: list[str] = []

        def flush_section():
            nonlocal section_header, section_body
            if not section_header:
                return
            body_text = "\n".join(section_body)
            if self._is_completed(section_header, body_text):
                archive_lines.append(section_header)
                archive_lines.extend(section_body)
                archive_lines.append("")
            else:
                keep_lines.append(section_header)
                keep_lines.extend(section_body)
            section_header = ""
            section_body = []

        for line in lines:
            if re.match(r"^#{2,3}\s+", line):
                flush_section()
                section_header = line
                section_body = []
            elif section_header:
                section_body.append(line)
            else:
                keep_lines.append(line)

        flush_section()

        clean = "\n".join(keep_lines).strip() + "\n"
        archived = "\n".join(archive_lines).strip()
        return clean, archived

    @staticmethod
    def _is_completed(header: str, body: str) -> bool:
        """Check if a section is completed and safe to archive."""
        h = header.lower()

        # Explicit markers
        if any(m in h for m in ["✅ completed", "— done", "— complete"]):
            return True
        if "✅" in header and "completed" in h:
            return True

        # All checkboxes checked (3+ items)
        checks = re.findall(r"\[[ x]\]", body)
        if checks and len(checks) >= 3 and all(c == "[x]" for c in checks):
            return True

        return False


def main():
    check_only = "--check" in sys.argv
    force = "--force" in sys.argv

    hygiene = HeartbeatHygiene()
    result = hygiene.run(check_only=check_only, force=force)
    print(result["message"])

    if result.get("archived"):
        print(f"   Before: {result['size_before']}B → After: {result['size_after']}B")
        print(f"   Archive: {result['archive_file']}")


if __name__ == "__main__":
    main()
