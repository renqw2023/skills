#!/usr/bin/env node
const { execSync, spawn } = require('child_process');
const fs = require('fs');
const path = require('path');

const WRAPPER_INDEX = path.join(__dirname, 'index.js');
const PID_FILE = path.resolve(__dirname, '../../memory/evolver_wrapper.pid');
const LEGACY_PID_FILE = path.resolve(__dirname, '../../memory/evolver_loop.pid'); // Deprecated but checked for cleanup

// Unified watchdog: self-contained cron that calls lifecycle.js ensure every 10 minutes
function ensureWatchdog() {
  try {
    var selfScript = path.resolve(__dirname, 'lifecycle.js');
    var logFile = path.resolve(__dirname, '../../logs/evolver_watchdog.log');
    var cronEntry = '*/10 * * * * node "' + selfScript + '" ensure >> "' + logFile + '" 2>&1';
    var crontab = '';
    try { crontab = execSync('crontab -l 2>/dev/null || true', { encoding: 'utf8' }); } catch (_) {}

    // Check if any evolver-related cron already exists (lifecycle, evolver-daemon, evolver-watchdog, evolver-control)
    if (crontab.includes('lifecycle.js') && crontab.includes('ensure')) {
      return; // Already installed
    }

    // Clean out legacy entries from evolver-daemon, evolver-watchdog, evolver-control
    var lines = crontab.split('\n').filter(function(l) {
      return !l.includes('evolver-daemon') && !l.includes('evolver-watchdog') && !l.includes('evolver-control');
    });
    lines.push(cronEntry);
    var newCrontab = lines.filter(Boolean).join('\n') + '\n';
    execSync('echo ' + JSON.stringify(newCrontab) + ' | crontab -', { encoding: 'utf8' });
    console.log('[Lifecycle] Watchdog cron installed (every 10 min).');
  } catch (e) {
    console.warn('[Lifecycle] Failed to ensure watchdog:', e.message);
  }
}

function getAllRunningPids() {
  const pids = [];
  const relativePath = 'skills/feishu-evolver-wrapper/index.js';
  
  if (process.platform === 'linux') {
    try {
      const procs = fs.readdirSync('/proc').filter(p => /^\d+$/.test(p));
      for (const p of procs) {
        if (parseInt(p) === process.pid) continue; // Skip self
        try {
          const cmdline = fs.readFileSync(path.join('/proc', p, 'cmdline'), 'utf8');
          if ((cmdline.includes(WRAPPER_INDEX) || cmdline.includes(relativePath)) && cmdline.includes('--loop')) {
             pids.push(p);
          }
        } catch(e) {}
      }
    } catch(e) {}
  }
  return pids;
}

function getRunningPid() {
  // Check primary PID file
  if (fs.existsSync(PID_FILE)) {
    const pid = fs.readFileSync(PID_FILE, 'utf8').trim();
    try {
      process.kill(pid, 0);
      return pid;
    } catch (e) {
      // Stale
    }
  }
  
  // Check actual processes
  const pids = getAllRunningPids();
  if (pids.length > 0) {
      // If multiple, pick the first one and warn
      if (pids.length > 1) {
          console.warn(`[WARNING] Multiple wrapper instances found: ${pids.join(', ')}. Using ${pids[0]}.`);
      }
      const pid = pids[0];
      fs.writeFileSync(PID_FILE, pid);
      return pid;
  }

  return null;
}

function start(args) {
  const pid = getRunningPid();
  if (pid) {
    console.log(`Evolver wrapper is already running (PID ${pid}).`);
    return;
  }

  ensureWatchdog();

  console.log('Starting Evolver Wrapper...');
  const out = fs.openSync(path.resolve(__dirname, '../../logs/wrapper_out.log'), 'a');
  const err = fs.openSync(path.resolve(__dirname, '../../logs/wrapper_err.log'), 'a');

  const child = spawn('node', [WRAPPER_INDEX, ...args], {
    detached: true,
    stdio: ['ignore', out, err],
    cwd: __dirname
  });
  
  fs.writeFileSync(PID_FILE, String(child.pid));
  child.unref();
  console.log(`Started background process (PID ${child.pid}).`);
}

function stop() {
  const pid = getRunningPid();
  if (!pid) {
    console.log('Evolver wrapper is not running.');
    return;
  }

  console.log(`Stopping Evolver Wrapper (PID ${pid})...`);
  try {
    process.kill(pid, 'SIGTERM');
    console.log('SIGTERM sent.');
    
    // Wait for process to exit (max 5 seconds)
    const start = Date.now();
    while (Date.now() - start < 5000) {
      try {
        process.kill(pid, 0);
        // Busy wait but safer than execSync
        const now = Date.now();
        while (Date.now() - now < 100) {}
      } catch (e) {
        console.log(`Process ${pid} exited successfully.`);
        break;
      }
    }
    
    // Force kill if still running
    try {
      process.kill(pid, 0);
      console.warn(`Process ${pid} did not exit gracefully. Sending SIGKILL...`);
      process.kill(pid, 'SIGKILL');
    } catch (e) {
      // Already exited
    }

    // Clean up PID files
    if (fs.existsSync(PID_FILE)) fs.unlinkSync(PID_FILE);
    if (fs.existsSync(LEGACY_PID_FILE)) fs.unlinkSync(LEGACY_PID_FILE);
  } catch (e) {
    console.error(`Failed to stop PID ${pid}: ${e.message}`);
    // Ensure cleanup even on error if process is gone
    try { process.kill(pid, 0); } catch(err) {
        if (fs.existsSync(PID_FILE)) fs.unlinkSync(PID_FILE);
    }
  }
}

function status(json = false) {
  const pid = getRunningPid();
  const logFile = path.resolve(__dirname, '../../logs/wrapper_lifecycle.log');
  const cycleFile = path.resolve(__dirname, '../../logs/cycle_count.txt');
  
  let cycle = 'Unknown';
  if (fs.existsSync(cycleFile)) {
    cycle = fs.readFileSync(cycleFile, 'utf8').trim();
  }

  let lastActivity = 'Never';
  let lastAction = '';
  
  if (fs.existsSync(logFile)) {
    try {
      // Read last 1KB to find last line
      const stats = fs.statSync(logFile);
      const size = stats.size;
      const bufferSize = Math.min(1024, size);
      const buffer = Buffer.alloc(bufferSize);
      const fd = fs.openSync(logFile, 'r');
      fs.readSync(fd, buffer, 0, bufferSize, size - bufferSize);
      fs.closeSync(fd);
      
      const lines = buffer.toString().trim().split('\n');
      
      // Parse: 🧬 [ISO_TIMESTAMP] MSG...
      let match = null;
      let line = '';
      
      // Try parsing backwards for a valid timestamp line
      for (let i = lines.length - 1; i >= 0; i--) {
          line = lines[i].trim();
          if (!line) continue;
          match = line.match(/\[(.*?)\] (.*)/);
          if (match) break;
      }

      if (match) {
           const date = new Date(match[1]);
           if (!isNaN(date.getTime())) {
               const diff = Math.floor((Date.now() - date.getTime()) / 1000);
               
               if (diff < 60) lastActivity = `${diff}s ago`;
               else if (diff < 3600) lastActivity = `${Math.floor(diff/60)}m ago`;
               else lastActivity = `${Math.floor(diff/3600)}h ago`;
               
               lastAction = match[2];
           }
      }
    } catch (e) {
      lastActivity = 'Error reading log: ' + e.message;
    }
  }

  // Fallback: Check wrapper_out.log (more granular) if lifecycle log is old (>5m)
  try {
      const outLog = path.resolve(__dirname, '../../logs/wrapper_out.log');
      if (fs.existsSync(outLog)) {
          const stats = fs.statSync(outLog);
          const diff = Math.floor((Date.now() - stats.mtimeMs) / 1000);
          // If outLog is fresher than what we found, use it
          // Or just append it as "Output Update"
          if (diff < 300) { // Only if recent (<5m)
              let timeStr = diff < 60 ? `${diff}s ago` : `${Math.floor(diff/60)}m ago`;
              lastActivity += ` (Output updated ${timeStr})`;
          }
      }
  } catch(e) {}


  if (json) {
    console.log(JSON.stringify({
      loop: pid ? `running (pid ${pid})` : 'stopped',
      pid: pid || null,
      cycle: cycle,
      watchdog: pid ? 'ok' : 'unknown',
      last_activity: lastActivity,
      last_action: lastAction
    }));
  } else {
    if (pid) {
      console.log(`✅ Evolver wrapper is RUNNING (PID ${pid})`);
      console.log(`   Cycle: #${cycle}`);
      console.log(`   Last Activity: ${lastActivity}`);
      console.log(`   Action: ${lastAction.substring(0, 60)}${lastAction.length > 60 ? '...' : ''}`);
      
      // If requested via --report, send a card
      if (process.argv.includes('--report')) {
         try {
             const reportScript = path.resolve(__dirname, 'report.js');
             const statusText = `PID: ${pid}\nCycle: #${cycle}\nLast Activity: ${lastActivity}\nAction: ${lastAction}`;
             const cmd = `node "${reportScript}" --title "🧬 Evolver Status Check" --status "Status: [RUNNING] wrapper is active.\n${statusText}" --color "green"`;
             execSync(cmd, { stdio: 'inherit' });
         } catch(e) {
             console.error('Failed to send status report:', e.message);
         }
      }

    } else {
      console.log('❌ Evolver wrapper is STOPPED');
      console.log(`   Last Known Cycle: #${cycle}`);
      console.log(`   Last Activity: ${lastActivity}`);

      if (process.argv.includes('--report')) {
         try {
             const reportScript = path.resolve(__dirname, 'report.js');
             const statusText = `Last Known Cycle: #${cycle}\nLast Activity: ${lastActivity}`;
             const cmd = `node "${reportScript}" --title "🚨 Evolver Status Check" --status "Status: [STOPPED] wrapper is NOT running.\n${statusText}" --color "red"`;
             execSync(cmd, { stdio: 'inherit' });
         } catch(e) {
             console.error('Failed to send status report:', e.message);
         }
      }
    }
  }
}

const action = process.argv[2];
const passArgs = process.argv.slice(2);

switch (action) {
  case 'start':
  case '--loop': 
    start(['--loop']);
    break;
  case 'stop':
    stop();
    break;
  case 'status':
    status(passArgs.includes('--json'));
    break;
  case 'restart':
    stop();
    setTimeout(() => start(['--loop']), 1000);
    break;
  case 'ensure':
    // Handle --delay argument (wait before checking)
    const delayArgIndex = passArgs.indexOf('--delay');
    if (delayArgIndex !== -1 && passArgs[delayArgIndex + 1]) {
        const ms = parseInt(passArgs[delayArgIndex + 1]);
        if (!isNaN(ms) && ms > 0) {
            console.log(`[Ensure] Waiting ${ms}ms before check...`);
            try {
                // Use sleep to save CPU (Linux only)
                execSync(`sleep ${ms / 1000}`);
            } catch (e) {
                // Fallback to busy wait if sleep fails
                const end = Date.now() + ms;
                while (Date.now() < end) {}
            }
        }
    }

    // Check if process is stuck by inspecting logs (stale > 10m)
    // We do this BEFORE the debounce check, because a stuck process needs immediate attention
    let isStuck = false;
    try {
        const logFile = path.resolve(__dirname, '../../logs/wrapper_lifecycle.log');
        const outLog = path.resolve(__dirname, '../../logs/wrapper_out.log');
        
        // Only consider stuck if BOTH logs are stale > 20m (to avoid false positives during sleep/long cycles)
        const now = Date.now();
        const threshold = 1200000; // 20 minutes (increased from 10m to support long reasoning cycles)
        
        let lifeStale = true;
        let outStale = true;

        if (fs.existsSync(logFile)) {
             lifeStale = (now - fs.statSync(logFile).mtimeMs) > threshold;
        }
        
        if (fs.existsSync(outLog)) {
             outStale = (now - fs.statSync(outLog).mtimeMs) > threshold;
        } else {
             // If outLog is missing but process is running, that's suspicious, but maybe it just started?
             // Let's assume stale if missing for >10m uptime, but simpler to just say stale=true.
        }

        if (lifeStale && outStale) {
            isStuck = true;
            console.log(`[Ensure] Logs are stale (Lifecycle: ${lifeStale}, Out: ${outStale}). Marking as stuck.`);
        }
    } catch(e) {
        console.warn('[Ensure] Log check failed:', e.message);
    }

    if (isStuck) {
        console.warn('[Ensure] Process appears stuck (logs stale > 10m). Restarting...');
        stop();
        // Clear lock so we can proceed
        try { if (fs.existsSync(path.resolve(__dirname, '../../memory/evolver_ensure.lock'))) fs.unlinkSync(path.resolve(__dirname, '../../memory/evolver_ensure.lock')); } catch(e) {}
    }

    // Simple debounce: if a recent ensure lock exists (<5m), skip
    const ensureLock = path.resolve(__dirname, '../../memory/evolver_ensure.lock');
    try {
      if (fs.existsSync(ensureLock)) {
        const stats = fs.statSync(ensureLock);
        if (Date.now() - stats.mtimeMs < 300000) { // Increased debounce to 5m
          // silent exit
          process.exit(0);
        }
      }
      fs.writeFileSync(ensureLock, String(Date.now()));
    } catch(e) {}

    ensureWatchdog();
    
    const runningPids = getAllRunningPids();
    if (runningPids.length > 1) {
        console.warn(`[Ensure] Found multiple instances: ${runningPids.join(', ')}. Killing all to reset state.`);
        runningPids.forEach(p => {
            try { process.kill(p, 'SIGKILL'); } catch(e) {}
        });
        // Remove PID file to force clean start
        if (fs.existsSync(PID_FILE)) fs.unlinkSync(PID_FILE);
        // Wait briefly for OS to clear
        execSync('sleep 1');
    }
    
    if (!getRunningPid()) {
      start(['--loop']);
      // If we started it, report success if requested
      if (passArgs.includes('--report')) {
          setTimeout(() => status(false), 2000); // wait for startup
      }
    } else {
      // If ensuring and already running, stay silent unless JSON/report requested
      if (passArgs.includes('--json')) {
         setTimeout(() => status(true), 1000);
         return;
      }
      if (passArgs.includes('--report')) {
         status(false);
         return;
      }
      // Silent success - do not spam logs
      return; 
    }
    // Only print status if we just started it or if JSON requested
    if (!getRunningPid() || passArgs.includes('--json')) {
       status(passArgs.includes('--json'));
    }
    break;
  default:
    console.log('Usage: node lifecycle.js [start|stop|restart|status|ensure|--loop] [--json]');
    status();
}
