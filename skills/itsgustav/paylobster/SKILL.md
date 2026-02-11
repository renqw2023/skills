---
name: paylobster-guardian
description: Expert security engineer, debugger, and QA specialist for the Pay Lobster platform. Use when auditing smart contracts, debugging TypeScript/Next.js code, finding security vulnerabilities, reviewing API endpoints, testing escrow/payment flows, analyzing on-chain transactions, hardening authentication, or performing any security/debugging/testing task on the PayLobster codebase. Covers the full stack: Solidity contracts (Base), TypeScript SDK (lib/), Next.js web app (web/), CLI, x402 protocol, ERC-8004 identity, and Firebase auth.
---

# PayLobster Guardian

Expert debugger, security engineer, and QA specialist for the Pay Lobster platform.

## Project Layout

```
~/Projects/paylobster/
├── lib/                    # Core TypeScript SDK
│   ├── agent.ts            # Agent payment logic
│   ├── autonomous.ts       # Trust-gate + spending limits
│   ├── contracts.ts        # V1 contract ABIs
│   ├── contracts-v3.ts     # V3 contract ABIs (current)
│   ├── escrow.ts           # Escrow operations
│   ├── escrow-templates.ts # Escrow template system
│   ├── circle-client.ts    # Circle API integration
│   ├── erc8004/            # ERC-8004 identity + reputation + discovery
│   ├── chains/             # Multi-chain support (Base, Solana)
│   ├── x402.ts             # x402 payment protocol
│   ├── x402-client.ts      # x402 client
│   ├── x402-server.ts      # x402 server middleware
│   ├── commission.ts       # Commission/splits
│   ├── invoices.ts         # Invoice generation
│   ├── subscriptions.ts    # Recurring payments
│   ├── tips.ts             # Tip jar system
│   ├── approvals.ts        # Multi-approver policies
│   ├── notifications.ts    # Webhook/alert system
│   ├── analytics.ts        # Usage analytics
│   ├── contacts.ts         # Address book
│   └── cli.ts              # CLI entrypoint
├── web/                    # Next.js 15 web app
│   └── src/
│       ├── app/            # App Router pages
│       │   ├── api/        # API routes
│       │   ├── auth/       # Auth pages (NextAuth + Firebase + SIWE)
│       │   ├── dashboard/  # Dashboard (analytics, disputes, score, send, etc.)
│       │   ├── docs/       # Documentation
│       │   ├── escrow/     # Escrow flow
│       │   ├── merchant/   # Merchant API
│       │   └── widget/     # Embeddable widget
│       ├── components/     # React components
│       ├── hooks/          # Custom hooks (useContractStats, etc.)
│       └── lib/            # Web utilities
├── base-app/               # PWA mobile app
├── api/                    # Standalone API
├── dist/                   # Compiled SDK
└── SKILL.md                # OpenClaw skill definition
```

## On-Chain Contracts (Base Mainnet)

| Contract | Address | Purpose |
|----------|---------|---------|
| V3 Identity (ERC-721) | `0xA174ee274F870631B3c330a85EBCad74120BE662` | Agent NFT registration |
| V3 Reputation | `0x02bb4132a86134684976E2a52E43D59D89E64b29` | Trust score registry |
| V3 Credit | `0xD9241Ce8a721Ef5fcCAc5A11983addC526eC80E1` | LOBSTER score (300-850) |
| V3 Escrow | `0x49EdEe04c78B7FeD5248A20706c7a6c540748806` | USDC escrow + milestones |
| USDC | `0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913` | Circle USDC on Base |

## Security Audit Checklist

### Smart Contracts
1. Read `lib/contracts-v3.ts` for V3 ABIs — check for reentrancy, access control, integer overflow
2. Verify escrow release logic — only authorized parties can release/dispute
3. Check identity registration — ensure no spoofing of agent NFTs
4. Audit credit score oracle — verify score can't be manipulated
5. Review USDC approval patterns — check for unlimited approvals
6. Verify owner functions on escrow contract (owner: `0xf775f0224A680E2915a066e53A389d0335318b7B`)

### API & Authentication
1. Check `web/src/app/api/` routes for auth middleware — every endpoint must verify session
2. Audit NextAuth + Firebase + SIWE integration in `web/src/app/auth/`
3. Look for exposed API keys or secrets in source code: `grep -r "sk_\|api_key\|secret\|password\|private" --include="*.ts" --include="*.tsx"`
4. Check CORS configuration
5. Verify webhook signature validation (HMAC)
6. Review rate limiting on payment endpoints

### Frontend Security
1. Check for XSS in user-rendered content (agent names, descriptions, metadata)
2. Verify CSP headers in `next.config`
3. Audit wallet connection flow (RainbowKit/wagmi) — ensure no phishing vectors
4. Check for exposed wallet addresses or private data in client bundles
5. Review form validation on payment/escrow creation pages

### SDK & CLI
1. Audit `lib/autonomous.ts` — trust-gate bypass vectors
2. Review spending limit enforcement in `lib/autonomous.ts`
3. Check `lib/circle-client.ts` for proper secret handling
4. Verify x402 payment proofs can't be replayed
5. Audit CLI command injection in `lib/cli.ts`

## Debugging Playbook

### Common Issues

**Build Errors:**
```bash
cd ~/Projects/paylobster/web && npm run build 2>&1 | head -50
```

**Type Errors:**
```bash
cd ~/Projects/paylobster/web && npx tsc --noEmit 2>&1 | head -50
```

**Runtime Errors — Check browser console:**
Look in `web/src/app/` for the failing route, trace component tree.

**Contract Interaction Failures:**
```bash
# Check contract state on Base
cast call <contract_address> "functionName(args)" --rpc-url https://mainnet.base.org
```

**Auth Flow Debugging:**
1. Check `web/src/app/providers.tsx` for session provider config
2. Check `web/src/app/wallet-providers.tsx` for RainbowKit config
3. Verify Firebase config in environment variables
4. Check NextAuth callbacks in API route

### Performance
```bash
# Bundle analysis
cd ~/Projects/paylobster/web && ANALYZE=true npm run build

# Check for large dependencies
du -sh web/node_modules/* | sort -rh | head -20
```

## Testing Strategy

### Unit Tests
- Test each `lib/*.ts` module in isolation
- Mock contract calls with ethers/viem test utilities
- Test edge cases: zero amounts, max uint256, empty strings, invalid addresses

### Integration Tests
- Test escrow full lifecycle: create → fund → milestone → release
- Test identity: register → update metadata → transfer
- Test credit score: initial score → transactions → score update
- Test x402: request → 402 response → payment → retry → success

### Security Tests
- Fuzz inputs on all API endpoints
- Test auth bypass attempts (missing token, expired token, wrong role)
- Test contract with adversarial inputs via Foundry
- Check for front-running vulnerabilities on escrow release

### On-Chain Verification
```bash
# Verify contract source on BaseScan
cast etherscan-source <address> --chain base

# Check contract storage slots
cast storage <address> <slot> --rpc-url https://mainnet.base.org

# Simulate transactions
cast call <address> "function(args)" --from <sender> --rpc-url https://mainnet.base.org
```

## Quick Reference

### Key Files to Audit First
1. `lib/contracts-v3.ts` — All V3 contract ABIs and interaction logic
2. `lib/autonomous.ts` — Trust-gate and spending limit enforcement
3. `lib/escrow.ts` — Payment holding and release logic
4. `web/src/app/api/` — All server-side API routes
5. `web/src/app/auth/` — Authentication flow
6. `lib/x402-server.ts` — Payment protocol middleware

### Tools
- **Foundry** (`forge`, `cast`, `anvil`) — Contract testing and interaction
- **BaseScan** — `https://basescan.org/address/<addr>`
- **Next.js DevTools** — Built-in with `npm run dev`
- **TypeScript** — `npx tsc --noEmit` for type checking

### For Deeper Analysis
See `references/vulnerability-patterns.md` for common Web3 + Next.js vulnerability patterns.
See `references/contract-audit.md` for detailed smart contract audit methodology.
