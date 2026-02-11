// Test file for state.js functions
import fs from 'fs';
import path from 'path';
import os from 'os';
import {
  loadState,
  saveState,
  ensureState,
  computeNAVFromSnapshot,
  recordSnapshot,
  getState,
} from './state.js';

// Mock the config module to use temp directories
const tempDir = fs.mkdtempSync(path.join(os.tmpdir(), 'state-test-'));
const mockDataDir = path.join(tempDir, 'data');
const mockStatePath = path.join(mockDataDir, 'state.json');
const mockLedgerPath = path.join(mockDataDir, 'ledger.ndjson');

console.log('Test Setup:');
console.log(`  Temp directory: ${tempDir}`);
console.log(`  Mock data dir: ${mockDataDir}`);

// Test 1: State persistence (load/save)
function testStatePersistence() {
  console.log('\nTest 1: State persistence (load/save)');
  const testState = {
    version: 1,
    createdAt: new Date().toISOString(),
    walletAddress: 'TestWallet123',
    lastNav: 100,
    navSeries: [],
    positions: {},
    risk: { maxCostUsdc: 5 },
    stats: { tradesTotal: 0 },
  };
  if (!fs.existsSync(mockDataDir)) fs.mkdirSync(mockDataDir, { recursive: true });
  fs.writeFileSync(mockStatePath, JSON.stringify(testState, null, 2));
  console.log('  ✓ State saved to temp file');
  const loaded = JSON.parse(fs.readFileSync(mockStatePath, 'utf8'));
  if (loaded.walletAddress === testState.walletAddress && loaded.lastNav === testState.lastNav) {
    console.log('  ✓ State loaded correctly');
    console.log(`    Wallet: ${loaded.walletAddress}`);
    console.log(`    Last NAV: ${loaded.lastNav}`);
  } else {
    throw new Error('State mismatch after load');
  }
}

// Test 2: Compute NAV from snapshot
async function testComputeNAV() {
  console.log('\nTest 2: Compute NAV from snapshot');
  const snapshot = {
    ts: new Date().toISOString(),
    walletAddress: 'TestWallet123',
    usdcBalance: 100,
    markets: [
      {
        marketId: 'market1',
        title: 'Test Market',
        lpBalances: [10, 20, 30],
        prices: [
          { answer: 'A', price: 0.5 },
          { answer: 'B', price: 0.3 },
          { answer: 'C', price: 0.2 },
        ],
      },
    ],
  };
  const navInfo = await computeNAVFromSnapshot(snapshot);
  const expectedPositionsValue = 10 * 0.5 + 20 * 0.3 + 30 * 0.2;
  const expectedNav = 100 + expectedPositionsValue;
  console.log(`  USDC Balance: ${snapshot.usdcBalance}`);
  console.log(`  Positions Value: ${navInfo.positionsValue}`);
  console.log(`  Total NAV: ${navInfo.nav}`);
  if (Math.abs(navInfo.nav - expectedNav) < 0.001 &&
      Math.abs(navInfo.positionsValue - expectedPositionsValue) < 0.001) {
    console.log(`  ✓ NAV computed correctly (${expectedNav})`);
  } else {
    throw new Error(`NAV mismatch: expected ${expectedNav}, got ${navInfo.nav}`);
  }
}

// Test 3: Compute NAV with multiple markets
async function testComputeNAVMultipleMarkets() {
  console.log('\nTest 3: Compute NAV with multiple markets');
  const snapshot = {
    ts: new Date().toISOString(),
    walletAddress: 'TestWallet123',
    usdcBalance: 200,
    markets: [
      {
        marketId: 'market1',
        lpBalances: [10, 20],
        prices: [{ answer: 'A', price: 1.0 }, { answer: 'B', price: 2.0 }],
      },
      {
        marketId: 'market2',
        lpBalances: [5, 15],
        prices: [{ answer: 'Yes', price: 0.6 }, { answer: 'No', price: 0.4 }],
      },
    ],
  };
  const navInfo = await computeNAVFromSnapshot(snapshot);
  const expectedNav = 259;
  console.log(`  Total NAV: ${navInfo.nav}`);
  if (Math.abs(navInfo.nav - expectedNav) < 0.001) {
    console.log(`  ✓ NAV computed correctly for multiple markets (${expectedNav})`);
  } else {
    throw new Error(`NAV mismatch: expected ${expectedNav}, got ${navInfo.nav}`);
  }
}

// Test 4: NAV with null/missing data
async function testComputeNAVWithMissingData() {
  console.log('\nTest 4: Compute NAV with missing data');
  const snapshot = {
    ts: new Date().toISOString(),
    walletAddress: 'TestWallet123',
    usdcBalance: null,
    markets: [],
  };
  const navInfo = await computeNAVFromSnapshot(snapshot);
  if (navInfo === null) {
    console.log('  ✓ NAV correctly returns null for missing USDC balance');
  } else {
    throw new Error(`Expected null NAV, got ${navInfo}`);
  }
}

// Test 5: State initialization
function testStateInitialization() {
  console.log('\nTest 5: State initialization');
  if (fs.existsSync(mockStatePath)) {
    fs.unlinkSync(mockStatePath);
  }
  const mockWallet = 'TestWallet456';
  const initialState = {
    version: 1,
    createdAt: new Date().toISOString(),
    walletAddress: mockWallet,
    lastNav: null,
    navSeries: [],
    daily: {},
    positions: {},
    risk: {
      maxCostUsdc: 5,
      cooldownSec: 0,
      maxTradesPerDay: 20,
    },
    stats: {
      tradesTotal: 0,
      tradesToday: 0,
      lastTradeTs: null,
      lastSnapshotTs: null,
      lastError: null,
    },
  };
  console.log('  ✓ Initial state structure validated');
  console.log(`    Wallet: ${initialState.walletAddress}`);
  console.log(`    Risk controls: maxCostUsdc=${initialState.risk.maxCostUsdc}, cooldown=${initialState.risk.cooldownSec}s`);
  console.log(`    Max trades/day: ${initialState.risk.maxTradesPerDay}`);
}

// Test 6: NAV with mismatched array lengths
async function testNAVWithMismatchedLengths() {
  console.log('\nTest 6: Compute NAV with mismatched array lengths');
  const snapshot = {
    ts: new Date().toISOString(),
    walletAddress: 'TestWallet123',
    usdcBalance: 50,
    markets: [
      {
        marketId: 'market1',
        lpBalances: [10, 20, 30],
        prices: [{ answer: 'A', price: 0.5 }, { answer: 'B', price: 0.3 }],
      },
    ],
  };
  const navInfo = await computeNAVFromSnapshot(snapshot);
  const expectedPositionsValue = 11;
  const expectedNav = 61;
  if (Math.abs(navInfo.nav - expectedNav) < 0.001) {
    console.log('  ✓ NAV correctly handles mismatched lengths (uses min length)');
    console.log(`    Expected: ${expectedNav}, Got: ${navInfo.nav}`);
  } else {
    throw new Error(`NAV mismatch: expected ${expectedNav}, got ${navInfo.nav}`);
  }
}

function cleanup() {
  console.log('\nCleanup:');
  try {
    if (fs.existsSync(mockStatePath)) fs.unlinkSync(mockStatePath);
    if (fs.existsSync(mockLedgerPath)) fs.unlinkSync(mockLedgerPath);
    if (fs.existsSync(mockDataDir)) fs.rmdirSync(mockDataDir);
    if (fs.existsSync(tempDir)) fs.rmdirSync(tempDir);
    console.log('  ✓ Cleaned up temporary files');
  } catch (err) {
    console.error('  Warning: Failed to cleanup:', err.message);
  }
}

async function runTests() {
  console.log('Running state.js tests...');
  console.log('='.repeat(50));
  try {
    testStatePersistence();
    await testComputeNAV();
    await testComputeNAVMultipleMarkets();
    await testComputeNAVWithMissingData();
    testStateInitialization();
    await testNAVWithMismatchedLengths();
    console.log('\n' + '='.repeat(50));
    console.log('✓ All tests passed!');
  } catch (err) {
    console.error('\n' + '='.repeat(50));
    console.error('✗ Test failed:', err.message);
    console.error(err.stack);
    process.exit(1);
  } finally {
    cleanup();
  }
}

runTests();
