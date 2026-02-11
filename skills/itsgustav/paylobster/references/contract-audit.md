# Smart Contract Audit Methodology — PayLobster

## Phase 1: Static Analysis

### Read Contract ABIs
```bash
# Extract function signatures from contracts-v3.ts
grep -E "function|event|error" ~/Projects/paylobster/lib/contracts-v3.ts
```

### Check Contract Verification
```bash
# Verify each contract on BaseScan
for addr in 0xA174ee274F870631B3c330a85EBCad74120BE662 \
            0x02bb4132a86134684976E2a52E43D59D89E64b29 \
            0xD9241Ce8a721Ef5fcCAc5A11983addC526eC80E1 \
            0x49EdEe04c78B7FeD5248A20706c7a6c540748806; do
  echo "Checking $addr..."
  cast etherscan-source $addr --chain base 2>&1 | head -5
done
```

### Storage Layout Analysis
```bash
# Check owner slots
cast storage 0x49EdEe04c78B7FeD5248A20706c7a6c540748806 0 --rpc-url https://mainnet.base.org

# Check total supply of identity NFTs
cast call 0xA174ee274F870631B3c330a85EBCad74120BE662 "totalSupply()" --rpc-url https://mainnet.base.org
```

## Phase 2: Functional Testing

### Identity Contract
```bash
# Check if agent is registered
cast call 0xA174ee274F870631B3c330a85EBCad74120BE662 "ownerOf(uint256)" 1 --rpc-url https://mainnet.base.org

# Get agent metadata
cast call 0xA174ee274F870631B3c330a85EBCad74120BE662 "tokenURI(uint256)" 1 --rpc-url https://mainnet.base.org
```

### Reputation Contract
```bash
# Get trust score for an agent
cast call 0x02bb4132a86134684976E2a52E43D59D89E64b29 "getScore(uint256)" 1 --rpc-url https://mainnet.base.org
```

### Credit Contract
```bash
# Get LOBSTER score
cast call 0xD9241Ce8a721Ef5fcCAc5A11983addC526eC80E1 "getScore(uint256)" 1 --rpc-url https://mainnet.base.org

# Get credit limit
cast call 0xD9241Ce8a721Ef5fcCAc5A11983addC526eC80E1 "getCreditLimit(uint256)" 1 --rpc-url https://mainnet.base.org
```

### Escrow Contract
```bash
# Check escrow owner
cast call 0x49EdEe04c78B7FeD5248A20706c7a6c540748806 "owner()" --rpc-url https://mainnet.base.org

# List active escrows (check events)
cast logs --from-block 0 --address 0x49EdEe04c78B7FeD5248A20706c7a6c540748806 --rpc-url https://mainnet.base.org | head -20
```

## Phase 3: Adversarial Testing

### With Anvil (Local Fork)
```bash
# Fork Base mainnet
anvil --fork-url https://mainnet.base.org --fork-block-number latest

# In another terminal, test adversarial scenarios:

# Try to register agent with existing name
cast send 0xA174ee274F870631B3c330a85EBCad74120BE662 \
  "registerAgent(string,string)" "PayLobster" "ipfs://fake" \
  --rpc-url http://localhost:8545 --private-key <test_key>

# Try to release escrow as non-participant
cast send 0x49EdEe04c78B7FeD5248A20706c7a6c540748806 \
  "release(uint256)" 1 \
  --rpc-url http://localhost:8545 --private-key <attacker_key>

# Try to update another agent's score
cast send 0x02bb4132a86134684976E2a52E43D59D89E64b29 \
  "updateScore(uint256,uint256)" 1 999 \
  --rpc-url http://localhost:8545 --private-key <attacker_key>
```

## Phase 4: Gas & Optimization
```bash
# Estimate gas for common operations
cast estimate 0xA174ee274F870631B3c330a85EBCad74120BE662 \
  "registerAgent(string,string)" "TestAgent" "ipfs://test" \
  --rpc-url https://mainnet.base.org --from 0x0000000000000000000000000000000000000001

# Check USDC transfer gas on Base (should be ~65k)
cast estimate 0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913 \
  "transfer(address,uint256)" 0x0000000000000000000000000000000000000001 1000000 \
  --rpc-url https://mainnet.base.org --from 0x19D3B7A92295eAa3Cf81C2538cbB68d58E34b436
```

## Report Template

```markdown
## Finding: [Title]
**Severity:** Critical / High / Medium / Low / Info
**Location:** [file:line or contract:function]
**Description:** [What the issue is]
**Impact:** [What an attacker could do]
**Reproduction:** [Steps to reproduce]
**Recommendation:** [How to fix]
```
