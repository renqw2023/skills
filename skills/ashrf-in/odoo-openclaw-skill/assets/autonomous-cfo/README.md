# Autonomous CFO Engine (Odoo)

## Purpose

Reliable, evidence-backed financial intelligence on top of Odoo for OpenClaw skills.

## Current capabilities

- Odoo financial summary (sales/expenses/unpaid/overdue)
- VAT computation (output/input/net)
- Cash-flow status
- Trend analysis with chart output
- Rules anomalies + AI-assisted anomaly narrative
- Natural-language financial Q&A grounded in Odoo data

## API backends

- `json2` (preferred on Odoo 19+)
- `xmlrpc` (fallback for older Odoo)
- `auto` routing in `cfo-cli` chooses backend by server version

## AI runtime

AI analysis is routed through **OpenClaw native local agent runtime** (`openclaw agent --local`), not standalone Gemini API flows.

## Key files

- `src/connectors/odoo_client.py` — JSON-2 + XML-RPC connector
- `src/tools/cfo_cli.py` — command interface
- `src/logic/finance_engine.py` — deterministic accounting logic
- `src/logic/intelligence_engine.py` — VAT/trend/anomaly orchestration
- `src/logic/openclaw_intelligence.py` — OpenClaw-native AI adapter

## Dependencies

See `requirements.txt`:
- `requests`
- `matplotlib`

Environment variables are loaded via an internal lightweight `.env` parser (no `python-dotenv` runtime dependency).

## Notes

- Read-only by default in skill workflows.
- Use `rpc-call --allow-write` only for explicit user-approved mutating operations.
