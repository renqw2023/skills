# Minara + Circle Wallet Integration Examples

Both examples assume circle-wallet skill is installed and configured via `circle-wallet setup`.

## Shared setup — load Circle config and create SDK client

```typescript
import { initiateDeveloperControlledWalletsClient } from "@circle-fin/developer-controlled-wallets";
import * as fs from "fs";

// Load credentials managed by circle-wallet skill
const config = JSON.parse(
  fs.readFileSync(`${process.env.HOME}/.openclaw/circle-wallet/config.json`, "utf-8")
);

const circleClient = initiateDeveloperControlledWalletsClient({
  apiKey: config.apiKey,
  entitySecret: config.entitySecret,
});
```

Get wallet address (use existing wallet or create one):

```bash
# List existing wallets
circle-wallet list

# Or create a new one
circle-wallet create "Trading Wallet" --chain BASE
```

---

## Example 1

**Spot Swap: Minara Intent → Circle Execution**

User: *"swap 500 USDC to ETH on Base"*

### 1. Parse intent (Minara)

```typescript
const swapTx = await fetch("https://api.minara.ai/v1/developer/intent-to-swap-tx", {
  method: "POST",
  headers: {
    "Authorization": `Bearer ${process.env.MINARA_API_KEY}`,
    "Content-Type": "application/json",
  },
  body: JSON.stringify({
    intent: "swap 500 USDC to ETH",
    walletAddress: walletAddress,   // from circle-wallet list
    chain: "base",
  }),
}).then((r) => r.json());

// swapTx.transaction = {
//   chain, inputTokenAddress, outputTokenAddress,
//   amount, slippagePercent, ...
// }
```

### 2a. Simple USDC transfer — use CLI

```bash
circle-wallet send 0xRecipientAddress 500 --from 0xWalletAddress
```

### 2b. DEX swap — use Circle API directly

Build calldata from Minara's swap params via a DEX aggregator (OKX DEX API, 1inch, Uniswap), then execute:

```typescript
const dexCalldata = await buildDexCalldata(swapTx.transaction);

// Circle contractExecution requires raw API call (not in SDK)
const res = await fetch(
  "https://api.circle.com/v1/w3s/developer/transactions/contractExecution",
  {
    method: "POST",
    headers: {
      "Authorization": `Bearer ${config.apiKey}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      idempotencyKey: crypto.randomUUID(),
      entitySecretCiphertext: await generateCiphertext(config.entitySecret, config.apiKey),
      walletId: walletId,
      contractAddress: dexCalldata.routerAddress,
      callData: dexCalldata.data,
      feeLevel: "MEDIUM",
    }),
  },
).then((r) => r.json());
```

> For `entitySecretCiphertext` generation in raw API calls, use the Circle SDK's `forgeEntitySecretCiphertext` utility or encrypt the entity secret with Circle's RSA public key. See [Circle entity secret docs](https://developers.circle.com/w3s/entity-secret-management).

### Flow

```
Minara intent-to-swap-tx → { tokens, amount, slippage }
  → DEX aggregator → { routerAddress, callData }
  → Circle contractExecution → tx on-chain
```

---

## Example 2

**Perp Trading: Minara Strategy → Hyperliquid Order via Circle Signing**

User: *"open a long ETH position, $1000 margin, 10x leverage"*

Hyperliquid is a permissionless perp DEX — no API key. Orders use EIP-712 signatures.

### 1. Get strategy (Minara)

```typescript
const strategy = await fetch("https://api.minara.ai/v1/developer/perp-trading-suggestion", {
  method: "POST",
  headers: {
    "Authorization": `Bearer ${process.env.MINARA_API_KEY}`,
    "Content-Type": "application/json",
  },
  body: JSON.stringify({
    symbol: "ETH",
    style: "scalping",
    marginUSD: 1000,
    leverage: 10,
  }),
}).then((r) => r.json());

// { entryPrice, side, stopLossPrice, takeProfitPrice, confidence, reasons, risks }
```

Confirm with user before proceeding — show strategy, confidence, and risks.

### 2. Map to Hyperliquid order

```typescript
// Asset indices: BTC=0, ETH=1, SOL=2, ...
// Full list: https://hyperliquid.gitbook.io/hyperliquid-docs/for-developers/api/asset-ids
const ASSET_INDEX: Record<string, number> = { BTC: 0, ETH: 1, SOL: 2 };

const assetIndex = ASSET_INDEX[strategy.symbol ?? "ETH"];
const isBuy = strategy.side === "long";
const price = strategy.entryPrice;
const size = String(strategy.marginUSD * strategy.leverage / parseFloat(price));
const nonce = Date.now();

const action = {
  type: "order",
  orders: [{
    a: assetIndex,
    b: isBuy,
    p: price,
    s: size,
    r: false,
    t: { limit: { tif: "Gtc" } },
  }],
  grouping: "na",
};
```

### 3. Build EIP-712 typed data

Use the [Hyperliquid SDK](https://github.com/hyperliquid-dex/hyperliquid-python-sdk) signing utilities for correct msgpack encoding and action hashing. Simplified illustration:

```typescript
const typedData = {
  types: {
    EIP712Domain: [
      { name: "name", type: "string" },
      { name: "version", type: "string" },
      { name: "chainId", type: "uint256" },
    ],
    "HyperliquidTransaction:Order": [
      { name: "action", type: "bytes" },
      { name: "nonce", type: "uint64" },
      { name: "vaultAddress", type: "address" },
    ],
  },
  domain: { name: "HyperliquidSignTransaction", version: "1", chainId: 42161 },
  primaryType: "HyperliquidTransaction:Order",
  message: {
    action: actionHash,  // msgpack hash — use SDK
    nonce: nonce,
    vaultAddress: "0x0000000000000000000000000000000000000000",
  },
};
```

### 4. Sign with Circle (EIP-712)

```typescript
// signTypedData requires raw API call (not in circle-wallet CLI)
const signRes = await fetch("https://api.circle.com/v1/w3s/developer/sign/typedData", {
  method: "POST",
  headers: {
    "Authorization": `Bearer ${config.apiKey}`,
    "Content-Type": "application/json",
  },
  body: JSON.stringify({
    data: JSON.stringify(typedData),
    entitySecretCiphertext: await generateCiphertext(config.entitySecret, config.apiKey),
    walletId: walletId,
    memo: `Hyperliquid ${strategy.side} ${strategy.symbol}`,
  }),
}).then((r) => r.json());

const signature = signRes.data.signature;
```

### 5. Submit to Hyperliquid

```typescript
const hlRes = await fetch("https://api.hyperliquid.xyz/exchange", {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({ action, nonce, signature }),
});
// Success: { status: "ok", response: { type: "order", data: { statuses: [...] } } }
// Error:   { status: "err", response: "..." }
```

### 6. (Optional) TP/SL orders

```typescript
const tpslAction = {
  type: "order",
  orders: [
    {
      a: assetIndex, b: !isBuy, p: strategy.takeProfitPrice, s: size,
      r: true, t: { trigger: { isMarket: true, triggerPx: strategy.takeProfitPrice, tpsl: "tp" } },
    },
    {
      a: assetIndex, b: !isBuy, p: strategy.stopLossPrice, s: size,
      r: true, t: { trigger: { isMarket: true, triggerPx: strategy.stopLossPrice, tpsl: "sl" } },
    },
  ],
  grouping: "positionTpsl",
};
// Sign and submit same as steps 3–5
```

### 7. (Optional) Set leverage

```typescript
const leverageAction = {
  type: "updateLeverage",
  asset: assetIndex,
  isCross: true,
  leverage: strategy.leverage ?? 10,
};
// Sign and submit before placing the main order
```

### Flow

```
Minara perp-trading-suggestion → { side, entryPrice, SL, TP, confidence }
  → Map to Hyperliquid order action
  → Build EIP-712 typed data (Hyperliquid SDK)
  → Circle signTypedData (raw API, credentials from ~/.openclaw/circle-wallet/config.json)
  → POST https://api.hyperliquid.xyz/exchange → order placed (no API key)
```
