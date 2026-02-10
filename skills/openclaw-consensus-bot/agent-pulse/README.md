# Agent Pulse — OpenClaw Skill 💓

On-chain liveness signaling for autonomous agents on Base.

## Quick Start

```bash
# 1. Configure
export PRIVATE_KEY="0x..."
./scripts/setup.sh --auto-approve

# 2. Send a pulse
./scripts/pulse.sh --direct 1000000000000000000

# 3. Check status
./scripts/status.sh 0xYourAddress

# 4. Auto-pulse (cron)
./scripts/auto-pulse.sh
```

## Requirements

- `curl`, `jq` — API calls and JSON parsing
- `cast` (Foundry) — on-chain transactions
- `PRIVATE_KEY` env var — agent wallet key

## Scripts

| Script          | Purpose                                |
|-----------------|----------------------------------------|
| `setup.sh`      | Auto-detect wallet, check balance, configure |
| `pulse.sh`      | Send on-chain pulse                    |
| `auto-pulse.sh` | Cron-safe heartbeat (skips if alive)   |
| `status.sh`     | Check one agent's status               |
| `monitor.sh`    | Check multiple agents or view feed     |
| `config.sh`     | Protocol configuration                 |
| `health.sh`     | Protocol health check                  |

## Network

- **Chain:** Base (8453)
- **PULSE Token:** `0x21111B39A502335aC7e45c4574Dd083A69258b07`
- **PulseRegistry:** `0xe61C615743A02983A46aFF66Db035297e8a43846`
- **API:** https://agent-pulse-nine.vercel.app

See `SKILL.md` for full documentation.
