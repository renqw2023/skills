#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import shutil
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any


CRON_PREFIX = "agent:main:cron:"


@dataclass
class SessionGcResult:
    sessions_dir: Path
    sessions_json_path: Path
    retention_days: int
    stale_days: int
    now_ms: int
    active_cron_ids: set[str]
    stale_detection: str
    keys_total: int
    cron_base_keys_total: int
    cron_run_keys_total: int
    stale_cron_base_keys: list[str]
    stale_cron_run_keys: list[str]
    jsonl_total: int
    referenced_session_ids: int
    orphan_jsonl_all: list[Path]
    orphan_jsonl_old_enough: list[Path]
    orphan_old_enough_bytes: int
    removed_keys: list[str]
    moved_orphans: list[Path]
    backup_dir: Path | None

    def to_dict(self) -> dict[str, Any]:
        return {
            "sessions_dir": str(self.sessions_dir),
            "sessions_json_path": str(self.sessions_json_path),
            "retention_days": self.retention_days,
            "stale_days": self.stale_days,
            "now_ms": self.now_ms,
            "active_cron_ids": sorted(self.active_cron_ids),
            "stale_detection": self.stale_detection,
            "keys_total": self.keys_total,
            "cron_base_keys_total": self.cron_base_keys_total,
            "cron_run_keys_total": self.cron_run_keys_total,
            "stale_cron_base_keys": self.stale_cron_base_keys,
            "stale_cron_run_keys": self.stale_cron_run_keys,
            "jsonl_total": self.jsonl_total,
            "referenced_session_ids": self.referenced_session_ids,
            "orphan_jsonl_all_count": len(self.orphan_jsonl_all),
            "orphan_jsonl_old_enough_count": len(self.orphan_jsonl_old_enough),
            "orphan_old_enough_bytes": self.orphan_old_enough_bytes,
            "orphan_old_enough_mb": round(self.orphan_old_enough_bytes / (1024 * 1024), 3),
            "removed_keys_count": len(self.removed_keys),
            "moved_orphans_count": len(self.moved_orphans),
            "removed_keys": self.removed_keys,
            "moved_orphans": [str(p) for p in self.moved_orphans],
            "backup_dir": str(self.backup_dir) if self.backup_dir else None,
        }


def _parse_active_ids(values: list[str]) -> set[str]:
    out: set[str] = set()
    for raw in values:
        for token in raw.split(","):
            token = token.strip()
            if token:
                out.add(token)
    return out


def _extract_cron_id(session_key: str) -> str | None:
    if not session_key.startswith(CRON_PREFIX):
        return None
    rest = session_key[len(CRON_PREFIX) :]
    if ":run:" in rest:
        return rest.split(":run:", 1)[0]
    return rest


def _load_sessions_json(path: Path) -> dict[str, Any]:
    raw = path.read_text(encoding="utf-8")
    data = json.loads(raw)
    if not isinstance(data, dict):
        raise ValueError(f"sessions.json is not an object: {path}")
    return data


def run_gc(
    sessions_dir: Path,
    retention_days: int,
    stale_days: int,
    active_cron_ids: set[str],
    apply_changes: bool,
    backup_root: Path,
    prune_stale_keys: bool,
    move_orphan_jsonl: bool,
    allow_heuristic_prune: bool,
) -> SessionGcResult:
    now_ms = int(time.time() * 1000)
    cutoff_ms = now_ms - retention_days * 24 * 60 * 60 * 1000
    stale_cutoff_ms = now_ms - stale_days * 24 * 60 * 60 * 1000

    sessions_json_path = sessions_dir / "sessions.json"
    if not sessions_json_path.exists():
        raise FileNotFoundError(f"sessions.json not found: {sessions_json_path}")

    data = _load_sessions_json(sessions_json_path)

    keys_total = len(data)
    cron_base_keys: list[str] = []
    cron_run_keys: list[str] = []

    referenced_ids: set[str] = set()
    for key, meta in data.items():
        if not isinstance(meta, dict):
            continue
        if key.startswith(CRON_PREFIX):
            if ":run:" in key:
                cron_run_keys.append(key)
            else:
                cron_base_keys.append(key)
        sid = meta.get("sessionId")
        if isinstance(sid, str) and sid:
            referenced_ids.add(sid)

    jsonl_files = sorted(sessions_dir.glob("*.jsonl"))
    jsonl_total = len(jsonl_files)
    jsonl_stems = {p.stem for p in jsonl_files}

    orphan_stems = sorted(jsonl_stems - referenced_ids)
    orphan_files_all = [sessions_dir / f"{stem}.jsonl" for stem in orphan_stems]
    orphan_files_old: list[Path] = []
    orphan_old_bytes = 0

    for p in orphan_files_all:
        try:
            st = p.stat()
        except FileNotFoundError:
            continue
        if int(st.st_mtime * 1000) <= cutoff_ms:
            orphan_files_old.append(p)
            orphan_old_bytes += st.st_size

    stale_base: list[str] = []
    stale_run: list[str] = []
    stale_detection = "exact-active-ids" if active_cron_ids else "heuristic-updatedAt"

    if active_cron_ids:
        for key in cron_base_keys:
            cid = _extract_cron_id(key)
            if cid and cid not in active_cron_ids:
                stale_base.append(key)
        for key in cron_run_keys:
            cid = _extract_cron_id(key)
            if cid and cid not in active_cron_ids:
                stale_run.append(key)
    else:
        for key in cron_base_keys:
            meta = data.get(key)
            ua = meta.get("updatedAt") if isinstance(meta, dict) else None
            if isinstance(ua, (int, float)) and int(ua) <= stale_cutoff_ms:
                stale_base.append(key)
        for key in cron_run_keys:
            meta = data.get(key)
            ua = meta.get("updatedAt") if isinstance(meta, dict) else None
            if isinstance(ua, (int, float)) and int(ua) <= stale_cutoff_ms:
                stale_run.append(key)

    removed_keys: list[str] = []
    moved_orphans: list[Path] = []
    backup_dir: Path | None = None

    if apply_changes:
        ts = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
        backup_dir = backup_root / f"session-gc-{ts}"
        backup_dir.mkdir(parents=True, exist_ok=True)

        shutil.copy2(sessions_json_path, backup_dir / "sessions.json.before")

        if prune_stale_keys:
            if not active_cron_ids and not allow_heuristic_prune:
                raise ValueError(
                    "Refusing to prune stale keys using heuristic mode. Provide --active-cron-id or pass --allow-heuristic-prune."
                )
            keys_to_remove = set(stale_base + stale_run)
            for key in sorted(keys_to_remove):
                if key in data:
                    removed_keys.append(key)
                    del data[key]

            tmp_path = sessions_json_path.with_suffix(".json.tmp")
            tmp_path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            tmp_path.replace(sessions_json_path)

        if move_orphan_jsonl:
            trash_dir = backup_dir / "orphan-jsonl"
            trash_dir.mkdir(parents=True, exist_ok=True)
            for p in orphan_files_old:
                if not p.exists():
                    continue
                target = trash_dir / p.name
                shutil.move(str(p), str(target))
                moved_orphans.append(target)

        (backup_dir / "summary.json").write_text(
            json.dumps(
                {
                    "removed_keys": removed_keys,
                    "moved_orphans": [str(p) for p in moved_orphans],
                },
                ensure_ascii=False,
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )

    return SessionGcResult(
        sessions_dir=sessions_dir,
        sessions_json_path=sessions_json_path,
        retention_days=retention_days,
        stale_days=stale_days,
        now_ms=now_ms,
        active_cron_ids=active_cron_ids,
        stale_detection=stale_detection,
        keys_total=keys_total,
        cron_base_keys_total=len(cron_base_keys),
        cron_run_keys_total=len(cron_run_keys),
        stale_cron_base_keys=stale_base,
        stale_cron_run_keys=stale_run,
        jsonl_total=jsonl_total,
        referenced_session_ids=len(referenced_ids),
        orphan_jsonl_all=orphan_files_all,
        orphan_jsonl_old_enough=orphan_files_old,
        orphan_old_enough_bytes=orphan_old_bytes,
        removed_keys=removed_keys,
        moved_orphans=moved_orphans,
        backup_dir=backup_dir,
    )


def _render_human(result: SessionGcResult, apply_changes: bool) -> str:
    lines: list[str] = []
    lines.append("Session GC report")
    lines.append(f"sessions_dir: {result.sessions_dir}")
    lines.append(f"retention_days: {result.retention_days}")
    lines.append(f"stale_days: {result.stale_days} ({result.stale_detection})")
    lines.append(f"keys_total: {result.keys_total}")
    lines.append(
        f"cron_keys: base={result.cron_base_keys_total}, run={result.cron_run_keys_total}, stale_base={len(result.stale_cron_base_keys)}, stale_run={len(result.stale_cron_run_keys)}"
    )
    lines.append(
        f"jsonl: total={result.jsonl_total}, referenced={result.referenced_session_ids}, orphan_all={len(result.orphan_jsonl_all)}, orphan_old_enough={len(result.orphan_jsonl_old_enough)}"
    )
    lines.append(
        f"reclaimable_old_orphans: {result.orphan_old_enough_bytes} bytes ({result.orphan_old_enough_bytes / (1024 * 1024):.2f} MB)"
    )

    if not apply_changes:
        lines.append("mode: dry-run (no changes)")
    else:
        lines.append("mode: apply")
        lines.append(f"removed_keys: {len(result.removed_keys)}")
        lines.append(f"moved_orphans: {len(result.moved_orphans)}")
        lines.append(f"backup_dir: {result.backup_dir}")

    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Digest + GC inactive OpenClaw sessions safely")
    ap.add_argument(
        "--sessions-dir",
        default=str(Path.home() / ".openclaw/agents/main/sessions"),
        help="Path to sessions directory (contains sessions.json + *.jsonl)",
    )
    ap.add_argument(
        "--active-cron-id",
        action="append",
        default=[],
        help="Active cron id (repeatable, or comma-separated list)",
    )
    ap.add_argument(
        "--retention-days",
        type=int,
        default=7,
        help="Only orphan jsonl older than this are candidates for move/delete",
    )
    ap.add_argument(
        "--stale-days",
        type=int,
        default=3,
        help="When active cron ids are not provided, mark cron keys older than this as stale candidates",
    )
    ap.add_argument("--apply", action="store_true", help="Apply changes (default: dry-run)")
    ap.add_argument(
        "--prune-stale-keys",
        action="store_true",
        help="When --apply, remove stale cron keys from sessions.json (requires --active-cron-id)",
    )
    ap.add_argument(
        "--move-orphan-jsonl",
        action="store_true",
        help="When --apply, move old orphan *.jsonl into backup folder",
    )
    ap.add_argument(
        "--allow-heuristic-prune",
        action="store_true",
        help="Allow pruning stale keys using heuristic mode (without explicit active cron ids)",
    )
    ap.add_argument(
        "--backup-root",
        default="memory/session-gc-backups",
        help="Backup root dir for apply mode",
    )
    ap.add_argument(
        "--report-out",
        default="",
        help="Optional path to write JSON report",
    )
    ap.add_argument("--json", action="store_true", help="Print JSON report")

    args = ap.parse_args(argv)

    try:
        sessions_dir = Path(args.sessions_dir).expanduser().resolve()
        active_ids = _parse_active_ids(args.active_cron_id)
        backup_root = Path(args.backup_root).expanduser().resolve()

        result = run_gc(
            sessions_dir=sessions_dir,
            retention_days=args.retention_days,
            stale_days=args.stale_days,
            active_cron_ids=active_ids,
            apply_changes=args.apply,
            backup_root=backup_root,
            prune_stale_keys=args.prune_stale_keys,
            move_orphan_jsonl=args.move_orphan_jsonl,
            allow_heuristic_prune=args.allow_heuristic_prune,
        )

        payload = result.to_dict()
        if args.report_out:
            out = Path(args.report_out).expanduser().resolve()
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

        if args.json:
            print(json.dumps(payload, ensure_ascii=False, indent=2))
        else:
            print(_render_human(result, apply_changes=args.apply))

        return 0
    except Exception as exc:  # pragma: no cover - CLI fallback
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
