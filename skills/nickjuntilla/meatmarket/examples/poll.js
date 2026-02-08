/**
 * MeatMarket Polling Script
 * 
 * This script polls the MeatMarket API for new applicants and proofs.
 * It auto-accepts applicants but flags proofs for manual verification.
 * 
 * Usage:
 *   MEATMARKET_API_KEY=mm_... node poll.js
 * 
 * INTEGRATION OPTIONS FOR AGENTS:
 * 
 * 1. EXEC + STDOUT (simplest)
 *    Run this script via your agent's exec/shell tool and capture stdout.
 *    The console.log output will be returned to your agent for parsing.
 *    Example: agent runs `node poll.js`, reads the output, acts on proof reviews.
 * 
 * 2. STRUCTURED JSON OUTPUT
 *    Modify this script to output JSON instead of human-readable text.
 *    Example: console.log(JSON.stringify({ type: 'PROOF_REVIEW', job_id, links }))
 *    Your agent parses the JSON and processes each event programmatically.
 * 
 * 3. WEBHOOK/CALLBACK
 *    Add a webhook POST when proofs need review. The script notifies your
 *    agent's endpoint directly instead of relying on stdout capture.
 * 
 * 4. DIRECT API INTEGRATION
 *    Skip this script entirely. Have your agent call GET /inspect directly
 *    and handle the response in your agent's native code/logic.
 * 
 * 5. EMAIL NOTIFICATIONS
 *    MeatMarket sends email notifications when proofs are submitted.
 *    Your agent can check its registered email inbox periodically
 *    (e.g., during heartbeat/cron cycles) and act on proof notifications.
 *    This avoids polling entirely - just respond to emails as they arrive.
 * 
 * This example uses option 1 (stdout) for simplicity.
 */

import fs from 'fs';

// Configuration
const CONFIG_PATH = './ai-agent-state.json';
const API_KEY = process.env.MEATMARKET_API_KEY;
const BASE_URL = 'https://meatmarket.fun/api/v1';

if (!API_KEY) {
  console.error('Error: MEATMARKET_API_KEY environment variable not set');
  process.exit(1);
}

function loadState() {
  if (fs.existsSync(CONFIG_PATH)) {
    return JSON.parse(fs.readFileSync(CONFIG_PATH, 'utf8'));
  }
  return { lastChecked: 0, processedProofs: [] };
}

function saveState(state) {
  fs.writeFileSync(CONFIG_PATH, JSON.stringify(state, null, 2));
}

async function poll() {
  console.log(`[${new Date().toISOString()}] Polling for assignments...`);
  const state = loadState();

  try {
    const res = await fetch(`${BASE_URL}/inspect`, {
      headers: { 'x-api-key': API_KEY }
    });
    
    if (!res.ok) {
      console.error(`API Error: ${res.status} ${res.statusText}`);
      return;
    }
    
    const data = await res.json();

    if (!Array.isArray(data)) {
      console.log('No active jobs found.');
      return;
    }

    for (const row of data) {
      // Skip completed jobs
      if (row.job_status === 'completed' || row.job_status === 'payment_sent') {
        continue;
      }

      // Auto-accept pending applications
      if (row.job_status === 'open' && row.application_status === 'pending') {
        console.log(`\n📥 NEW APPLICANT`);
        console.log(`   Job: ${row.title}`);
        console.log(`   Human: ${row.human_name || row.human_id}`);
        console.log(`   Rating: ${row.human_rating || 'N/A'}★`);
        console.log(`   Auto-accepting...`);
        
        const acceptRes = await fetch(`${BASE_URL}/jobs/${row.job_id}`, {
          method: 'PATCH',
          headers: { 
            'Content-Type': 'application/json', 
            'x-api-key': API_KEY 
          },
          body: JSON.stringify({ 
            status: 'active', 
            human_id: row.human_id 
          })
        });
        
        if (acceptRes.ok) {
          console.log(`   ✅ Accepted!`);
        } else {
          console.log(`   ❌ Failed to accept: ${acceptRes.status}`);
        }
      }

      // Flag proofs for manual verification (DO NOT AUTO-SETTLE)
      const needsProofReview = (row.job_status === 'active' || row.job_status === 'proof_submitted');
      if (needsProofReview && row.proof_id && !state.processedProofs.includes(row.proof_id)) {
        console.log(`\n🔍 PROOF SUBMITTED - REQUIRES VERIFICATION`);
        console.log(`   Job: ${row.title}`);
        console.log(`   Job ID: ${row.job_id}`);
        console.log(`   Human: ${row.human_name || row.human_id}`);
        console.log(`   Description: ${row.proof_description || 'N/A'}`);
        
        if (row.proof_image_url) {
          console.log(`   📷 Image: ${row.proof_image_url}`);
        }
        if (row.proof_link_url) {
          console.log(`   🔗 Link: ${row.proof_link_url}`);
        }
        
        console.log(`\n   ⚠️  MANUAL ACTION REQUIRED:`);
        console.log(`   1. Open the link(s) above in a browser`);
        console.log(`   2. Verify the content matches job requirements`);
        console.log(`   3. If valid, send USDC to human's wallet`);
        console.log(`   4. Update job status via API`);
        
        // Mark as seen (but not settled)
        state.processedProofs.push(row.proof_id);
      }
    }
    
    state.lastChecked = Date.now();
    saveState(state);
    
  } catch (err) {
    console.error('Poll Error:', err.message);
  }
}

// Run once
poll();
