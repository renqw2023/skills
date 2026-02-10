# Silverback x402 API — Endpoint Reference

Base URL: `https://x402.silverbackdefi.app`

All endpoints require authentication via `x-api-key` header or x402 micropayment.

## Chat (Recommended)

| Method | Path | Price | Description |
|--------|------|-------|-------------|
| POST | `/api/v1/chat` | $0.05 | AI chat with all 11 intelligence tools |

**Input:** `{"message": "your question", "history": []}`
**Output:** `{"success": true, "data": {"response": "...", "toolsUsed": ["top_coins"]}}`

The chat endpoint is the easiest way to use Silverback — ask a natural language question and the AI agent selects the right tools automatically.

---

## Market Data

| Method | Path | Price | Description |
|--------|------|-------|-------------|
| POST | `/api/v1/top-coins` | $0.001 | Top cryptocurrencies by market cap |
| POST | `/api/v1/top-pools` | $0.001 | Top yielding liquidity pools on Base |
| POST | `/api/v1/top-protocols` | $0.001 | Top DeFi protocols by TVL |
| POST | `/api/v1/trending-tokens` | $0.001 | Trending tokens on CoinGecko |
| POST | `/api/v1/gas-price` | $0.001 | Current Base chain gas prices |

## Trading & Analysis

| Method | Path | Price | Description |
|--------|------|-------|-------------|
| POST | `/api/v1/swap-quote` | $0.002 | Optimal swap route with price impact |
| POST | `/api/v1/swap` | $0.05 | Execute token swap via Permit2 |
| POST | `/api/v1/technical-analysis` | $0.02 | RSI, MACD, Bollinger Bands, signals |
| POST | `/api/v1/backtest` | $0.10 | Backtest a trading strategy |
| POST | `/api/v1/correlation-matrix` | $0.005 | Token price correlation analysis |

## Yield & DeFi

| Method | Path | Price | Description |
|--------|------|-------|-------------|
| POST | `/api/v1/defi-yield` | $0.02 | Yield opportunities (lending, LP, staking) |
| POST | `/api/v1/pool-analysis` | $0.005 | Liquidity pool health analysis |

## Security & Intelligence

| Method | Path | Price | Description |
|--------|------|-------|-------------|
| POST | `/api/v1/token-audit` | $0.01 | Token contract security audit |
| POST | `/api/v1/whale-moves` | $0.01 | Large wallet movement tracking |
| POST | `/api/v1/agent-reputation` | $0.001 | ERC-8004 agent reputation scores |
| POST | `/api/v1/agent-discover` | $0.002 | Discover AI agents by capability |

---

## Authentication

Include the API key in every request:

```bash
curl -X POST https://x402.silverbackdefi.app/api/v1/chat \
  -H "Content-Type: application/json" \
  -H "x-api-key: sk_sb_YOUR_KEY" \
  -d '{"message": "top coins"}'
```

Or use Bearer auth:
```bash
-H "Authorization: Bearer sk_sb_YOUR_KEY"
```

## Response Format

All responses follow ZAUTH format:
```json
{
  "success": true,
  "data": { ... }
}
```

Error responses:
```json
{
  "success": false,
  "error": "Error description"
}
```
