import path from 'path';
import os from 'os';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

function expandHome(p) {
  if (!p) return p;
  if (p.startsWith('~')) return path.join(os.homedir(), p.slice(1));
  return p;
}

function envPath(name, fallback) {
  return expandHome(process.env[name] ?? fallback);
}

const defaultDataDir = path.join(__dirname, 'data');

export const API_URL = process.env.BELIEF_MARKETS_API_URL ?? 'https://belief-markets-api.fly.dev';
export const DATA_DIR = envPath('BELIEF_MARKETS_DATA_DIR', defaultDataDir);
export const LEDGER_PATH = envPath('BELIEF_MARKETS_LEDGER_PATH', path.join(DATA_DIR, 'ledger.ndjson'));
export const STATE_PATH = envPath('BELIEF_MARKETS_STATE_PATH', path.join(DATA_DIR, 'state.json'));
export const KEYPAIR_PATH = envPath('BELIEF_MARKETS_KEYPAIR_PATH', path.join(os.homedir(), '.config', 'solana', 'phantom_trading.json'));
// USDC Mint Address (devnet)
export const USDC_MINT = process.env.BELIEF_MARKETS_USDC_MINT ?? 'Gh9ZwEmdLJ8DscKNTkTqPbNwLNNBjuSzaG9Vp2KGtKJr';
export const MARKET_ID = process.env.BELIEF_MARKETS_MARKET_ID ?? 'CAU5Dxw7mXJQDZvsTRaHNTg854bHMRj3b9QKjpCsRX3k';
