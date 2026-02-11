// Belief Markets Skill for OpenClaw
// Provides thin interface for autonomous agents to interact with the Belief Markets API

import fetch from 'node-fetch';
import fs from 'fs';
import { Connection, Keypair, PublicKey, Transaction, clusterApiUrl } from '@solana/web3.js';
import { API_URL, KEYPAIR_PATH, USDC_MINT } from './config.js';


// Load keypair from a keypair file path and extract public key and private key in base58
export function loadKeypairFromPath(keypairPath) {
  const keypairData = JSON.parse(fs.readFileSync(keypairPath, 'utf8'));
  const keypair = Keypair.fromSecretKey(Uint8Array.from(keypairData));
  return keypair;
}

export function loadKeypair() {
  return loadKeypairFromPath(KEYPAIR_PATH);
}

// Lookup USDC balance for a wallet address on devnet
export async function getUsdcBalance(walletAddress) {
  const connection = new Connection(clusterApiUrl('devnet'), 'confirmed');
  const owner = new PublicKey(walletAddress);
  const mint = new PublicKey(USDC_MINT);

  const tokenAccounts = await connection.getParsedTokenAccountsByOwner(owner, { mint });
  let total = 0;

  for (const { account } of tokenAccounts.value) {
    const amount = account?.data?.parsed?.info?.tokenAmount;
    if (!amount) continue;
    if (typeof amount.uiAmount === 'number') {
      total += amount.uiAmount;
    } else if (typeof amount.amount === 'string' && typeof amount.decimals === 'number') {
      total += Number(amount.amount) / Math.pow(10, amount.decimals);
    }
  }

  return total;
}


// Build and sign a transaction locally
async function signTransaction(unsignedTxBase64) {
  const keypair = loadKeypair();
  const txBuffer = Buffer.from(unsignedTxBase64, 'base64');
  const transaction = Transaction.from(txBuffer);
  transaction.partialSign(keypair);
  return transaction.serialize({ requireAllSignatures: false }).toString('base64');
}

// Skill functions
export async function getMarkets() {
  const response = await fetch(`${API_URL}/api/markets`);
  return await response.json();
}

export async function getMarket(marketId) {
  const response = await fetch(`${API_URL}/api/markets/${marketId}`);
  return await response.json();
}

export async function getMarketPrices(marketId) {
  const response = await fetch(`${API_URL}/api/markets/${marketId}/prices`);
  const json = await response.json();
  if (json.success) {
    return json.data.prices.map(p => ({ answer: p.answer, price: p.price }));
  } else {
    throw new Error(json.error || 'Failed to fetch market prices');
  }
}

export async function getPosition(marketId, walletAddress) {
  const response = await fetch(`${API_URL}/api/markets/${marketId}/user/${walletAddress}`);
  return await response.json();
}

export async function calculateTradeCost(marketId, deltaLpTokens) {
  const response = await fetch(`${API_URL}/api/markets/${marketId}/calculate-cost`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ deltaLpTokens })
  });
  return await response.json();
}

// Build unsigned create market transaction
export async function buildCreateMarketTransaction(title, answers, walletAddress) {
  const response = await fetch(`${API_URL}/api/create-market/build`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ title, answers, walletAddress })
  });
  const data = await response.json();
  return data.data.transaction;
}

// Submit signed create market transaction
export async function submitCreateMarketTransaction(signedTransaction) {
  const response = await fetch(`${API_URL}/api/create-market/submit`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ signedTransaction })
  });
  return await response.json();
}

// Build unsigned order transaction
export async function buildOrderTransaction(marketId, walletAddress, deltaLpTokens) {
  const response = await fetch(`${API_URL}/api/orders/build`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ marketId, walletAddress, deltaLpTokens })
  });
  const data = await response.json();
  return data.data.transaction;
}

// Submit signed order transaction
export async function submitOrderTransaction(signedTransaction) {
  const response = await fetch(`${API_URL}/api/orders`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ signedTransaction })
  });
  return await response.json();
}


// Export signing function for agent to use
export async function signTx(unsignedTxBase64) {
  return await signTransaction(unsignedTxBase64);
}

// Additional utility functions and error handling can be added as needed
