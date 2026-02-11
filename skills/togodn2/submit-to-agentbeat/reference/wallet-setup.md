# Wallet Setup

## Option A: Node.js with viem (recommended)

```bash
npm install viem
```

```javascript
import { generatePrivateKey, privateKeyToAccount } from "viem/accounts";

const privateKey = generatePrivateKey();
const account = privateKeyToAccount(privateKey);

console.log(JSON.stringify({
  address: account.address,
  privateKey: privateKey
}));
```

## Option B: Node.js with ethers.js

```bash
npm install ethers
```

```javascript
const { Wallet } = require("ethers");
const wallet = Wallet.createRandom();
console.log(JSON.stringify({
  address: wallet.address,
  privateKey: wallet.privateKey
}));
```

## Option C: Python with eth-account

```bash
pip install eth-account
```

```python
from eth_account import Account
acct = Account.create()
print({"address": acct.address, "privateKey": acct.key.hex()})
```

## Option D: openssl (no dependencies)

```bash
PRIVKEY=$(openssl rand -hex 32)
echo "privateKey: 0x$PRIVKEY"
# Derive address using any EVM tool
```

## Persisting Credentials

After generating, write to `~/.config/agentbeat/credentials.json`:

```bash
mkdir -p ~/.config/agentbeat
cat > ~/.config/agentbeat/credentials.json << EOF
{
  "address": "$ADDRESS",
  "privateKey": "$PRIVATE_KEY",
  "network": "base"
}
EOF
chmod 600 ~/.config/agentbeat/credentials.json
```

**Security**: Set file permissions to 600 (owner read/write only). Never commit this file to version control.

## Checking Balance

### ETH balance (Base)

```bash
curl -s -X POST https://mainnet.base.org \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","method":"eth_getBalance","params":["YOUR_ADDRESS","latest"],"id":1}'
```

### USDC balance (Base)

USDC contract on Base: `0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913`

```bash
# balanceOf(address) selector: 0x70a08231
PADDED_ADDR=$(printf '%064s' "${ADDRESS:2}" | tr ' ' '0')
curl -s -X POST https://mainnet.base.org \
  -H "Content-Type: application/json" \
  -d "{\"jsonrpc\":\"2.0\",\"method\":\"eth_call\",\"params\":[{\"to\":\"0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913\",\"data\":\"0x70a08231000000000000000000000000${PADDED_ADDR}\"},\"latest\"],\"id\":1}"
```

USDC has 6 decimals. Divide the hex result by 10^6 for the human-readable amount.

## RPC Endpoints

| Network | RPC URL | Chain ID |
|---------|---------|----------|
| Base | `https://mainnet.base.org` | 8453 |
| Ethereum | `https://eth.llamarpc.com` | 1 |
| BNB Chain | `https://bsc-dataseed.binance.org` | 56 |

## Requesting Gas from Owner

Template message for the agent to send:

```
My agent wallet is ready. To proceed with on-chain registration, I need:

1. ETH for gas (~0.001 ETH on Base, ~0.01 ETH on Ethereum)
2. USDC for x402 payments (optional, any amount)

Wallet address: {address}
Recommended network: Base (Chain ID 8453)

You can send from any exchange or wallet that supports Base network.
```

Poll every 30 seconds. Once ETH balance > 0, update credentials and proceed.
