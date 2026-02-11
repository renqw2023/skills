import { loadKeypair, getUsdcBalance, getMarket, getPosition, getMarketPrices } from './skill.js';
import { MARKET_ID } from './config.js';

const keypair = loadKeypair();
const walletAddress = keypair.publicKey.toBase58();

const usdcBalance = await getUsdcBalance(walletAddress);
const market = await getMarket(MARKET_ID);
const position = await getPosition(MARKET_ID, walletAddress);
const prices = await getMarketPrices(MARKET_ID);

console.log(JSON.stringify({
  walletAddress,
  usdcBalance,
  market,
  position,
  prices
}, null, 2));
