# Session Store Hygiene (Digest + Dismiss Inactive Sessions)

## Why
Long-running OpenClaw setups can accumulate:
- stale cron session keys in `~/.openclaw/agents/main/sessions/sessions.json`
- orphan transcript files `~/.openclaw/agents/main/sessions/*.jsonl`

This inflates storage and increases operational noise.

## Script
Use bundled script:
- `skills/context-clean-up/scripts/session_gc.py`

## Recommended workflow
1. Run dry-run first.
2. Review stale key/orphan counts.
3. Apply only with explicit user approval.
4. Keep backup folder for rollback.

## Dry-run example
```bash
bash -lc 'cd "${WORKDIR:-.}" && uv run --python 3.13 -- python skills/context-clean-up/scripts/session_gc.py --retention-days 7 --stale-days 3 --json --report-out memory/session-gc/latest-report.json'
```

## Apply example (conservative)
```bash
bash -lc 'cd "${WORKDIR:-.}" && uv run --python 3.13 -- python skills/context-clean-up/scripts/session_gc.py --retention-days 7 --active-cron-id <id1,id2,...> --apply --prune-stale-keys --move-orphan-jsonl --json --report-out memory/session-gc/latest-apply.json'
```

## Rollback
- `sessions.json` backup: `<backup_dir>/sessions.json.before`
- moved transcript backups: `<backup_dir>/orphan-jsonl/`

To rollback, restore `sessions.json.before` and move files back from `orphan-jsonl/`.
