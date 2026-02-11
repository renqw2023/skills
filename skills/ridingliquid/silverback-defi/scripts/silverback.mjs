#!/usr/bin/env node
/**
 * Silverback DeFi Intelligence — x402 paid skill script
 * Pays per request with USDC on Base via x402 micropayments.
 *
 * Usage: node silverback.mjs "What are the top coins?"
 * Requires: node 18+, SILVERBACK_PRIVATE_KEY env var (or config.json fallback)
 *
 * Security: This script ONLY calls x402.silverbackdefi.app/api/v1/chat.
 * Maximum payment per call is $0.05 USDC (set by x402 server, not this script).
 * The x402 protocol only signs EIP-3009 transferWithAuthorization for the
 * exact amount specified in the server's 402 response — it cannot sign
 * arbitrary transactions.
 */

import { readFileSync, existsSync } from 'fs';
import { dirname, join } from 'path';
import { fileURLToPath } from 'url';
import { createWalletClient, http } from 'viem';
import { privateKeyToAccount } from 'viem/accounts';
import { base } from 'viem/chains';

const __dirname = dirname(fileURLToPath(import.meta.url));
const CONFIG_PATH = join(__dirname, '..', 'config.json');
const API_BASE = 'https://x402.silverbackdefi.app';
const ENDPOINT = '/api/v1/chat';
const MAX_PRICE_USDC = 0.05;

// Read private key: prefer env var, fall back to config.json
let privateKey = process.env.SILVERBACK_PRIVATE_KEY;

if (!privateKey) {
  if (existsSync(CONFIG_PATH)) {
    try {
      const config = JSON.parse(readFileSync(CONFIG_PATH, 'utf-8'));
      privateKey = config.private_key;
    } catch {
      // config.json exists but can't be parsed
    }
  }
}

if (!privateKey || privateKey === '0x_YOUR_WALLET_PRIVATE_KEY_HERE') {
  console.error('Error: No wallet private key found.');
  console.error('Set SILVERBACK_PRIVATE_KEY env var, or add to config.json:');
  console.error('  {"private_key": "0xYOUR_KEY"}');
  console.error('');
  console.error('IMPORTANT: Use a dedicated wallet with minimal USDC.');
  console.error('Do NOT use your main wallet.');
  process.exit(1);
}

// Get prompt from args
const prompt = process.argv.slice(2).join(' ');
if (!prompt) {
  console.error('Usage: node silverback.mjs "your question here"');
  process.exit(1);
}

// Dynamic import of @x402/fetch (installed via npm install)
let wrapFetch;
try {
  const x402Fetch = await import('@x402/fetch');
  wrapFetch = x402Fetch.wrapFetchWithPayment || x402Fetch.default?.wrapFetchWithPayment;
} catch {
  console.error('Error: @x402/fetch not installed. Run: npm install');
  process.exit(1);
}

// Set up wallet for x402 payments
const account = privateKeyToAccount(privateKey);
const walletClient = createWalletClient({
  account,
  chain: base,
  transport: http(),
});

console.error(`Wallet: ${account.address}`);
console.error(`Endpoint: ${ENDPOINT} (max $${MAX_PRICE_USDC} USDC per call)`);
console.error('');

// Wrap fetch with x402 payment capabilities
const x402fetch = wrapFetch(fetch, walletClient);

try {
  const response = await x402fetch(`${API_BASE}${ENDPOINT}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ message: prompt }),
  });

  if (!response.ok) {
    const text = await response.text();
    console.error(`Error: API returned HTTP ${response.status}`);
    try {
      const err = JSON.parse(text);
      console.error(err.error || err.message || text);
    } catch {
      console.error(text);
    }
    process.exit(1);
  }

  const data = await response.json();
  console.log(data?.data?.response || data?.response || JSON.stringify(data, null, 2));
} catch (err) {
  console.error(`Error: ${err.message}`);
  process.exit(1);
}
