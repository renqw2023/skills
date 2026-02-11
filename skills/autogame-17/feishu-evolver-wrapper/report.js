#!/usr/bin/env node
const fs = require('fs');
const path = require('path');
const os = require('os');
const { program } = require('commander');
const { execSync } = require('child_process');
const { sendCard } = require('./feishu-helper.js');
const { fetchWithAuth } = require('../common/feishu-client.js');
const crypto = require('crypto');

// --- REPORT DEDUP ---
const DEDUP_FILE = path.resolve(__dirname, '../../memory/report_dedup.json');
const DEDUP_WINDOW_MS = 30 * 60 * 1000; // 30 minutes

function isDuplicateReport(reportKey) {
    if (process.env.EVOLVE_REPORT_DEDUP === '0') return false;
    try {
        var cache = {};
        if (fs.existsSync(DEDUP_FILE)) {
            cache = JSON.parse(fs.readFileSync(DEDUP_FILE, 'utf8'));
        }
        var now = Date.now();
        // Prune old entries
        for (var k in cache) {
            if (now - cache[k] > DEDUP_WINDOW_MS) delete cache[k];
        }
        if (cache[reportKey]) {
            console.log('[Wrapper] Report dedup: skipping duplicate report (' + reportKey.slice(0, 40) + '...)');
            return true;
        }
        cache[reportKey] = now;
        var tmpDedup = DEDUP_FILE + '.tmp.' + process.pid;
        fs.writeFileSync(tmpDedup, JSON.stringify(cache, null, 2));
        fs.renameSync(tmpDedup, DEDUP_FILE);
        return false;
    } catch (e) {
        // On error, allow the report through
        return false;
    }
}

// --- DASHBOARD LOGIC START ---
const EVENTS_FILE = path.resolve(__dirname, '../../assets/gep/events.jsonl');

function getDashboardStats() {
    if (!fs.existsSync(EVENTS_FILE)) return null;
    
    try {
        const content = fs.readFileSync(EVENTS_FILE, 'utf8');
        const lines = content.split('\n').filter(Boolean);
        const events = lines.map(l => { try { return JSON.parse(l); } catch(e){ return null; } }).filter(e => e && e.type === 'EvolutionEvent');
        
        if (events.length === 0) return null;

        const total = events.length;
        const successful = events.filter(e => e.outcome && e.outcome.status === 'success').length;
        const successRate = ((successful / total) * 100).toFixed(1);
        
        const intents = { innovate: 0, repair: 0, optimize: 0 };
        events.forEach(e => {
            if (intents[e.intent] !== undefined) intents[e.intent]++;
        });

        const recent = events.slice(-5).reverse().map(e => ({
            id: e.id.replace('evt_', '').substring(0, 6),
            intent: e.intent === 'innovate' ? '✨' : (e.intent === 'repair' ? '🔧' : '⚡'),
            status: e.outcome && e.outcome.status === 'success' ? '✅' : '❌'
        }));

        return { total, successRate, intents, recent };
    } catch (e) {
        return null;
    }
}
// --- DASHBOARD LOGIC END ---

let runSkillsMonitor;
try {
    runSkillsMonitor = require('../evolver/src/ops/skills_monitor').run;
} catch (e) {
    try { runSkillsMonitor = require('./skills_monitor.js').run; } catch (e2) {
        runSkillsMonitor = () => [];
    }
}

// INNOVATION: Load dedicated System Monitor (Native Node) if available
let sysMon;
try {
    // Try to load the optimized monitor first
    sysMon = require('../common/system-monitor/index.js');
} catch (e) {
    // Fallback: minimal implementation using child_process (discouraged but functional)
    sysMon = {
        getProcessCount: () => { try { return execSync('ps -e | wc -l').toString().trim(); } catch(e){ return '?'; } },
        getDiskUsage: () => { try { return execSync("df -h / | tail -1 | awk '{print $5}'").toString().trim(); } catch(e){ return '?'; } },
        getLastLine: (f) => { try { return execSync(`tail -n 1 "${f}"`).toString().trim(); } catch(e){ return ''; } }
    };
}

program
  .option('-s, --status <text>', 'Status text/markdown content')
  .option('-f, --file <path>', 'Path to markdown file content')
  .option('-c, --cycle <id>', 'Evolution Cycle ID')
  .option('--title <text>', 'Card Title override')
  .option('--color <color>', 'Header color (blue/red/green/orange)', 'blue')
  .option('--target <id>', 'Target User/Chat ID')
  .option('--lang <lang>', 'Language (en|cn)', 'en')
  .parse(process.argv);

const options = program.opts();

const STATE_FILE = path.resolve(__dirname, '../../memory/evolution_state.json');

function getCycleInfo() {
    let nextId = 1;
    let durationStr = 'N/A';
    const now = new Date();

    // 1. Try State File (Fast & Persistent)
    try {
        if (fs.existsSync(STATE_FILE)) {
            const state = JSON.parse(fs.readFileSync(STATE_FILE, 'utf8'));
            if (state.lastCycleId) {
                nextId = state.lastCycleId + 1;
                
                // Calculate duration since last cycle
                if (state.lastUpdate) {
                    const diff = now.getTime() - new Date(state.lastUpdate).getTime();
                    const mins = Math.floor(diff / 60000);
                    const secs = Math.floor((diff % 60000) / 1000);
                    durationStr = `${mins}m ${secs}s`;
                }

                // Auto-increment and save
                state.lastCycleId = nextId;
                state.lastUpdate = now.toISOString();
                fs.writeFileSync(STATE_FILE, JSON.stringify(state, null, 2));
                return { id: nextId, duration: durationStr };
            }
        }
    } catch (e) {}

    // 2. Fallback: MEMORY.md (Legacy/Seed)
    let maxId = 0;
    try {
        const memPath = path.resolve(__dirname, '../../MEMORY.md');
        if (fs.existsSync(memPath)) {
            const memContent = fs.readFileSync(memPath, 'utf8');
            const matches = [...memContent.matchAll(/Cycle #(\d+)/g)];
            for (const match of matches) {
                const id = parseInt(match[1]);
                if (id > maxId) maxId = id;
            }
        }
    } catch (e) {}

    // Initialize State File if missing
    nextId = (maxId > 0 ? maxId : Math.floor(Date.now() / 1000)) + 1;
    try {
        fs.writeFileSync(STATE_FILE, JSON.stringify({
            lastCycleId: nextId,
            lastUpdate: now.toISOString()
        }, null, 2));
    } catch(e) {}

    return { id: nextId, duration: 'First Run' };
}

async function findEvolutionGroup() {
    try {
        let pageToken = '';
        do {
            const url = `https://open.feishu.cn/open-apis/im/v1/chats?page_size=100${pageToken ? `&page_token=${pageToken}` : ''}`;
            const res = await fetchWithAuth(url, { method: 'GET' });
            const data = await res.json();
            
            if (data.code !== 0) {
                console.warn(`[Wrapper] List Chats failed: ${data.msg}`);
                return null;
            }

            if (data.data && data.data.items) {
                const group = data.data.items.find(c => c.name && c.name.includes('🧬'));
                if (group) {
                    console.log(`[Wrapper] Found Evolution Group: ${group.name} (${group.chat_id})`);
                    return group.chat_id;
                }
            }
            
            pageToken = data.data.page_token;
        } while (pageToken);
    } catch (e) {
        console.warn(`[Wrapper] Group lookup error: ${e.message}`);
    }
    return null;
}

// Resolve content
let content = options.status || '';
if (options.file) {
    try {
        content = fs.readFileSync(options.file, 'utf8');
    } catch (e) {
        console.error(`Failed to read file: ${options.file}`);
        process.exit(1);
    }
}

if (!content) {
    console.error('Error: Must provide --status or --file');
    process.exit(1);
}

// Prepare Title
const cycleInfo = options.cycle ? { id: options.cycle, duration: 'Manual' } : getCycleInfo();
const cycleId = cycleInfo.id;
let title = options.title;

if (!title) {
    // Default title based on lang
    if (options.lang === 'cn') {
        title = `🧬 进化 #${cycleId} 日志`;
    } else {
        title = `🧬 Evolution #${cycleId} Log`;
    }
}

// Resolve Target
const MASTER_ID = process.env.OPENCLAW_MASTER_ID || '';

(async () => {
    let target = options.target;

    // Priority: CLI Target > Evolution Group (🧬) > Master ID
    if (!target) {
        target = await findEvolutionGroup();
    }
    
    if (!target) {
        console.log('[Wrapper] No Evolution Group (🧬) found. Falling back to Master ID.');
        target = MASTER_ID;
    }

    if (!target) {
        console.error('[Wrapper] Error: No target ID found (Env OPENCLAW_MASTER_ID missing and no --target).');
        process.exit(1);
    }

    // --- DASHBOARD SNAPSHOT ---
    let dashboardMd = '';
    const stats = getDashboardStats();
    if (stats) {
        const trend = stats.recent.map(e => `${e.intent}${e.status}`).join(' ');
        
        dashboardMd = `\n\n---
**📊 Dashboard Snapshot**
- **Success Rate:** ${stats.successRate}% (${stats.total} Cycles)
- **Breakdown:** ✨${stats.intents.innovate} 🔧${stats.intents.repair} ⚡${stats.intents.optimize}
- **Recent:** ${trend}`;
    }
    // --- END SNAPSHOT ---

    try {
        console.log(`[Wrapper] Reporting Cycle #${cycleId} to ${target}...`);
        
        let procCount = '?';
        let memUsage = '?';
        let uptime = '?';
        let loadAvg = '?';
        let diskUsage = '?';

        try {
            procCount = sysMon.getProcessCount();
            memUsage = Math.round(process.memoryUsage().rss / 1024 / 1024);
            uptime = Math.round(process.uptime());
            loadAvg = os.loadavg()[0].toFixed(2);
            diskUsage = sysMon.getDiskUsage('/');
        } catch(e) {
            console.warn('[Wrapper] Stats collection failed:', e.message);
        }

        // --- ERROR LOG CHECK ---
        let errorAlert = '';
        try {
            const evolverDirName = ['private-evolver', 'evolver', 'capability-evolver'].find(d => fs.existsSync(path.resolve(__dirname, `../${d}/index.js`))) || 'private-evolver';
            const evolverDir = path.resolve(__dirname, `../${evolverDirName}`);
            const errorLogPath = path.join(evolverDir, 'evolution_error.log');

            if (fs.existsSync(errorLogPath)) {
                const stats = fs.statSync(errorLogPath);
                const now = new Date();
                const diffMs = now - stats.mtime;
                
                if (diffMs < 10 * 60 * 1000) {
                    const lastLine = (sysMon.getLastLine(errorLogPath) || '').substring(0, 200);
                    errorAlert = `\n\n⚠️ **CRITICAL ALERT**: System reported a failure ${(diffMs/1000/60).toFixed(1)}m ago.\n> ${lastLine}`;
                }
            }
        } catch (e) {}

        // --- SKILL HEALTH CHECK ---
        let healthAlert = '';
        try {
            const issues = runSkillsMonitor();
            if (issues && issues.length > 0) {
                healthAlert = `\n\n🚨 **SKILL HEALTH WARNING**: ${issues.length} skill(s) broken.\n`;
                issues.slice(0, 3).forEach(issue => {
                    healthAlert += `> **${issue.name}**: ${issue.issues.join(', ')}\n`;
                });
                if (issues.length > 3) healthAlert += `> ...and ${issues.length - 3} more.`;
            }
        } catch (e) {
            console.warn('[Wrapper] Skill monitor failed:', e.message);
        }

        const isChineseReport = options.lang === 'cn';

        const labels = isChineseReport
            ? {
                proc: '进程',
                mem: '内存',
                up: '运行',
                load: '负载',
                disk: '磁盘',
                loop: '循环',
                skills: '技能',
                ok: '正常',
                loopOn: '运行中',
                loopOff: '已停止'
            }
            : {
                proc: 'Proc',
                mem: 'Mem',
                up: 'Up',
                load: 'Load',
                disk: 'Disk',
                loop: 'Loop',
                skills: 'Skills',
                ok: 'OK',
                loopOn: 'ON',
                loopOff: 'OFF'
            };

        // --- LOOP STATUS CHECK ---
        let loopStatus = 'UNKNOWN';
        try {
            const lifecycle = require('./lifecycle.js');
            // Mock status call to avoid exec/logs spam if possible, or use status --json?
            // Actually lifecycle.status() prints to console. We should export a helper.
            // For now, assume if pid file exists, it's running.
            const PID_FILE = path.resolve(__dirname, '../../memory/evolver_wrapper.pid');
            if (fs.existsSync(PID_FILE)) {
                 try { process.kill(parseInt(fs.readFileSync(PID_FILE, 'utf8').trim(), 10), 0); loopStatus = labels.loopOn; } 
                 catch(e) { loopStatus = labels.loopOff; }
            } else {
                 loopStatus = labels.loopOff;
            }
        } catch (e) {
            loopStatus = `${labels.loopOff} (?)`;
        }

        let footerStats = `${labels.proc}: ${procCount} | ${labels.mem}: ${memUsage}MB | ${labels.up}: ${uptime}s | ${labels.load}: ${loadAvg} | ${labels.disk}: ${diskUsage} | 🔁 ${labels.loop}: ${loopStatus}`;
        if (!healthAlert) footerStats += ` | 🛡️ ${labels.skills}: ${labels.ok}`;

        const finalContent = `${content}${errorAlert}${healthAlert}${dashboardMd}`;

        // --- DEDUP CHECK ---
        var statusHash = crypto.createHash('md5').update(options.status || '').digest('hex').slice(0, 12);
        var reportKey = `${cycleId}:${target}:${title}:${statusHash}`;
        if (isDuplicateReport(reportKey)) {
            console.log('[Wrapper] Duplicate report suppressed.');
            process.exit(0);
        }

        await sendCard({
            target: target,
            title: title,
            text: finalContent,
            note: footerStats,
            color: options.color || 'blue'
        });
        
        console.log('[Wrapper] Report sent successfully.');

        try {
            const LOG_FILE = path.resolve(__dirname, '../../logs/evolution_reports.log');
            if (!fs.existsSync(path.dirname(LOG_FILE))) {
                fs.mkdirSync(path.dirname(LOG_FILE), { recursive: true });
            }
            fs.appendFileSync(LOG_FILE, `[${new Date().toISOString()}] Cycle #${cycleId} - Status: SUCCESS - Target: ${target} - Duration: ${cycleInfo.duration}\n`);
        } catch (logErr) {
            console.warn('[Wrapper] Failed to write to local log:', logErr.message);
        }
    } catch (e) {
        console.error('[Wrapper] Report failed:', e.message);
        process.exit(1);
    }
})();
