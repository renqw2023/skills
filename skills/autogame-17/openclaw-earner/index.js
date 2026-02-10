#!/usr/bin/env node
// agent-earner: Autonomous bounty hunter for AI agents
// Supports ClawTasks and OpenWork platforms
//
// Usage:
//   node index.js browse                     # List open bounties
//   node index.js browse --match             # Only show skill-matched bounties
//   node index.js propose <bounty_id>        # Submit a proposal
//   node index.js submit <bounty_id> <file>  # Submit completed work
//   node index.js stats                      # View earnings stats
//   node index.js daemon                     # Start autonomous mode
//
const { program } = require('commander');
const path = require('path');
const fs = require('fs');

try {
    require('dotenv').config({ path: path.resolve(__dirname, '../../.env') });
} catch (e) {}

const CLAWTASKS_API = 'https://clawtasks.com/api';
const OPENWORK_API = 'https://api.openwork.bot/v1';
const CLAWTASKS_KEY = process.env.CLAWTASKS_API_KEY || '';
const OPENWORK_KEY = process.env.OPENWORK_API_KEY || '';
const POLL_INTERVAL_MS = (Number(process.env.EARNER_POLL_MINUTES) || 30) * 60 * 1000;
const STATE_FILE = path.join(__dirname, '.earner_state.json');

const AGENT_SKILLS = ['writing', 'research', 'code', 'creative', 'documentation', 'automation'];

function loadState() {
    try {
        if (fs.existsSync(STATE_FILE)) return JSON.parse(fs.readFileSync(STATE_FILE, 'utf8'));
    } catch (e) {}
    return { proposals: [], submissions: [], totalEarned: 0, lastPoll: null };
}

function saveState(state) {
    fs.writeFileSync(STATE_FILE, JSON.stringify(state, null, 2));
}

async function apiFetch(url, opts = {}) {
    const timeout = opts.timeout || 30000;
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), timeout);
    try {
        const res = await fetch(url, { ...opts, signal: controller.signal });
        const data = await res.json();
        if (!res.ok) throw new Error(data.error || data.message || `HTTP ${res.status}`);
        return data;
    } finally {
        clearTimeout(timer);
    }
}

async function browseBounties({ platform = 'all', matchSkills = false } = {}) {
    const bounties = [];

    if ((platform === 'all' || platform === 'clawtasks') && CLAWTASKS_KEY) {
        try {
            const data = await apiFetch(`${CLAWTASKS_API}/bounties?status=open`, {
                headers: { 'Authorization': `Bearer ${CLAWTASKS_KEY}` }
            });
            const items = (data.bounties || data.data || []).map(b => ({
                id: b.id,
                title: b.title || b.name,
                reward: `${b.reward || b.amount || '?'} USDC`,
                tags: b.tags || b.skills || [],
                platform: 'clawtasks',
                deadline: b.deadline || b.expires_at,
                url: `https://clawtasks.com/bounty/${b.id}`
            }));
            bounties.push(...items);
        } catch (e) {
            console.error(`[ClawTasks] ${e.message}`);
        }
    }

    if ((platform === 'all' || platform === 'openwork') && OPENWORK_KEY) {
        try {
            const data = await apiFetch(`${OPENWORK_API}/tasks?status=open`, {
                headers: { 'Authorization': `Bearer ${OPENWORK_KEY}` }
            });
            const items = (data.tasks || data.data || []).map(b => ({
                id: b.id,
                title: b.title || b.name,
                reward: `${b.reward || b.amount || '?'} $OPENWORK`,
                tags: b.tags || b.skills || [],
                platform: 'openwork',
                deadline: b.deadline || b.expires_at,
                url: `https://openwork.bot/task/${b.id}`
            }));
            bounties.push(...items);
        } catch (e) {
            console.error(`[OpenWork] ${e.message}`);
        }
    }

    if (!CLAWTASKS_KEY && !OPENWORK_KEY) {
        console.error('Error: No API keys configured. Set CLAWTASKS_API_KEY and/or OPENWORK_API_KEY.');
        return [];
    }

    if (matchSkills) {
        return bounties.filter(b =>
            b.tags.some(t => AGENT_SKILLS.includes(t.toLowerCase()))
        );
    }
    return bounties;
}

async function submitProposal(bountyId, proposal) {
    const state = loadState();

    // Try ClawTasks first
    if (CLAWTASKS_KEY) {
        try {
            const data = await apiFetch(`${CLAWTASKS_API}/bounties/${bountyId}/propose`, {
                method: 'POST',
                headers: {
                    'Authorization': `Bearer ${CLAWTASKS_KEY}`,
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ proposal: proposal || 'AI agent proposal - will deliver quality work within deadline.' })
            });
            state.proposals.push({ id: bountyId, platform: 'clawtasks', at: new Date().toISOString() });
            saveState(state);
            console.log(JSON.stringify({ ok: true, platform: 'clawtasks', proposalId: data.id || data.proposal_id }));
            return;
        } catch (e) {
            if (!OPENWORK_KEY) throw e;
        }
    }

    // Try OpenWork
    if (OPENWORK_KEY) {
        const data = await apiFetch(`${OPENWORK_API}/tasks/${bountyId}/bids`, {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${OPENWORK_KEY}`,
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ message: proposal || 'AI agent bid - experienced in automation and research.' })
        });
        state.proposals.push({ id: bountyId, platform: 'openwork', at: new Date().toISOString() });
        saveState(state);
        console.log(JSON.stringify({ ok: true, platform: 'openwork', bidId: data.id || data.bid_id }));
    }
}

async function submitWork(bountyId, workFile) {
    const state = loadState();
    let work = workFile;
    if (fs.existsSync(workFile)) {
        work = fs.readFileSync(workFile, 'utf8');
    }

    if (CLAWTASKS_KEY) {
        try {
            const data = await apiFetch(`${CLAWTASKS_API}/bounties/${bountyId}/submit`, {
                method: 'POST',
                headers: {
                    'Authorization': `Bearer ${CLAWTASKS_KEY}`,
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ content: work })
            });
            state.submissions.push({ id: bountyId, platform: 'clawtasks', at: new Date().toISOString() });
            saveState(state);
            console.log(JSON.stringify({ ok: true, platform: 'clawtasks', submissionId: data.id }));
            return;
        } catch (e) {
            if (!OPENWORK_KEY) throw e;
        }
    }

    if (OPENWORK_KEY) {
        const data = await apiFetch(`${OPENWORK_API}/tasks/${bountyId}/submit`, {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${OPENWORK_KEY}`,
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ content: work })
        });
        state.submissions.push({ id: bountyId, platform: 'openwork', at: new Date().toISOString() });
        saveState(state);
        console.log(JSON.stringify({ ok: true, platform: 'openwork', submissionId: data.id }));
    }
}

function showStats() {
    const state = loadState();
    console.log(JSON.stringify({
        proposals: state.proposals.length,
        submissions: state.submissions.length,
        totalEarned: state.totalEarned,
        lastPoll: state.lastPoll,
        recentProposals: state.proposals.slice(-5),
        recentSubmissions: state.submissions.slice(-5)
    }, null, 2));
}

async function daemonMode() {
    console.log(`[Earner] Autonomous mode started. Polling every ${POLL_INTERVAL_MS / 60000} minutes.`);
    while (true) {
        try {
            const bounties = await browseBounties({ matchSkills: true });
            const state = loadState();
            state.lastPoll = new Date().toISOString();

            if (bounties.length > 0) {
                console.log(`[Earner] Found ${bounties.length} matching bounties.`);
                // Auto-propose on the first unproposed bounty
                const proposed = new Set(state.proposals.map(p => p.id));
                const fresh = bounties.filter(b => !proposed.has(b.id));
                if (fresh.length > 0) {
                    const target = fresh[0];
                    console.log(`[Earner] Auto-proposing: ${target.title} (${target.reward})`);
                    try {
                        await submitProposal(target.id);
                    } catch (e) {
                        console.error(`[Earner] Proposal failed: ${e.message}`);
                    }
                }
            } else {
                console.log(`[Earner] No matching bounties found.`);
            }
            saveState(state);
        } catch (e) {
            console.error(`[Earner] Poll error: ${e.message}`);
        }
        await new Promise(r => setTimeout(r, POLL_INTERVAL_MS));
    }
}

program
    .command('browse')
    .description('List open bounties')
    .option('--match', 'Only show skill-matched bounties')
    .option('--platform <platform>', 'Platform filter (clawtasks|openwork|all)', 'all')
    .action(async (opts) => {
        const bounties = await browseBounties({ platform: opts.platform, matchSkills: opts.match });
        console.log(JSON.stringify(bounties, null, 2));
    });

program
    .command('propose <bountyId>')
    .description('Submit a proposal for a bounty')
    .option('--message <text>', 'Custom proposal message')
    .action(async (bountyId, opts) => {
        await submitProposal(bountyId, opts.message);
    });

program
    .command('submit <bountyId> <work>')
    .description('Submit completed work (text or file path)')
    .action(async (bountyId, work) => {
        await submitWork(bountyId, work);
    });

program
    .command('stats')
    .description('View earnings statistics')
    .action(() => {
        showStats();
    });

program
    .command('daemon')
    .description('Start autonomous bounty hunting mode')
    .action(async () => {
        await daemonMode();
    });

program.parse();
