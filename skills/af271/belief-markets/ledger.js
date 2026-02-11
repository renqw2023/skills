import fs from 'fs';
import crypto from 'crypto';
import { DATA_DIR, LEDGER_PATH } from './config.js';

function ensureDir(p) {
  if (!fs.existsSync(p)) fs.mkdirSync(p, { recursive: true });
}

export function nowIso() {
  return new Date().toISOString();
}

export function newId(prefix = 'evt') {
  return `${prefix}_${crypto.randomBytes(8).toString('hex')}`;
}

/**
 * Append one event as NDJSON line.
 * Crash-safe: appendFile is atomic per line on Linux in practice for small writes,
 * and even if interrupted you might only get a truncated last line (we handle that in reader).
 */
export function appendEvent(type, payload = {}, meta = {}) {
  ensureDir(DATA_DIR);
  const evt = {
    id: newId(type),
    ts: nowIso(),
    type,
    payload,
    meta,
  };
  fs.appendFileSync(LEDGER_PATH, JSON.stringify(evt) + '\n', 'utf8');
  return evt;
}

/**
 * Read ledger events. For simplicity, reads whole file; fine for early stage.
 * If you later have lots of events, we can add tailing or paging.
 */
export function readLedgerEvents({ sinceTs = null, limit = null } = {}) {
  if (!fs.existsSync(LEDGER_PATH)) return [];
  const raw = fs.readFileSync(LEDGER_PATH, 'utf8');
  const lines = raw.split('\n').filter(Boolean);

  const evts = [];
  for (const line of lines) {
    try {
      const e = JSON.parse(line);
      evts.push(e);
    } catch {
      // ignore truncated/corrupt line at end
    }
  }

  let out = evts;
  if (sinceTs) out = out.filter(e => e.ts >= sinceTs);
  if (limit) out = out.slice(-limit);
  return out;
}
