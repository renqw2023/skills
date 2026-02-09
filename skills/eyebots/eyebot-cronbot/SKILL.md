---
name: eyebot-cronbot
description: Task scheduler and blockchain automation engine
version: 1.0.0
author: ILL4NE
metadata:
  api_endpoint: http://93.186.255.184:8001
  pricing:
    per_use: $1
    lifetime: $25
  chains: [base, ethereum, polygon, arbitrum]
---

# Eyebot CronBot ⏰

Task scheduler and automation engine. Schedule recurring transactions, automate DeFi operations, and set up conditional triggers.

## API Endpoint
`http://93.186.255.184:8001`

## Usage
```bash
# Request payment
curl -X POST "http://93.186.255.184:8001/a2a/request-payment?agent_id=cronbot&caller_wallet=YOUR_WALLET"

# After payment, verify and execute
curl -X POST "http://93.186.255.184:8001/a2a/verify-payment?request_id=...&tx_hash=..."
```

## Pricing
- Per-use: $1
- Lifetime (unlimited): $25
- All 15 agents bundle: $200

## Capabilities
- Scheduled transactions
- Recurring DeFi operations
- Price-triggered actions
- Gas price automation
- Time-based claims
- Multi-step workflow automation
- Keeper network integration
- Event-driven triggers
- Task monitoring dashboard
