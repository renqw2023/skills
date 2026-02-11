import fs from 'fs';
import { DATA_DIR, STATE_PATH } from './config.js';
import { appendEvent, nowIso } from './ledger.js';

// wir importieren DEIN Skill-Modul
import {
  getMarket,
  getMarketPrices,
  getPosition,
  getUsdcBalance,
  calculateTradeCost,
  buildOrderTransaction,
  signTx,
  submitOrderTransaction,
} from './skill.js';

function ensureDir(p) {
  if (!fs.existsSync(p)) fs.mkdirSync(p, { recursive: true });
}

function atomicWriteJson(filePath, obj) {
  const tmp = `${filePath}.tmp`;
  fs.writeFileSync(tmp, JSON.stringify(obj, null, 2), 'utf8');
  fs.renameSync(tmp, filePath);
}

export function loadState() {
  ensureDir(DATA_DIR);
  if (!fs.existsSync(STATE_PATH)) return null;
  return JSON.parse(fs.readFileSync(STATE_PATH, 'utf8'));
}

export function saveState(state) {
  ensureDir(DATA_DIR);
  atomicWriteJson(STATE_PATH, state);
}

/**
 * Initialize if missing.
 */
export function ensureState(walletAddress) {
  let st = loadState();
  if (!st) {
    st = {
      version: 1,
      createdAt: nowIso(),
      walletAddress,
      // last known NAV in USDC
      lastNav: null,
      // timeseries of NAV snapshots
      navSeries: [], // [{ts, nav, usdc, positionsValue}]
      // daily PnL aggregation (optional simple)
      daily: {}, // { 'YYYY-MM-DD': { navOpen, navClose, pnl } }
      // positions: per market, per answer
      positions: {}, // { marketId: { shares: [..], lastPrices: [..], lastValue: number } }
      // risk / controls
      risk: {
        maxCostUsdc: 5,
        cooldownSec: 0,
        maxTradesPerDay: 20,
      },
      // runtime counters
      stats: {
        tradesTotal: 0,
        tradesToday: 0,
        lastTradeTs: null,
        lastSnapshotTs: null,
        lastError: null,
      },
    };
    saveState(st);
  } else if (walletAddress && st.walletAddress !== walletAddress) {
    // don't silently swap wallets
    throw new Error(`State walletAddress mismatch: state=${st.walletAddress} vs provided=${walletAddress}`);
  }
  if (!st.risk) {
    st.risk = { maxCostUsdc: 5, cooldownSec: 0, maxTradesPerDay: 20 };
  } else {
    if (typeof st.risk.cooldownSec !== 'number') st.risk.cooldownSec = 0;
    if (typeof st.risk.maxCostUsdc !== 'number') st.risk.maxCostUsdc = 5;
    if (typeof st.risk.maxTradesPerDay !== 'number') st.risk.maxTradesPerDay = 20;
  }
  return st;
}

/**
 * Parse your API position response into a canonical structure.
 * Your API currently returns JSON; we try to be defensive.
 */
function parsePosition(posJson) {
  // Expected: something that includes usdcBalance and lpBalances
  // You'll adapt keys if your API uses different names.
  // We'll try multiple paths:
  const data = posJson?.data ?? posJson;

  const usdc = data?.usdc_balance ?? data?.usdcBalance ?? data?.usdc ?? null;

  // lp_balances as array
  const lpBalances =
    data?.lp_balances ??
    data?.lpBalances ??
    data?.lp ?? null;

  return {
    usdcBalance: (typeof usdc === 'number') ? usdc : null,
    lpBalances: Array.isArray(lpBalances) ? lpBalances.map(x => Number(x)) : null,
  };
}

/**
 * Parse prices into array of {answer, price}
 */
function parsePrices(pricesJson) {
  const data = pricesJson?.data ?? pricesJson;
  // your getMarketPrices already returns [{answer, price}] if success
  if (Array.isArray(data)) return data;
  if (Array.isArray(data?.prices)) return data.prices;
  return null;
}

function mapPricesToNumbers(prices) {
  return prices?.map(p => {
    if (typeof p === 'number') return p;
    if (typeof p?.price === 'number') return p.price;
    const asNum = Number(p?.price ?? p);
    return Number.isFinite(asNum) ? asNum : 0;
  });
}

/**
 * Compute mark-to-market value from snapshot.
 * When useImpactPricing=true, we value each market position by simulating a full liquidation
 * using calculateTradeCost (which accounts for price impact). If the API call fails, we
 * fall back to the simple price * shares estimate.
 */
export async function computeNAVFromSnapshot(snapshot, { useImpactPricing = false } = {}) {
  if (snapshot.usdcBalance == null) return null;

  let positionsValue = 0;
  const perMarketValues = {};

  for (const m of snapshot.markets) {
    const shares = Array.isArray(m.lpBalances) ? m.lpBalances.map(Number) : null;
    const prices = Array.isArray(m.prices) ? mapPricesToNumbers(m.prices) : null;

    let baseValue = 0;
    if (shares && prices) {
      const n = Math.min(shares.length, prices.length);
      for (let i = 0; i < n; i++) {
        baseValue += (Number(shares[i]) || 0) * (Number(prices[i]) || 0);
      }
    }

    let marketValue = baseValue;
    let method = 'prices';

    if (useImpactPricing && shares && shares.some(s => Math.abs(s) > 0)) {
      const liquidationDelta = shares.map(s => s ? -s : 0);
      if (liquidationDelta.some(v => v !== 0)) {
        try {
          const costJson = await calculateTradeCost(m.marketId, liquidationDelta);
          const costData = costJson?.data ?? costJson;
          const rawCost = costData?.costUsdc ?? costData?.cost ?? costData?.data?.costUsdc;
          const liquidationCost = typeof rawCost === 'string' ? Number(rawCost) : rawCost;
          if (typeof liquidationCost === 'number' && Number.isFinite(liquidationCost)) {
            // selling shares yields proceeds, so negate the (likely negative) cost
            marketValue = -liquidationCost;
            method = 'impact';
          }
        } catch (err) {
          // swallow errors and keep price-based value
          method = 'prices';
        }
      }
    }

    positionsValue += marketValue;
    perMarketValues[m.marketId] = {
      value: marketValue,
      method,
      baseValue,
    };
  }

  return {
    nav: snapshot.usdcBalance + positionsValue,
    usdc: snapshot.usdcBalance,
    positionsValue,
    marketValues: perMarketValues,
  };
}

/**
 * Take a snapshot for one or multiple markets.
 * This is the key: it produces ground truth for USDC + shares + prices.
 */
export async function recordSnapshot({ marketIds, walletAddress }) {
  const st = ensureState(walletAddress);

  const markets = [];
  for (const marketId of marketIds) {
    // position (your balances)
    const posJson = await getPosition(marketId, walletAddress);
    const pos = parsePosition(posJson);

    // prices
    const prices = await getMarketPrices(marketId); // already normalized in your skill
    const pricesNorm = parsePrices(prices) ?? prices;

    // market meta (answers length, title)
    const marketJson = await getMarket(marketId);
    const marketData = marketJson?.data ?? marketJson;
    const title = marketData?.title ?? marketData?.account?.title ?? null;
    const answerTitles = Array.isArray(marketData?.answers)
      ? marketData.answers.map((ans, idx) => ans?.title ?? `Answer ${idx}`)
      : null;

    markets.push({
      marketId,
      title,
      lpBalances: pos.lpBalances,
      prices: pricesNorm,
      answerTitles,
    });
  }

  // Pull USDC balance directly from chain using the USDC mint.
  const usdcBalance = await getUsdcBalance(walletAddress);

  const snapshot = {
    ts: nowIso(),
    walletAddress,
    usdcBalance,
    markets,
  };

  const navInfo = await computeNAVFromSnapshot(snapshot, { useImpactPricing: true });

  appendEvent('snapshot', { snapshot, navInfo }, { walletAddress, marketIds });

  // update state
  if (navInfo?.nav != null) {
    st.stats.lastSnapshotTs = snapshot.ts;
    st.navSeries.push({ ts: snapshot.ts, ...navInfo });

    st.lastNav = navInfo.nav;

    // daily aggregation
    const day = snapshot.ts.slice(0, 10);
    const d = st.daily[day] ?? { navOpen: navInfo.nav, navClose: navInfo.nav, pnl: 0 };
    d.navClose = navInfo.nav;
    d.pnl = d.navClose - d.navOpen;
    st.daily[day] = d;

    // update per-market position cache
    for (const m of markets) {
      const pricesNum = mapPricesToNumbers(m.prices) ?? [];
      const shares = m.lpBalances?.map(Number) ?? null;
      const computed = navInfo.marketValues?.[m.marketId];
      let fallbackValue = 0;
      if (shares && pricesNum.length) {
        const n = Math.min(shares.length, pricesNum.length);
        for (let i = 0; i < n; i++) fallbackValue += shares[i] * pricesNum[i];
      }
      const value = computed?.value ?? fallbackValue;

      const prevEntry = st.positions[m.marketId] ?? {};

      st.positions[m.marketId] = {
        title: m.title,
        shares,
        lastPrices: pricesNum,
        prevPrices: prevEntry.lastPrices ?? null,
        answerTitles: m.answerTitles ?? prevEntry.answerTitles ?? null,
        lastValue: value,
        valuationMethod: computed?.method ?? 'prices',
        lastTs: snapshot.ts,
      };
    }

    // simple tradesToday reset logic
    const lastTradeDay = st.stats.lastTradeTs ? st.stats.lastTradeTs.slice(0, 10) : null;
    if (lastTradeDay && lastTradeDay !== day) st.stats.tradesToday = 0;
  }

  saveState(st);
  return { snapshot, navInfo };
}

/**
 * Record an intent (what you planned, expected cost, rationale)
 */
export function recordTradeIntent({ walletAddress, marketId, deltaLpTokens, expectedCost, reason }) {
  appendEvent('order_intent', { walletAddress, marketId, deltaLpTokens, expectedCost, reason }, { walletAddress, marketId });
}

/**
 * High-level “safe trade” wrapper: cost-check, build, sign, submit, snapshot before/after.
 * This gives you ground truth deltas even with impact.
 */
export async function executeTrade({
  walletAddress,
  marketId,
  deltaLpTokens,
  reason = 'autonomous',
  maxCostUsdc = null,
  cooldownSec = null,
  marketsForNav = null, // list of marketIds to include in snapshot (default: [marketId])
}) {
  const st = ensureState(walletAddress);

  // risk checks
  const day = nowIso().slice(0, 10);
  const lastTradeDay = st.stats.lastTradeTs ? st.stats.lastTradeTs.slice(0, 10) : null;
  if (lastTradeDay && lastTradeDay !== day) st.stats.tradesToday = 0;

  const cd = cooldownSec ?? st.risk.cooldownSec ?? 0;
  if (cd > 0 && st.stats.lastTradeTs) {
    const dt = (Date.now() - Date.parse(st.stats.lastTradeTs)) / 1000;
    if (dt < cd) throw new Error(`Cooldown active: wait ${(cd - dt).toFixed(1)}s`);
  }
  if (st.stats.tradesToday >= st.risk.maxTradesPerDay) {
    throw new Error(`Max trades/day reached: ${st.stats.tradesToday}/${st.risk.maxTradesPerDay}`);
  }

  // snapshot before
  const navMarkets = marketsForNav ?? [marketId];
  const before = await recordSnapshot({ marketIds: navMarkets, walletAddress });

  // expected cost (impact-aware from your API)
  const costJson = await calculateTradeCost(marketId, deltaLpTokens);
  const costData = costJson?.data ?? costJson;
  const expectedCost = costData?.costUsdc ?? costData?.cost ?? costData?.data?.costUsdc ?? null;

  if (maxCostUsdc != null && expectedCost != null && expectedCost > maxCostUsdc) {
    recordTradeIntent({ walletAddress, marketId, deltaLpTokens, expectedCost, reason: `${reason} (blocked: expectedCost>${maxCostUsdc})` });
    throw new Error(`Cost guard: expectedCost=${expectedCost} > maxCostUsdc=${maxCostUsdc}`);
  }

  recordTradeIntent({ walletAddress, marketId, deltaLpTokens, expectedCost, reason });

  // build → sign → submit
  const unsignedTx = await buildOrderTransaction(marketId, walletAddress, deltaLpTokens);
  const signedTx = await signTx(unsignedTx);

  appendEvent('tx_submitted', { walletAddress, marketId, deltaLpTokens }, { walletAddress, marketId });

  const submitRes = await submitOrderTransaction(signedTx);
  appendEvent('tx_result', { walletAddress, marketId, deltaLpTokens, submitRes }, { walletAddress, marketId });

  // snapshot after
  const after = await recordSnapshot({ marketIds: navMarkets, walletAddress });

  // compute realised deltas for this trade (from snapshots)
  // Use the marketId position deltas; plus USDC delta
  const beforePos = before.snapshot.markets.find(m => m.marketId === marketId);
  const afterPos = after.snapshot.markets.find(m => m.marketId === marketId);

  const delta = {
    usdcDelta: (after.snapshot.usdcBalance != null && before.snapshot.usdcBalance != null)
      ? after.snapshot.usdcBalance - before.snapshot.usdcBalance
      : null,
    sharesDelta: null,
  };

  if (beforePos?.lpBalances && afterPos?.lpBalances) {
    const n = Math.min(beforePos.lpBalances.length, afterPos.lpBalances.length);
    delta.sharesDelta = Array.from({ length: n }, (_, i) => Number(afterPos.lpBalances[i]) - Number(beforePos.lpBalances[i]));
  }

  appendEvent('trade_delta', { walletAddress, marketId, delta, expectedCost }, { walletAddress, marketId });

  // update state trade stats
  st.stats.lastTradeTs = nowIso();
  st.stats.tradesTotal += 1;
  st.stats.tradesToday += 1;
  st.stats.lastError = null;
  saveState(st);

  return { submitRes, before, after, delta, expectedCost };
}

/**
 * Convenience: return current derived state.
 */
export function getState(walletAddress) {
  const st = ensureState(walletAddress);
  return st;
}
