import { getUsdcBalance, loadKeypair } from './skill.js';

async function run() {
  const keypair = loadKeypair();
  const walletAddress = keypair.publicKey.toBase58();
  const usdcBalance = await getUsdcBalance(walletAddress);
  console.log(`USDC balance for ${walletAddress}:`, usdcBalance);
}

run().catch((err) => {
  console.error('Failed to fetch USDC balance:', err);
  process.exitCode = 1;
});
