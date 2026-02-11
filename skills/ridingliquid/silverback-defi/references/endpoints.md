# Silverback x402 API — Endpoint Reference

Base URL: `https://x402.silverbackdefi.app`

All endpoints require x402 micropayment (USDC on Base). No API keys needed.

## Chat (Recommended)

| Method | Path | Price | Description |
|--------|------|-------|-------------|
| POST | `/api/v1/chat` | $0.05 | AI chat with all intelligence tools |

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
| POST | `/api/v1/dex-metrics` | $0.001 | DEX trading volume and metrics |
| POST | `/api/v1/token-metadata` | $0.001 | Token details and contract info |
| POST | `/api/v1/correlation-matrix` | $0.005 | Token price correlation analysis |

## Trading & Analysis

| Method | Path | Price | Description |
|--------|------|-------|-------------|
| POST | `/api/v1/swap-quote` | $0.002 | Optimal swap route with price impact |
| POST | `/api/v1/swap` | $0.05 | Non-custodial Permit2 swap (returns EIP-712 signing data) |
| POST | `/api/v1/technical-analysis` | $0.02 | RSI, MACD, Bollinger Bands, signals |
| POST | `/api/v1/backtest` | $0.10 | Backtest a trading strategy |

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
| POST | `/api/v1/arbitrage-scanner` | $0.005 | Cross-DEX arbitrage opportunities |
| POST | `/api/v1/agent-reputation` | $0.001 | ERC-8004 agent reputation scores |
| POST | `/api/v1/agent-discover` | $0.002 | Discover AI agents by capability |

---

## Payment (x402)

All endpoints use the x402 protocol. Your agent's wallet pays USDC on Base automatically:

1. Request hits endpoint
2. Server returns HTTP 402 with payment requirements
3. Your wallet signs a USDC payment
4. Request retries with `X-Payment` header
5. Server verifies payment, returns data

Use `@x402/fetch` to handle this automatically:

```javascript
import { wrapFetchWithPayment } from '@x402/fetch';
import { createWalletClient, http } from 'viem';
import { privateKeyToAccount } from 'viem/accounts';
import { base } from 'viem/chains';

const wallet = createWalletClient({
  account: privateKeyToAccount('0xYOUR_KEY'),
  chain: base,
  transport: http(),
});

const x402fetch = wrapFetchWithPayment(fetch, wallet);
const res = await x402fetch('https://x402.silverbackdefi.app/api/v1/top-coins', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({}),
});
```

## Response Format

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
