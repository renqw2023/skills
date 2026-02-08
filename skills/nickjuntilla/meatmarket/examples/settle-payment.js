/**
 * MeatMarket Payment Settlement Script
 * 
 * After verifying a proof, use this to record the payment.
 * You must send the USDC manually first, then call this to update the job status.
 * 
 * Usage:
 *   MEATMARKET_API_KEY=mm_... node settle-payment.js <job_id> <tx_link>
 */

const API_KEY = process.env.MEATMARKET_API_KEY;
const BASE_URL = 'https://meatmarket.fun/api/v1';

const jobId = process.argv[2];
const txLink = process.argv[3];

if (!API_KEY) {
  console.error('Error: MEATMARKET_API_KEY environment variable not set');
  process.exit(1);
}

if (!jobId || !txLink) {
  console.error('Usage: node settle-payment.js <job_id> <transaction_link>');
  console.error('Example: node settle-payment.js cd35... https://basescan.org/tx/0x...');
  process.exit(1);
}

async function settlePayment() {
  console.log(`Settling payment for job ${jobId}...`);
  console.log(`Transaction: ${txLink}`);

  try {
    const res = await fetch(`${BASE_URL}/jobs/${jobId}`, {
      method: 'PATCH',
      headers: {
        'Content-Type': 'application/json',
        'x-api-key': API_KEY
      },
      body: JSON.stringify({
        status: 'payment_sent',
        transaction_link: txLink
      })
    });

    const data = await res.json();

    if (res.ok) {
      console.log('\n✅ Payment recorded successfully!');
      console.log('Job status updated to: payment_sent');
    } else {
      console.error('\n❌ Failed to update job:');
      console.error(data);
    }
  } catch (err) {
    console.error('Error:', err.message);
  }
}

settlePayment();
