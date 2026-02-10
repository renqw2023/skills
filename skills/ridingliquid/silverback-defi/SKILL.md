---
name: silverback-defi
description: DeFi intelligence powered by Silverback — market data, swap quotes, technical analysis, yield opportunities, token audits, whale tracking, and AI chat via 11 real-time tools on Base chain
homepage: https://silverbackdefi.app
user-invocable: true
metadata: {"clawdbot":{"requires":{"bins":["curl","jq"]},"emoji":"🦍","category":"Finance & Crypto","tags":["defi","trading","crypto","yield","swap","analysis","base-chain"]}}
---

# Silverback DeFi Intelligence

Silverback provides real-time DeFi intelligence via an AI agent with 11 specialized tools. Ask any question about crypto markets, trading, yields, or token security — Silverback's agent analyzes on-chain data and returns actionable insights.

## Setup

1. Get an API key from the Silverback team
2. Create `config.json` in the skill root:
```json
{
  "api_key": "sk_sb_YOUR_KEY_HERE"
}
```

## Usage

```bash
bash scripts/silverback.sh "What are the top coins right now?"
bash scripts/silverback.sh "Analyze ETH technically"
bash scripts/silverback.sh "Where can I earn yield on USDC?"
bash scripts/silverback.sh "Is 0x558881c4959e9cf961a7E1815FCD6586906babd2 safe?"
bash scripts/silverback.sh "Show me whale activity on VIRTUAL"
```

## Available Intelligence Tools

| Tool | Description |
|------|-------------|
| **top_coins** | Top cryptocurrencies by market cap with prices and 24h changes |
| **top_pools** | Best yielding liquidity pools on Base DEXes |
| **top_protocols** | Top DeFi protocols ranked by TVL |
| **swap_quote** | Optimal swap routing with price impact on Base chain |
| **technical_analysis** | RSI, MACD, Bollinger Bands, trend detection, trading signals |
| **defi_yield** | Yield opportunities across lending, LP, and staking protocols |
| **pool_analysis** | Liquidity pool health — TVL, volume, fees, IL risk |
| **token_audit** | Smart contract security audit — honeypot detection, ownership, taxes |
| **whale_moves** | Track large wallet movements for any token |
| **agent_reputation** | ERC-8004 on-chain reputation scores for AI agents |
| **agent_discover** | Discover trusted AI agents by capability |

## Example Queries

| Question | Tools Used |
|----------|-----------|
| "What are the top coins?" | top_coins |
| "Best pools to LP in?" | top_pools |
| "Analyze ETH for me" | technical_analysis |
| "Where to earn yield on USDC?" | defi_yield |
| "Is this token safe? 0xabc..." | token_audit |
| "Whale activity on VIRTUAL" | whale_moves |
| "Compare ETH and BTC correlation" | correlation_matrix |
| "Get me a swap quote: 1 ETH to USDC" | swap_quote |

## How It Works

The skill calls Silverback's `/api/v1/chat` endpoint with your API key. The AI agent:
1. Understands your question
2. Selects the right intelligence tools
3. Fetches real-time on-chain data (CoinGecko, DexScreener, Base chain)
4. Returns a natural language response with data

See `references/endpoints.md` for the full API reference including all 16 direct endpoints.
