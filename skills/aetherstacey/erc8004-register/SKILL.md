# ERC-8004 Registration Skill

Register, update, and validate agents on-chain via the ERC-8004 Identity Registry.

## Commands

### register
Register a new agent on-chain.

```bash
python scripts/register.py register --name "AgentName" --description "Description" [--image URL] [--chain base]
```

**Process:**
1. Calls `register()` to mint an agent NFT and get agentId
2. Calls `setAgentURI()` with full compliant metadata including the agentId in registrations[]

**Options:**
- `--name` (required): Agent name
- `--description` (required): Agent description
- `--image`: Image URL (must be https://)
- `--chain`: Blockchain (base, ethereum, polygon, monad, bnb). Default: base

### update
Update an existing agent's metadata.

```bash
python scripts/register.py update <agentId> [--name NAME] [--description DESC] [--image URL] [--add-service name=X,endpoint=Y] [--remove-service NAME] [--chain base]
```

Reads current on-chain URI, merges changes, and submits updated metadata.

### info
Display agent information.

```bash
python scripts/register.py info <agentId> [--chain base]
```

Shows owner, decoded metadata, services, and registrations.

### validate
Check registration for common issues.

```bash
python scripts/register.py validate <agentId> [--chain base]
```

**Checks:**
- Missing `type` field
- Local-path images (/home/..., ./, file://)
- Empty name/description
- Missing registrations array
- Unreachable image URLs (HTTP HEAD check)

## Wallet Configuration

Set one of these environment variables:

```bash
export ERC8004_MNEMONIC="your twelve word mnemonic phrase here"
# OR
export ERC8004_PRIVATE_KEY="0x..."
```

## Contract

Identity Registry: `0x8004A169FB4a3325136EB29fA0ceB6D2e539a432` (same on all chains)

## Supported Chains

| Chain    | ID  | Explorer |
|----------|-----|----------|
| Base     | 8453 | basescan.org |
| Ethereum | 1    | etherscan.io |
| Polygon  | 137  | polygonscan.com |
| Monad    | 143  | explorer.monad.xyz |
| BNB      | 56   | bscscan.com |

## Registration JSON Schema

All registrations follow the ERC-8004 spec:

```json
{
  "type": "https://eips.ethereum.org/EIPS/eip-8004#registration-v1",
  "name": "AgentName",
  "description": "Description",
  "image": "https://example.com/image.jpg",
  "services": [],
  "x402Support": false,
  "active": true,
  "registrations": [
    {
      "agentId": 123,
      "agentRegistry": "eip155:8453:0x8004A169FB4a3325136EB29fA0ceB6D2e539a432"
    }
  ],
  "supportedTrust": ["reputation"]
}
```

## Dependencies

```bash
pip install web3 eth-account
```

## Examples

Register an agent:
```bash
python scripts/register.py register \
  --name "TradingBot" \
  --description "Automated DeFi trading agent" \
  --image "https://example.com/bot.png" \
  --chain base
```

Update description:
```bash
python scripts/register.py update 42 --description "Updated trading bot v2"
```

Add a service endpoint:
```bash
python scripts/register.py update 42 --add-service "name=api,endpoint=https://api.mybot.com"
```

Check for issues:
```bash
python scripts/register.py validate 42
```

## Related

- **erc8004-reputation**: Rate agents and check trust scores
