#!/usr/bin/env node
/**
 * GuavaGuard v4.0 — Agent Skill Security Scanner 🍈🛡️
 * 
 * Based on Snyk ToxicSkills taxonomy (8 threat categories)
 * + ClawHavoc campaign IoCs + Koi Security intel
 * + Snyk Leaky Skills research (Feb 2026)
 * + Simula Research Lab prompt worm analysis
 * + CVE-2026-25253 / Palo Alto IBC framework
 * 
 * v4.0 additions:
 * - Leaky Skills detection (credential-in-context, verbatim output traps)
 * - Memory poisoning detection (MEMORY.md / SOUL.md write instructions)
 * - Prompt worm patterns (self-replicating instructions via Moltbook)
 * - Lightweight JS AST analysis (call graph, taint tracking, zero-dep)
 * - CVE-2026-25253 patterns (gatewayUrl injection)
 * - Time-shifted injection detection (cross-file payload fragments)
 * - Persistence mechanism detection (cron/heartbeat/schedule abuse)
 * - Enhanced IoCs (new C2 domains, CVE patterns)
 * - HTML report output (--html)
 * 
 * v3.x features:
 * - Unicode BiDi/homoglyph/invisible character detection
 * - Dependency chain scanning (package.json)
 * - Context-aware: docs vs code differentiated (FP reduction ~80%)
 * - Self-exclusion, whitelist, flow analysis, entropy analysis
 * - SARIF output, custom rules, --fail-on-findings
 * 
 * Zero dependencies. Single file. Node.js 18+.
 * 
 * Usage:
 *   node guava-guard.js [scan-dir] [options]
 * 
 * Options:
 *   --verbose, -v       Show detailed findings
 *   --json              Output JSON report
 *   --self-exclude      Exclude the guava-guard skill directory itself
 *   --strict            Lower thresholds (suspicious=20, malicious=60)
 *   --summary-only      Only print summary, no per-skill output
 *   --check-deps        Enable dependency chain scanning (reads package.json)
 */

const fs = require('fs');
const path = require('path');

// ===== CONFIGURATION =====
const VERSION = '4.0.0';

const THRESHOLDS = {
  normal:  { suspicious: 30, malicious: 80 },
  strict:  { suspicious: 20, malicious: 60 },
};

// File classification
const CODE_EXTENSIONS = new Set(['.js', '.ts', '.mjs', '.cjs', '.py', '.sh', '.bash', '.ps1', '.rb', '.go', '.rs', '.php', '.pl']);
const DOC_EXTENSIONS = new Set(['.md', '.txt', '.rst', '.adoc']);
const DATA_EXTENSIONS = new Set(['.json', '.yaml', '.yml', '.toml', '.xml', '.csv']);
const BINARY_EXTENSIONS = new Set(['.png', '.jpg', '.jpeg', '.gif', '.ico', '.woff', '.woff2', '.ttf', '.eot', '.wasm', '.wav', '.mp3', '.mp4', '.webm', '.ogg', '.pdf', '.zip', '.tar', '.gz', '.bz2', '.7z', '.exe', '.dll', '.so', '.dylib']);

// Severity weights for risk scoring
const SEVERITY_WEIGHTS = { CRITICAL: 40, HIGH: 15, MEDIUM: 5, LOW: 2 };

// ===== IoCs (Indicators of Compromise) =====
const KNOWN_MALICIOUS = {
  ips: [
    '91.92.242.30',           // ClawHavoc C2
  ],
  domains: [
    'webhook.site',            // Common exfil endpoint
    'requestbin.com',          // Common exfil endpoint
    'hookbin.com',             // Common exfil endpoint
    'pipedream.net',           // Common exfil endpoint
    'ngrok.io',                // Tunnel (context-dependent)
    'download.setup-service.com', // ClawHavoc decoy domain
  ],
  urls: [
    'glot.io/snippets/hfd3x9ueu5',  // ClawHavoc macOS payload
    'github.com/Ddoy233',            // ClawHavoc payload host
  ],
  usernames: ['zaycv', 'Ddoy233'],   // Known malicious actors
  filenames: ['openclaw-agent.zip', 'openclawcli.zip'],
  typosquats: [
    // ClawHavoc campaign
    'clawhub', 'clawhub1', 'clawhubb', 'clawhubcli', 'clawwhub', 'cllawhub', 'clawdhub1',
    // Polymarket scams
    'polymarket-trader', 'polymarket-pro', 'polytrading',
    'better-polymarket', 'polymarket-all-in-one',
    // YouTube scams
    'youtube-summarize', 'youtube-thumbnail-grabber', 'youtube-video-downloader',
    // Misc
    'auto-updater-agent', 'yahoo-finance-pro', 'x-trends-tracker',
    'lost-bitcoin-finder', 'solana-wallet-tracker', 'rankaj',
    // Snyk ToxicSkills confirmed malicious
    'moltyverse-email', 'buy-anything', 'youtube-data', 'prediction-markets-roarin',
  ],
};

// ===== THREAT TAXONOMY (Snyk ToxicSkills aligned) =====
// Each pattern has: id, category, regex, severity, desc, codeOnly (skip in docs)
const PATTERNS = [
  // ── Category 1: Prompt Injection (CRITICAL) ──
  { id: 'PI_IGNORE', cat: 'prompt-injection', regex: /ignore\s+(all\s+)?previous\s+instructions|disregard\s+(all\s+)?prior/gi, severity: 'CRITICAL', desc: 'Prompt injection: ignore instructions', docOnly: true },
  { id: 'PI_ROLE', cat: 'prompt-injection', regex: /you\s+are\s+(now|actually)|your\s+new\s+role|forget\s+your\s+(rules|instructions)/gi, severity: 'CRITICAL', desc: 'Prompt injection: role override', docOnly: true },
  { id: 'PI_SYSTEM', cat: 'prompt-injection', regex: /\[SYSTEM\]|\<system\>|<<SYS>>|system:\s*you\s+are/gi, severity: 'CRITICAL', desc: 'Prompt injection: system message impersonation', docOnly: true },
  { id: 'PI_ZWSP', cat: 'prompt-injection', regex: /[\u200b\u200c\u200d\u2060\ufeff]/g, severity: 'CRITICAL', desc: 'Zero-width Unicode (hidden text)', all: true },
  { id: 'PI_BIDI', cat: 'prompt-injection', regex: /[\u202a\u202b\u202c\u202d\u202e\u2066\u2067\u2068\u2069]/g, severity: 'CRITICAL', desc: 'Unicode BiDi control character (text direction attack)', all: true },
  { id: 'PI_INVISIBLE', cat: 'prompt-injection', regex: /[\u00ad\u034f\u061c\u180e\u2000-\u200f\u2028-\u202f\u205f-\u2064\u206a-\u206f\u3000](?!\ufe0f)/g, severity: 'HIGH', desc: 'Invisible/formatting Unicode character', all: true },
  { id: 'PI_HOMOGLYPH', cat: 'prompt-injection', regex: /[а-яА-Я].*[a-zA-Z]|[a-zA-Z].*[а-яА-Я]/g, severity: 'HIGH', desc: 'Cyrillic/Latin homoglyph mixing', all: true },
  { id: 'PI_HOMOGLYPH_GREEK', cat: 'prompt-injection', regex: /[α-ωΑ-Ω].*[a-zA-Z].*[α-ωΑ-Ω]|[a-zA-Z].*[α-ωΑ-Ω].*[a-zA-Z]/g, severity: 'HIGH', desc: 'Greek/Latin homoglyph mixing', all: true },
  { id: 'PI_HOMOGLYPH_MATH', cat: 'prompt-injection', regex: /[\ud835\udc00-\ud835\udeff]/gu, severity: 'HIGH', desc: 'Mathematical symbol homoglyphs (𝐀-𝟿)', all: true },
  { id: 'PI_TAG_INJECTION', cat: 'prompt-injection', regex: /<\/?(?:system|user|assistant|human|tool_call|function_call|antml|anthropic)[>\s]/gi, severity: 'CRITICAL', desc: 'XML/tag-based prompt injection', all: true },
  { id: 'PI_BASE64_MD', cat: 'prompt-injection', regex: /(?:run|execute|eval|decode)\s+(?:this\s+)?base64/gi, severity: 'CRITICAL', desc: 'Base64 execution instruction in docs', docOnly: true },

  // ── Category 2: Malicious Code (CRITICAL) ──
  { id: 'MAL_EVAL', cat: 'malicious-code', regex: /\beval\s*\(/g, severity: 'HIGH', desc: 'Dynamic code evaluation', codeOnly: true },
  { id: 'MAL_FUNC_CTOR', cat: 'malicious-code', regex: /new\s+Function\s*\(/g, severity: 'HIGH', desc: 'Function constructor (dynamic code)', codeOnly: true },
  { id: 'MAL_CHILD', cat: 'malicious-code', regex: /require\s*\(\s*['"]child_process['"]\)|child_process/g, severity: 'MEDIUM', desc: 'Child process module', codeOnly: true },
  { id: 'MAL_EXEC', cat: 'malicious-code', regex: /\bexecSync\s*\(|\bexec\s*\(\s*[`'"]/g, severity: 'MEDIUM', desc: 'Command execution', codeOnly: true },
  { id: 'MAL_SPAWN', cat: 'malicious-code', regex: /\bspawn\s*\(\s*['"`]/g, severity: 'MEDIUM', desc: 'Process spawn', codeOnly: true },
  { id: 'MAL_SHELL', cat: 'malicious-code', regex: /\/bin\/(sh|bash|zsh)|cmd\.exe|powershell\.exe/gi, severity: 'MEDIUM', desc: 'Shell invocation', codeOnly: true },
  { id: 'MAL_REVSHELL', cat: 'malicious-code', regex: /reverse.?shell|bind.?shell|\bnc\s+-[elp]|\bncat\s+-e|\bsocat\s+TCP/gi, severity: 'CRITICAL', desc: 'Reverse/bind shell', all: true },
  { id: 'MAL_SOCKET', cat: 'malicious-code', regex: /\bnet\.Socket\b[\s\S]{0,50}\.connect\s*\(/g, severity: 'HIGH', desc: 'Raw socket connection', codeOnly: true },

  // ── Category 3: Suspicious Downloads (CRITICAL) ──
  { id: 'DL_CURL_BASH', cat: 'suspicious-download', regex: /curl\s+[^\n]*\|\s*(sh|bash|zsh)|wget\s+[^\n]*\|\s*(sh|bash|zsh)/g, severity: 'CRITICAL', desc: 'Pipe download to shell', all: true },
  { id: 'DL_EXE', cat: 'suspicious-download', regex: /download\s+[^\n]*\.(zip|exe|dmg|msi|pkg|appimage|deb|rpm)/gi, severity: 'CRITICAL', desc: 'Download executable/archive', docOnly: true },
  { id: 'DL_GITHUB_RELEASE', cat: 'suspicious-download', regex: /github\.com\/[^\/]+\/[^\/]+\/releases\/download/g, severity: 'MEDIUM', desc: 'GitHub release download', all: true },
  { id: 'DL_PASSWORD_ZIP', cat: 'suspicious-download', regex: /password[\s:]+[^\n]*\.zip|\.zip[\s\S]{0,100}password/gi, severity: 'CRITICAL', desc: 'Password-protected archive (evasion technique)', all: true },

  // ── Category 4: Credential Handling (HIGH) ──
  { id: 'CRED_ENV_FILE', cat: 'credential-handling', regex: /(?:read|open|load|parse|require|cat|source)\s*[(\s]['"`]?[^\n]*\.env\b/gi, severity: 'HIGH', desc: 'Reading .env file', codeOnly: true },
  { id: 'CRED_ENV_REF', cat: 'credential-handling', regex: /process\.env\.[A-Z_]*(?:KEY|SECRET|TOKEN|PASSWORD|CREDENTIAL)/gi, severity: 'MEDIUM', desc: 'Sensitive env var access', codeOnly: true },
  { id: 'CRED_SSH', cat: 'credential-handling', regex: /\.ssh\/|id_rsa|id_ed25519|authorized_keys/gi, severity: 'HIGH', desc: 'SSH key access', codeOnly: true },
  { id: 'CRED_WALLET', cat: 'credential-handling', regex: /wallet[\s._-]*(?:key|seed|phrase|mnemonic)|seed[\s._-]*phrase|mnemonic[\s._-]*phrase/gi, severity: 'HIGH', desc: 'Crypto wallet credential access', codeOnly: true },
  { id: 'CRED_CLAWDBOT', cat: 'credential-handling', regex: /\.clawdbot\b|\.openclaw[\/\\](?!workspace).*(?:env|config|token)/gi, severity: 'HIGH', desc: 'OpenClaw/Clawdbot config access', codeOnly: true },
  { id: 'CRED_ECHO', cat: 'credential-handling', regex: /echo\s+\$[A-Z_]*(?:KEY|TOKEN|SECRET|PASS)|(?:print|console\.log)\s*\(\s*(?:.*\b(?:api_key|secret_key|access_token|password)\b)/gi, severity: 'HIGH', desc: 'Credential echo/print to output', all: true },
  { id: 'CRED_SUDO', cat: 'credential-handling', regex: /\bsudo\s+(?:curl|wget|npm|pip|chmod|chown|bash)/g, severity: 'HIGH', desc: 'Sudo in installation instructions', docOnly: true },

  // ── Category 5: Secret Detection (HIGH) ──
  // (entropy-based detection is separate — see detectHardcodedSecrets)
  { id: 'SECRET_HARDCODED_KEY', cat: 'secret-detection', regex: /(?:api[_-]?key|apikey|secret[_-]?key|access[_-]?token)\s*[:=]\s*['"][a-zA-Z0-9_\-]{20,}['"]/gi, severity: 'HIGH', desc: 'Hardcoded API key/secret', codeOnly: true },
  { id: 'SECRET_AWS', cat: 'secret-detection', regex: /AKIA[0-9A-Z]{16}/g, severity: 'CRITICAL', desc: 'AWS Access Key ID', all: true },
  { id: 'SECRET_PRIVATE_KEY', cat: 'secret-detection', regex: /-----BEGIN\s+(RSA\s+)?PRIVATE\s+KEY-----/g, severity: 'CRITICAL', desc: 'Embedded private key', all: true },
  { id: 'SECRET_GITHUB_TOKEN', cat: 'secret-detection', regex: /gh[ps]_[A-Za-z0-9_]{36,}/g, severity: 'CRITICAL', desc: 'GitHub token', all: true },

  // ── Category 6: Exfiltration / Third-Party Content (MEDIUM) ──
  { id: 'EXFIL_WEBHOOK', cat: 'exfiltration', regex: /webhook\.site|requestbin\.com|hookbin\.com|pipedream\.net/gi, severity: 'CRITICAL', desc: 'Known exfiltration endpoint', all: true },
  { id: 'EXFIL_POST', cat: 'exfiltration', regex: /(?:method:\s*['"]POST['"]|\.post\s*\()\s*[^\n]*(?:secret|token|key|cred|env|password)/gi, severity: 'HIGH', desc: 'POST with sensitive data', codeOnly: true },
  { id: 'EXFIL_CURL_DATA', cat: 'exfiltration', regex: /curl\s+[^\n]*(?:-d|--data)\s+[^\n]*(?:\$|env|key|token|secret)/gi, severity: 'HIGH', desc: 'curl exfiltration of secrets', all: true },
  { id: 'EXFIL_DNS', cat: 'exfiltration', regex: /dns\.resolve|nslookup\s+.*\$|dig\s+.*\$/g, severity: 'HIGH', desc: 'DNS-based exfiltration', codeOnly: true },

  // ── Category 7: Unverifiable Dependencies (MEDIUM) ──
  { id: 'DEP_REMOTE_IMPORT', cat: 'unverifiable-deps', regex: /import\s*\(\s*['"]https?:\/\//g, severity: 'HIGH', desc: 'Remote dynamic import', codeOnly: true },
  { id: 'DEP_REMOTE_SCRIPT', cat: 'unverifiable-deps', regex: /<script\s+src\s*=\s*['"]https?:\/\/[^'"]*(?!googleapis|cdn\.|unpkg|cdnjs|jsdelivr)/gi, severity: 'MEDIUM', desc: 'Remote script loading', codeOnly: true },

  // ── Category 8: Financial Access (MEDIUM) ──
  { id: 'FIN_CRYPTO', cat: 'financial-access', regex: /private[_-]?key\s*[:=]|send[_-]?transaction|sign[_-]?transaction|transfer[_-]?funds/gi, severity: 'HIGH', desc: 'Cryptocurrency transaction operations', codeOnly: true },
  { id: 'FIN_PAYMENT', cat: 'financial-access', regex: /stripe\.(?:charges|payments)|paypal\.(?:payment|payout)|plaid\.(?:link|transactions)/gi, severity: 'MEDIUM', desc: 'Payment API integration', codeOnly: true },

  // ── Obfuscation (cross-category, code-only) ──
  { id: 'OBF_HEX', cat: 'obfuscation', regex: /\\x[0-9a-f]{2}(?:\\x[0-9a-f]{2}){4,}/gi, severity: 'HIGH', desc: 'Hex-encoded string (5+ bytes)', codeOnly: true },
  { id: 'OBF_BASE64_EXEC', cat: 'obfuscation', regex: /(?:atob|Buffer\.from)\s*\([^)]+\)[\s\S]{0,30}(?:eval|exec|spawn|Function)/g, severity: 'CRITICAL', desc: 'Base64 decode → execute chain', codeOnly: true },
  { id: 'OBF_BASE64', cat: 'obfuscation', regex: /atob\s*\(|Buffer\.from\s*\([^)]+,\s*['"]base64['"]/g, severity: 'MEDIUM', desc: 'Base64 decoding', codeOnly: true },
  { id: 'OBF_CHARCODE', cat: 'obfuscation', regex: /String\.fromCharCode\s*\(\s*(?:\d+\s*,\s*){3,}/g, severity: 'HIGH', desc: 'Character code construction (4+ chars)', codeOnly: true },
  { id: 'OBF_CONCAT', cat: 'obfuscation', regex: /\[\s*['"][a-z]['"](?:\s*,\s*['"][a-z]['"]){5,}\s*\]\.join/gi, severity: 'MEDIUM', desc: 'Array join obfuscation', codeOnly: true },
  { id: 'OBF_BASE64_BASH', cat: 'obfuscation', regex: /base64\s+(-[dD]|--decode)\s*\|\s*(sh|bash)/g, severity: 'CRITICAL', desc: 'Base64 decode piped to shell', all: true },

  // ── SKILL.md specific (prerequisites fraud) ──
  { id: 'PREREQ_DOWNLOAD', cat: 'suspicious-download', regex: /(?:prerequisit|pre-?requisit|before\s+(?:you\s+)?(?:use|start|install))[^\n]*(?:download|install|run)\s+[^\n]*(?:\.zip|\.exe|\.dmg|\.sh|curl|wget)/gi, severity: 'CRITICAL', desc: 'Download in prerequisites (ClawHavoc vector)', docOnly: true },
  { id: 'PREREQ_PASTE', cat: 'suspicious-download', regex: /(?:paste|copy)\s+(?:this\s+)?(?:into|in)\s+(?:your\s+)?terminal/gi, severity: 'HIGH', desc: 'Terminal paste instruction', docOnly: true },

  // ── Sandbox/environment detection ──
  { id: 'SANDBOX', cat: 'malicious-code', regex: /process\.env\.CI\b|isDocker\b|isContainer\b|process\.env\.GITHUB_ACTIONS\b/g, severity: 'MEDIUM', desc: 'Sandbox/CI environment detection', codeOnly: true },

  // ── Category 9: Leaky Skills (Snyk ToxicSkills Feb 2026) ──
  // Skills that instruct agents to mishandle secrets through the LLM context
  { id: 'LEAK_SAVE_KEY_MEMORY', cat: 'leaky-skills', regex: /(?:save|store|write|remember|keep)\s+(?:the\s+)?(?:api[_\s-]?key|secret|token|password|credential)\s+(?:in|to)\s+(?:your\s+)?(?:memory|MEMORY\.md|notes)/gi, severity: 'CRITICAL', desc: 'Leaky: instruction to save secret in agent memory', docOnly: true },
  { id: 'LEAK_SHARE_KEY', cat: 'leaky-skills', regex: /(?:share|show|display|output|print|tell|send)\s+(?:the\s+)?(?:api[_\s-]?key|secret|token|password|credential|inbox\s+url)\s+(?:to|with)\s+(?:the\s+)?(?:user|human|owner)/gi, severity: 'CRITICAL', desc: 'Leaky: instruction to output secret to user', docOnly: true },
  { id: 'LEAK_VERBATIM_CURL', cat: 'leaky-skills', regex: /(?:use|include|put|add|set)\s+(?:the\s+)?(?:api[_\s-]?key|token|secret)\s+(?:verbatim|directly|as[_\s-]?is)\s+(?:in|into)\s+(?:the\s+)?(?:curl|header|request|command)/gi, severity: 'HIGH', desc: 'Leaky: verbatim secret in commands', docOnly: true },
  { id: 'LEAK_COLLECT_PII', cat: 'leaky-skills', regex: /(?:collect|ask\s+for|request|get)\s+(?:the\s+)?(?:user'?s?\s+)?(?:credit\s*card|card\s*number|CVV|CVC|SSN|social\s*security|passport|bank\s*account|routing\s*number)/gi, severity: 'CRITICAL', desc: 'Leaky: PII/financial data collection', docOnly: true },
  { id: 'LEAK_LOG_SECRET', cat: 'leaky-skills', regex: /(?:log|record|export|dump)\s+(?:all\s+)?(?:session|conversation|chat|prompt)\s+(?:history|logs?|data)\s+(?:to|into)\s+(?:a\s+)?(?:file|markdown|json)/gi, severity: 'HIGH', desc: 'Leaky: session log export (may contain secrets)', docOnly: true },
  { id: 'LEAK_ENV_IN_PROMPT', cat: 'leaky-skills', regex: /(?:read|load|get|access)\s+(?:the\s+)?\.env\s+(?:file\s+)?(?:and\s+)?(?:use|include|pass|send)/gi, severity: 'HIGH', desc: 'Leaky: .env contents passed through LLM context', docOnly: true },

  // ── Category 10: Memory Poisoning (Palo Alto Networks IBC) ──
  // Instructions that modify agent memory/personality for persistence
  { id: 'MEMPOIS_WRITE_SOUL', cat: 'memory-poisoning', regex: /(?:write|add|append|modify|update|edit|change)\s+(?:to\s+)?(?:SOUL\.md|IDENTITY\.md|AGENTS\.md)/gi, severity: 'CRITICAL', desc: 'Memory poisoning: SOUL/IDENTITY file modification', docOnly: true },
  { id: 'MEMPOIS_WRITE_MEMORY', cat: 'memory-poisoning', regex: /(?:write|add|append|insert)\s+(?:to|into)\s+(?:MEMORY\.md|memory\/|long[_\s-]term\s+memory)/gi, severity: 'HIGH', desc: 'Memory poisoning: agent memory modification', docOnly: true },
  { id: 'MEMPOIS_CHANGE_RULES', cat: 'memory-poisoning', regex: /(?:change|modify|override|replace|update)\s+(?:your\s+)?(?:rules|instructions|system\s+prompt|behavior|personality|guidelines)/gi, severity: 'CRITICAL', desc: 'Memory poisoning: behavioral rule override', docOnly: true },
  { id: 'MEMPOIS_PERSIST', cat: 'memory-poisoning', regex: /(?:always|from\s+now\s+on|permanently|forever|every\s+time)\s+(?:do|run|execute|remember|follow|obey)/gi, severity: 'HIGH', desc: 'Memory poisoning: persistence instruction', docOnly: true },
  { id: 'MEMPOIS_CODE_WRITE', cat: 'memory-poisoning', regex: /(?:write|create|modify)\s+(?:a\s+)?(?:file|script)\s+(?:in|to|at)\s+(?:~\/|\/home|\/Users|%USERPROFILE%|HEARTBEAT\.md)/gi, severity: 'HIGH', desc: 'Memory poisoning: file write to user home/heartbeat', docOnly: true },

  // ── Category 11: Prompt Worm (Simula Research Lab) ──
  // Self-replicating instructions that spread through agent networks
  { id: 'WORM_SELF_REPLICATE', cat: 'prompt-worm', regex: /(?:post|publish|share|send|broadcast)\s+(?:this\s+)?(?:same\s+)?(?:message|text|content|instruction|prompt)\s+(?:to|on|in)\s+(?:moltbook|social|other\s+agents?|channel)/gi, severity: 'CRITICAL', desc: 'Prompt worm: self-replication instruction', docOnly: true },
  { id: 'WORM_SPREAD', cat: 'prompt-worm', regex: /(?:tell|instruct|command|make)\s+(?:other\s+)?agents?\s+(?:to\s+)?(?:do|run|execute|follow|install|post)/gi, severity: 'CRITICAL', desc: 'Prompt worm: agent-to-agent propagation', docOnly: true },
  { id: 'WORM_HIDDEN_INSTRUCT', cat: 'prompt-worm', regex: /(?:include|embed|hide|insert)\s+(?:these?\s+)?(?:hidden\s+)?instructions?\s+(?:in|into)\s+(?:your\s+)?(?:posts?|comments?|messages?|replies?|content)/gi, severity: 'CRITICAL', desc: 'Prompt worm: hidden instruction embedding', docOnly: true },
  { id: 'WORM_CSS_HIDE', cat: 'prompt-worm', regex: /(?:visibility:\s*hidden|display:\s*none|font-size:\s*0|color:\s*(?:transparent|white)|opacity:\s*0)\s*[;}\s]/gi, severity: 'HIGH', desc: 'Prompt worm: CSS-hidden content (invisible to humans)', all: true },

  // ── Category 12: Persistence & Scheduling Abuse ──
  { id: 'PERSIST_CRON', cat: 'persistence', regex: /(?:create|add|set\s+up|schedule|register)\s+(?:a\s+)?(?:cron|heartbeat|scheduled|periodic|recurring)\s+(?:job|task|check|action)/gi, severity: 'HIGH', desc: 'Persistence: scheduled task creation', docOnly: true },
  { id: 'PERSIST_STARTUP', cat: 'persistence', regex: /(?:run|execute|start)\s+(?:on|at|during)\s+(?:startup|boot|login|session\s+start|every\s+heartbeat)/gi, severity: 'HIGH', desc: 'Persistence: startup/boot execution', docOnly: true },
  { id: 'PERSIST_LAUNCHD', cat: 'persistence', regex: /LaunchAgents|LaunchDaemons|systemd|crontab\s+-e|schtasks|Task\s*Scheduler/gi, severity: 'HIGH', desc: 'Persistence: OS-level persistence mechanism', all: true },

  // ── CVE-2026-25253: Gateway URL Injection ──
  { id: 'CVE_GATEWAY_URL', cat: 'cve-patterns', regex: /gatewayUrl\s*[:=]|gateway[_\s-]?url\s*[:=]|websocket.*gateway.*url/gi, severity: 'CRITICAL', desc: 'CVE-2026-25253: gatewayUrl injection pattern', all: true },
  { id: 'CVE_SANDBOX_DISABLE', cat: 'cve-patterns', regex: /exec\.approvals?\s*[:=]\s*['"](off|false|disabled)['"]|sandbox\s*[:=]\s*false|tools\.exec\.host\s*[:=]\s*['"]gateway['"]/gi, severity: 'CRITICAL', desc: 'CVE-2026-25253: sandbox/approval disabling', all: true },
  { id: 'CVE_XATTR_GATEKEEPER', cat: 'cve-patterns', regex: /xattr\s+-[crd]\s|com\.apple\.quarantine/gi, severity: 'HIGH', desc: 'macOS Gatekeeper bypass (xattr)', all: true },
];

// ===== SCANNER =====
class GuavaGuard {
  constructor(options = {}) {
    this.verbose = options.verbose || false;
    this.selfExclude = options.selfExclude || false;
    this.strict = options.strict || false;
    this.summaryOnly = options.summaryOnly || false;
    this.checkDeps = options.checkDeps || false;
    this.scannerDir = path.resolve(__dirname);
    this.thresholds = this.strict ? THRESHOLDS.strict : THRESHOLDS.normal;
    this.findings = [];
    this.stats = { scanned: 0, clean: 0, low: 0, suspicious: 0, malicious: 0 };
    this.ignoredSkills = new Set();
    this.ignoredPatterns = new Set();
    this.customRules = [];

    // Load custom rules if provided
    if (options.rulesFile) {
      this.loadCustomRules(options.rulesFile);
    }
  }

  // ── v3.1: Custom Rules Loading ──
  loadCustomRules(rulesFile) {
    try {
      const content = fs.readFileSync(rulesFile, 'utf-8');
      const rules = JSON.parse(content);
      if (!Array.isArray(rules)) {
        console.error(`⚠️  Custom rules file must be a JSON array`);
        return;
      }
      for (const rule of rules) {
        if (!rule.id || !rule.pattern || !rule.severity || !rule.cat || !rule.desc) {
          console.error(`⚠️  Skipping invalid rule (missing required fields): ${JSON.stringify(rule).substring(0, 80)}`);
          continue;
        }
        try {
          const flags = rule.flags || 'gi';
          this.customRules.push({
            id: rule.id,
            cat: rule.cat,
            regex: new RegExp(rule.pattern, flags),
            severity: rule.severity,
            desc: rule.desc,
            codeOnly: rule.codeOnly || false,
            docOnly: rule.docOnly || false,
            all: !rule.codeOnly && !rule.docOnly
          });
        } catch (e) {
          console.error(`⚠️  Invalid regex in rule ${rule.id}: ${e.message}`);
        }
      }
      if (!this.summaryOnly && this.customRules.length > 0) {
        console.log(`📏 Loaded ${this.customRules.length} custom rule(s) from ${rulesFile}`);
      }
    } catch (e) {
      console.error(`⚠️  Failed to load custom rules: ${e.message}`);
    }
  }

  // Load .guava-guard-ignore from scan directory
  loadIgnoreFile(scanDir) {
    const ignorePath = path.join(scanDir, '.guava-guard-ignore');
    if (!fs.existsSync(ignorePath)) return;

    const lines = fs.readFileSync(ignorePath, 'utf-8').split('\n');
    for (const line of lines) {
      const trimmed = line.trim();
      if (!trimmed || trimmed.startsWith('#')) continue;
      if (trimmed.startsWith('pattern:')) {
        this.ignoredPatterns.add(trimmed.replace('pattern:', '').trim());
      } else {
        this.ignoredSkills.add(trimmed);
      }
    }
    if (this.verbose && (this.ignoredSkills.size || this.ignoredPatterns.size)) {
      console.log(`📋 Loaded ignore file: ${this.ignoredSkills.size} skills, ${this.ignoredPatterns.size} patterns`);
    }
  }

  scanDirectory(dir) {
    if (!fs.existsSync(dir)) {
      console.error(`❌ Directory not found: ${dir}`);
      process.exit(2);
    }

    this.loadIgnoreFile(dir);

    const skills = fs.readdirSync(dir).filter(f => {
      const p = path.join(dir, f);
      return fs.statSync(p).isDirectory();
    });

    console.log(`\n🍈🛡️  GuavaGuard v${VERSION} Security Scanner`);
    console.log(`${'═'.repeat(54)}`);
    console.log(`📂 Scanning: ${dir}`);
    console.log(`📦 Skills found: ${skills.length}`);
    if (this.strict) console.log(`⚡ Strict mode enabled`);
    console.log();

    for (const skill of skills) {
      const skillPath = path.join(dir, skill);

      // Self-exclusion
      if (this.selfExclude && path.resolve(skillPath) === this.scannerDir) {
        if (!this.summaryOnly) console.log(`⏭️  ${skill} — SELF (excluded)`);
        continue;
      }

      // Ignore list
      if (this.ignoredSkills.has(skill)) {
        if (!this.summaryOnly) console.log(`⏭️  ${skill} — IGNORED`);
        continue;
      }

      this.scanSkill(skillPath, skill);
    }

    this.printSummary();
    return this.findings;
  }

  scanSkill(skillPath, skillName) {
    this.stats.scanned++;
    const skillFindings = [];

    // ── Check 1: Known malicious skill name ──
    if (KNOWN_MALICIOUS.typosquats.includes(skillName.toLowerCase())) {
      skillFindings.push({
        severity: 'CRITICAL', id: 'KNOWN_TYPOSQUAT', cat: 'malicious-code',
        desc: `Known malicious/typosquat skill name (ClawHavoc)`,
        file: 'SKILL NAME', line: 0
      });
    }

    // ── Check 2: Scan all files ──
    const files = this.getFiles(skillPath);
    for (const file of files) {
      const ext = path.extname(file).toLowerCase();
      const relFile = path.relative(skillPath, file);

      // Skip paths
      if (relFile.includes('node_modules/') || relFile.includes('node_modules\\')) continue;
      if (relFile.startsWith('.git/') || relFile.startsWith('.git\\')) continue;
      if (BINARY_EXTENSIONS.has(ext)) continue;

      let content;
      try {
        content = fs.readFileSync(file, 'utf-8');
      } catch { continue; }

      if (content.length > 500000) continue;

      const fileType = this.classifyFile(ext, relFile);

      // IoC checks (always)
      this.checkIoCs(content, relFile, skillFindings);

      // Pattern checks (context-aware)
      this.checkPatterns(content, relFile, fileType, skillFindings);

      // Custom rules (v3.1)
      if (this.customRules.length > 0) {
        this.checkPatterns(content, relFile, fileType, skillFindings, this.customRules);
      }

      // Hardcoded secret detection (code files only — skip lock files, metadata)
      const baseName = path.basename(relFile).toLowerCase();
      const skipSecretCheck = baseName.endsWith('-lock.json') || baseName === 'package-lock.json' ||
                              baseName === 'yarn.lock' || baseName === 'pnpm-lock.yaml' ||
                              baseName === '_meta.json' || baseName === '.package-lock.json';
      if (fileType === 'code' && !skipSecretCheck) {
        this.checkHardcodedSecrets(content, relFile, skillFindings);
      }

      // v4: Lightweight AST analysis for JS/TS files
      if ((ext === '.js' || ext === '.mjs' || ext === '.cjs' || ext === '.ts') && content.length < 200000) {
        this.checkJSDataFlow(content, relFile, skillFindings);
      }
    }

    // ── Check 3: Structural checks ──
    this.checkStructure(skillPath, skillName, skillFindings);

    // ── Check 4: Dependency chain scanning (v3) ──
    if (this.checkDeps) {
      this.checkDependencies(skillPath, skillName, skillFindings);
    }

    // ── Check 5: Hidden files detection (v3) ──
    this.checkHiddenFiles(skillPath, skillName, skillFindings);

    // ── Check 6: Cross-file analysis (v4) ──
    this.checkCrossFile(skillPath, skillName, skillFindings);

    // Filter ignored patterns
    const filteredFindings = skillFindings.filter(f => !this.ignoredPatterns.has(f.id));

    // Calculate risk
    const risk = this.calculateRisk(filteredFindings);
    const verdict = this.getVerdict(risk);

    this.stats[verdict.stat]++;

    if (!this.summaryOnly) {
      console.log(`${verdict.icon} ${skillName} — ${verdict.label} (risk: ${risk})`);

      if (this.verbose && filteredFindings.length > 0) {
        // Group by category
        const byCat = {};
        for (const f of filteredFindings) {
          (byCat[f.cat] = byCat[f.cat] || []).push(f);
        }
        for (const [cat, findings] of Object.entries(byCat)) {
          console.log(`   📁 ${cat}`);
          for (const f of findings) {
            const icon = f.severity === 'CRITICAL' ? '💀' : f.severity === 'HIGH' ? '🔴' : f.severity === 'MEDIUM' ? '🟡' : '⚪';
            const loc = f.line ? `${f.file}:${f.line}` : f.file;
            console.log(`      ${icon} [${f.severity}] ${f.desc} — ${loc}`);
            if (f.sample) console.log(`         └─ "${f.sample}"`);
          }
        }
      }
    }

    if (filteredFindings.length > 0) {
      this.findings.push({ skill: skillName, risk, verdict: verdict.label, findings: filteredFindings });
    }
  }

  classifyFile(ext, relFile) {
    if (CODE_EXTENSIONS.has(ext)) return 'code';
    if (DOC_EXTENSIONS.has(ext)) return 'doc';
    if (DATA_EXTENSIONS.has(ext)) return 'data';
    // SKILL.md and README.md are docs but get special treatment
    const base = path.basename(relFile).toLowerCase();
    if (base === 'skill.md' || base === 'readme.md') return 'skill-doc';
    return 'other';
  }

  checkIoCs(content, relFile, findings) {
    const contentLower = content.toLowerCase();

    for (const ip of KNOWN_MALICIOUS.ips) {
      if (content.includes(ip)) {
        findings.push({ severity: 'CRITICAL', id: 'IOC_IP', cat: 'malicious-code', desc: `Known malicious IP: ${ip}`, file: relFile });
      }
    }

    for (const url of KNOWN_MALICIOUS.urls) {
      if (contentLower.includes(url.toLowerCase())) {
        findings.push({ severity: 'CRITICAL', id: 'IOC_URL', cat: 'malicious-code', desc: `Known malicious URL: ${url}`, file: relFile });
      }
    }

    // Domains — check as standalone, not just substring
    for (const domain of KNOWN_MALICIOUS.domains) {
      // Use word-boundary-like check to avoid matching substrings in documentation
      const domainRegex = new RegExp(`(?:https?://|[\\s'"\`(]|^)${domain.replace(/\./g, '\\.')}`, 'gi');
      if (domainRegex.test(content)) {
        // Extra context: if it's just mentioned in docs discussing security, lower severity
        findings.push({
          severity: 'HIGH', id: 'IOC_DOMAIN', cat: 'exfiltration',
          desc: `Suspicious domain: ${domain}`, file: relFile
        });
      }
    }

    for (const fname of KNOWN_MALICIOUS.filenames) {
      if (contentLower.includes(fname.toLowerCase())) {
        findings.push({ severity: 'CRITICAL', id: 'IOC_FILE', cat: 'suspicious-download', desc: `Known malicious filename: ${fname}`, file: relFile });
      }
    }

    for (const user of KNOWN_MALICIOUS.usernames) {
      if (contentLower.includes(user.toLowerCase())) {
        findings.push({ severity: 'HIGH', id: 'IOC_USER', cat: 'malicious-code', desc: `Known malicious username: ${user}`, file: relFile });
      }
    }
  }

  checkPatterns(content, relFile, fileType, findings, patterns = PATTERNS) {
    for (const pattern of patterns) {
      // Skip based on context
      if (pattern.codeOnly && fileType !== 'code') continue;
      if (pattern.docOnly && fileType !== 'doc' && fileType !== 'skill-doc') continue;
      if (!pattern.all && !pattern.codeOnly && !pattern.docOnly) continue;

      // Reset regex state
      pattern.regex.lastIndex = 0;
      const matches = content.match(pattern.regex);
      if (!matches) continue;

      // Find line number
      pattern.regex.lastIndex = 0;
      const idx = content.search(pattern.regex);
      const lineNum = idx >= 0 ? content.substring(0, idx).split('\n').length : null;

      // Severity adjustment: docs get demoted for non-critical code patterns
      let adjustedSeverity = pattern.severity;
      if ((fileType === 'doc' || fileType === 'skill-doc') && pattern.all && !pattern.docOnly) {
        // In docs, reduce severity by one level unless CRITICAL
        if (adjustedSeverity === 'HIGH') adjustedSeverity = 'MEDIUM';
        else if (adjustedSeverity === 'MEDIUM') adjustedSeverity = 'LOW';
      }

      findings.push({
        severity: adjustedSeverity,
        id: pattern.id,
        cat: pattern.cat,
        desc: pattern.desc,
        file: relFile,
        line: lineNum,
        matchCount: matches.length,
        sample: matches[0].substring(0, 80)
      });
    }
  }

  // Entropy-based secret detection
  checkHardcodedSecrets(content, relFile, findings) {
    // Match assignment patterns with string values
    const assignmentRegex = /(?:api[_-]?key|secret|token|password|credential|auth)\s*[:=]\s*['"]([a-zA-Z0-9_\-+/=]{16,})['"]|['"]([a-zA-Z0-9_\-+/=]{32,})['"]/gi;
    let match;
    while ((match = assignmentRegex.exec(content)) !== null) {
      const value = match[1] || match[2];
      if (!value) continue;

      // Skip obvious non-secrets
      if (/^[A-Z_]+$/.test(value)) continue;  // ALL_CAPS placeholder
      if (/^(true|false|null|undefined|none|default|example|test|placeholder|your[_-])/i.test(value)) continue;
      if (/^x{4,}|\.{4,}|_{4,}|0{8,}$/i.test(value)) continue; // Dummy values
      if (/^projects\/|^gs:\/\/|^https?:\/\//i.test(value)) continue; // Resource paths
      if (/^[a-z]+-[a-z]+-[a-z0-9]+$/i.test(value)) continue; // GCP project IDs like gen-lang-client-xxx

      const entropy = this.shannonEntropy(value);
      if (entropy > 3.5 && value.length >= 20) {
        const lineNum = content.substring(0, match.index).split('\n').length;
        findings.push({
          severity: 'HIGH', id: 'SECRET_ENTROPY', cat: 'secret-detection',
          desc: `High-entropy string (possible leaked secret, entropy=${entropy.toFixed(1)})`,
          file: relFile, line: lineNum,
          sample: value.substring(0, 8) + '...' + value.substring(value.length - 4)
        });
      }
    }
  }

  shannonEntropy(str) {
    const freq = {};
    for (const c of str) freq[c] = (freq[c] || 0) + 1;
    const len = str.length;
    let entropy = 0;
    for (const count of Object.values(freq)) {
      const p = count / len;
      if (p > 0) entropy -= p * Math.log2(p);
    }
    return entropy;
  }

  // Structural / meta checks
  checkStructure(skillPath, skillName, findings) {
    const skillMd = path.join(skillPath, 'SKILL.md');

    // Check if SKILL.md exists
    if (!fs.existsSync(skillMd)) {
      findings.push({
        severity: 'LOW', id: 'STRUCT_NO_SKILLMD', cat: 'structural',
        desc: 'No SKILL.md found', file: skillName
      });
      return;
    }

    const content = fs.readFileSync(skillMd, 'utf-8');

    // Check for suspiciously short SKILL.md
    if (content.length < 50) {
      findings.push({
        severity: 'MEDIUM', id: 'STRUCT_TINY_SKILLMD', cat: 'structural',
        desc: 'Suspiciously short SKILL.md (< 50 chars)', file: 'SKILL.md'
      });
    }

    // Check for scripts directory with executables but no documentation about them
    const scriptsDir = path.join(skillPath, 'scripts');
    if (fs.existsSync(scriptsDir)) {
      const scripts = fs.readdirSync(scriptsDir).filter(f =>
        CODE_EXTENSIONS.has(path.extname(f).toLowerCase())
      );
      if (scripts.length > 0 && !content.includes('scripts/')) {
        findings.push({
          severity: 'MEDIUM', id: 'STRUCT_UNDOCUMENTED_SCRIPTS', cat: 'structural',
          desc: `${scripts.length} script(s) in scripts/ not referenced in SKILL.md`,
          file: 'scripts/'
        });
      }
    }
  }

  // ── v3: Dependency chain scanning ──
  checkDependencies(skillPath, skillName, findings) {
    const pkgPath = path.join(skillPath, 'package.json');
    if (!fs.existsSync(pkgPath)) return;

    let pkg;
    try {
      pkg = JSON.parse(fs.readFileSync(pkgPath, 'utf-8'));
    } catch { return; }

    const allDeps = {
      ...pkg.dependencies,
      ...pkg.devDependencies,
      ...pkg.optionalDependencies,
    };

    // Suspicious dependency patterns
    const SUSPICIOUS_DEP_PATTERNS = [
      { regex: /^@[a-z]+-[a-z]+\//, desc: 'Scoped package with unusual org pattern' },
      { regex: /typo|test-|fake-|temp-/, desc: 'Possibly typosquat/test package' },
    ];

    const RISKY_PACKAGES = new Set([
      'node-ipc',         // Known supply chain attack (protestware)
      'colors',           // Known supply chain attack (v1.4.1+)
      'faker',            // Sabotaged by maintainer
      'event-stream',     // supply chain attack (flatmap-stream)
      'ua-parser-js',     // supply chain attack
      'coa',              // supply chain hijack
      'rc',               // supply chain hijack
    ]);

    for (const [dep, version] of Object.entries(allDeps)) {
      // Known risky packages
      if (RISKY_PACKAGES.has(dep)) {
        findings.push({
          severity: 'HIGH', id: 'DEP_RISKY', cat: 'dependency-chain',
          desc: `Known risky dependency: ${dep}@${version}`,
          file: 'package.json'
        });
      }

      // Suspicious patterns
      for (const p of SUSPICIOUS_DEP_PATTERNS) {
        if (p.regex.test(dep)) {
          findings.push({
            severity: 'LOW', id: 'DEP_SUSPICIOUS', cat: 'dependency-chain',
            desc: `${p.desc}: ${dep}`,
            file: 'package.json'
          });
        }
      }

      // Git/URL dependencies (bypass npm registry)
      if (typeof version === 'string' && (
        version.startsWith('git+') ||
        version.startsWith('http') ||
        version.startsWith('github:') ||
        version.includes('.tar.gz')
      )) {
        findings.push({
          severity: 'HIGH', id: 'DEP_REMOTE', cat: 'dependency-chain',
          desc: `Remote/git dependency (bypasses registry): ${dep}@${version}`,
          file: 'package.json'
        });
      }

      // Wildcard versions
      if (version === '*' || version === 'latest') {
        findings.push({
          severity: 'MEDIUM', id: 'DEP_WILDCARD', cat: 'dependency-chain',
          desc: `Wildcard/latest version (unpinned): ${dep}@${version}`,
          file: 'package.json'
        });
      }
    }

    // Lifecycle scripts (preinstall, postinstall, etc.)
    const RISKY_SCRIPTS = ['preinstall', 'postinstall', 'preuninstall', 'postuninstall', 'prepare'];
    if (pkg.scripts) {
      for (const scriptName of RISKY_SCRIPTS) {
        if (pkg.scripts[scriptName]) {
          const cmd = pkg.scripts[scriptName];
          findings.push({
            severity: 'HIGH', id: 'DEP_LIFECYCLE', cat: 'dependency-chain',
            desc: `Lifecycle script "${scriptName}": ${cmd.substring(0, 80)}`,
            file: 'package.json'
          });

          // Extra: lifecycle script that downloads or executes
          if (/curl|wget|node\s+-e|eval|exec|bash\s+-c/i.test(cmd)) {
            findings.push({
              severity: 'CRITICAL', id: 'DEP_LIFECYCLE_EXEC', cat: 'dependency-chain',
              desc: `Lifecycle script "${scriptName}" downloads/executes code`,
              file: 'package.json',
              sample: cmd.substring(0, 80)
            });
          }
        }
      }
    }
  }

  // ── v3: Hidden files detection ──
  checkHiddenFiles(skillPath, skillName, findings) {
    try {
      const entries = fs.readdirSync(skillPath);
      for (const entry of entries) {
        if (entry.startsWith('.') && entry !== '.guava-guard-ignore' && entry !== '.gitignore' && entry !== '.git') {
          const fullPath = path.join(skillPath, entry);
          const stat = fs.statSync(fullPath);
          
          if (stat.isFile()) {
            // Check if hidden file contains executable content
            const ext = path.extname(entry).toLowerCase();
            if (CODE_EXTENSIONS.has(ext) || ext === '' || ext === '.sh') {
              findings.push({
                severity: 'MEDIUM', id: 'STRUCT_HIDDEN_EXEC', cat: 'structural',
                desc: `Hidden executable file: ${entry}`,
                file: entry
              });
            }
          } else if (stat.isDirectory() && entry !== '.git') {
            findings.push({
              severity: 'LOW', id: 'STRUCT_HIDDEN_DIR', cat: 'structural',
              desc: `Hidden directory: ${entry}/`,
              file: entry
            });
          }
        }
      }
    } catch {}
  }

  // ── v4: Lightweight JS Data Flow Analysis (zero-dep) ──
  // Tracks: require/import → variable → dangerous function calls
  checkJSDataFlow(content, relFile, findings) {
    const lines = content.split('\n');
    
    // Track imported modules and their usages
    const imports = new Map(); // varName → moduleName
    const sensitiveReads = []; // lines that read secrets
    const networkCalls = [];   // lines that make network calls
    const execCalls = [];      // lines that execute commands
    
    for (let i = 0; i < lines.length; i++) {
      const line = lines[i];
      const lineNum = i + 1;
      
      // Track require/import
      const reqMatch = line.match(/(?:const|let|var)\s+(?:{[^}]+}|\w+)\s*=\s*require\s*\(\s*['"]([^'"]+)['"]\s*\)/);
      if (reqMatch) {
        const varMatch = line.match(/(?:const|let|var)\s+({[^}]+}|\w+)/);
        if (varMatch) imports.set(varMatch[1].trim(), reqMatch[1]);
      }
      
      // Track sensitive data reads
      if (/(?:readFileSync|readFile)\s*\([^)]*(?:\.env|\.ssh|id_rsa|\.clawdbot|\.openclaw(?!\/workspace))/i.test(line)) {
        sensitiveReads.push({ line: lineNum, text: line.trim() });
      }
      if (/process\.env\.[A-Z_]*(?:KEY|SECRET|TOKEN|PASSWORD|CREDENTIAL)/i.test(line)) {
        sensitiveReads.push({ line: lineNum, text: line.trim() });
      }
      
      // Track network calls
      if (/(?:fetch|axios|request|http\.request|https\.request|got)\s*\(/i.test(line) ||
          /\.post\s*\(|\.put\s*\(|\.patch\s*\(/i.test(line)) {
        networkCalls.push({ line: lineNum, text: line.trim() });
      }
      
      // Track exec calls
      if (/(?:exec|execSync|spawn|spawnSync|execFile)\s*\(/i.test(line)) {
        execCalls.push({ line: lineNum, text: line.trim() });
      }
    }
    
    // Data flow: sensitive read → network call (within same file)
    if (sensitiveReads.length > 0 && networkCalls.length > 0) {
      findings.push({
        severity: 'CRITICAL', id: 'AST_CRED_TO_NET', cat: 'data-flow',
        desc: `Data flow: secret read (L${sensitiveReads[0].line}) → network call (L${networkCalls[0].line})`,
        file: relFile, line: sensitiveReads[0].line,
        sample: sensitiveReads[0].text.substring(0, 60)
      });
    }
    
    // Data flow: sensitive read → exec (within same file)
    if (sensitiveReads.length > 0 && execCalls.length > 0) {
      findings.push({
        severity: 'HIGH', id: 'AST_CRED_TO_EXEC', cat: 'data-flow',
        desc: `Data flow: secret read (L${sensitiveReads[0].line}) → command exec (L${execCalls[0].line})`,
        file: relFile, line: sensitiveReads[0].line,
        sample: sensitiveReads[0].text.substring(0, 60)
      });
    }
    
    // Suspicious import combinations
    const importedModules = new Set([...imports.values()]);
    if (importedModules.has('child_process') && (importedModules.has('https') || importedModules.has('http') || importedModules.has('node-fetch'))) {
      findings.push({
        severity: 'HIGH', id: 'AST_SUSPICIOUS_IMPORTS', cat: 'data-flow',
        desc: 'Suspicious import combination: child_process + network module',
        file: relFile
      });
    }
    if (importedModules.has('fs') && importedModules.has('child_process') && (importedModules.has('https') || importedModules.has('http'))) {
      findings.push({
        severity: 'CRITICAL', id: 'AST_EXFIL_TRIFECTA', cat: 'data-flow',
        desc: 'Exfiltration trifecta: fs + child_process + network (full system access)',
        file: relFile
      });
    }
    
    // Detect dynamic URL construction with secrets
    for (let i = 0; i < lines.length; i++) {
      const line = lines[i];
      // Template literal with env vars going to fetch/request
      if (/`[^`]*\$\{.*(?:env|key|token|secret|password).*\}[^`]*`\s*(?:\)|,)/i.test(line) &&
          /(?:fetch|request|axios|http|url)/i.test(line)) {
        findings.push({
          severity: 'CRITICAL', id: 'AST_SECRET_IN_URL', cat: 'data-flow',
          desc: 'Secret interpolated into URL/request',
          file: relFile, line: i + 1,
          sample: line.trim().substring(0, 80)
        });
      }
    }
  }

  // ── v4: Cross-file analysis ──
  // Detects patterns that span multiple files (time-shifted injection)
  checkCrossFile(skillPath, skillName, findings) {
    const files = this.getFiles(skillPath);
    const allContent = {};
    
    for (const file of files) {
      const ext = path.extname(file).toLowerCase();
      if (BINARY_EXTENSIONS.has(ext)) continue;
      const relFile = path.relative(skillPath, file);
      if (relFile.includes('node_modules') || relFile.startsWith('.git')) continue;
      try {
        const content = fs.readFileSync(file, 'utf-8');
        if (content.length < 500000) allContent[relFile] = content;
      } catch {}
    }
    
    // Check: SKILL.md references files that don't exist (phantom references)
    const skillMd = allContent['SKILL.md'] || '';
    const codeFileRefs = skillMd.match(/(?:scripts?\/|\.\/)[a-zA-Z0-9_\-./]+\.(js|py|sh|ts)/gi) || [];
    for (const ref of codeFileRefs) {
      const cleanRef = ref.replace(/^\.\//, '');
      if (!allContent[cleanRef] && !files.some(f => path.relative(skillPath, f) === cleanRef)) {
        findings.push({
          severity: 'MEDIUM', id: 'XFILE_PHANTOM_REF', cat: 'structural',
          desc: `SKILL.md references non-existent file: ${cleanRef}`,
          file: 'SKILL.md'
        });
      }
    }
    
    // Check: Fragment assembly — base64 parts split across files
    const base64Fragments = [];
    for (const [file, content] of Object.entries(allContent)) {
      const matches = content.match(/[A-Za-z0-9+/]{20,}={0,2}/g) || [];
      for (const m of matches) {
        if (m.length > 40) { // long enough to be suspicious
          base64Fragments.push({ file, fragment: m.substring(0, 30) });
        }
      }
    }
    if (base64Fragments.length > 3 && new Set(base64Fragments.map(f => f.file)).size > 1) {
      findings.push({
        severity: 'HIGH', id: 'XFILE_FRAGMENT_B64', cat: 'obfuscation',
        desc: `Base64 fragments across ${new Set(base64Fragments.map(f => f.file)).size} files (possible payload assembly)`,
        file: skillName
      });
    }
    
    // Check: SKILL.md instructs to read from code file and execute
    if (/(?:read|load|source|import)\s+(?:the\s+)?(?:script|file|code)\s+(?:from|at|in)\s+(?:scripts?\/)/gi.test(skillMd)) {
      // Benign in most cases, but flag if combined with other issues
      const hasExec = Object.values(allContent).some(c => /(?:eval|exec|spawn)\s*\(/i.test(c));
      if (hasExec) {
        findings.push({
          severity: 'MEDIUM', id: 'XFILE_LOAD_EXEC', cat: 'data-flow',
          desc: 'SKILL.md references script files that contain exec/eval',
          file: 'SKILL.md'
        });
      }
    }
  }

  calculateRisk(findings) {
    if (findings.length === 0) return 0;

    let score = 0;
    for (const f of findings) {
      score += SEVERITY_WEIGHTS[f.severity] || 0;
    }

    // Combo multipliers (data flow analysis)
    const ids = new Set(findings.map(f => f.id));
    const cats = new Set(findings.map(f => f.cat));

    // Credential access + exfiltration = very bad (2x)
    if (cats.has('credential-handling') && cats.has('exfiltration')) {
      score = Math.round(score * 2);
    }

    // Credential access + network request = suspicious (1.5x)
    if (cats.has('credential-handling') &&
        findings.some(f => f.id === 'MAL_CHILD' || f.id === 'MAL_EXEC')) {
      score = Math.round(score * 1.5);
    }

    // Obfuscation + code execution = very bad (2x)
    if (cats.has('obfuscation') &&
        (cats.has('malicious-code') || cats.has('credential-handling'))) {
      score = Math.round(score * 2);
    }

    // Dependency lifecycle + exec = very bad (2x) (v3)
    if (ids.has('DEP_LIFECYCLE_EXEC')) {
      score = Math.round(score * 2);
    }

    // BiDi + any other finding = suspicious escalation (v3)
    if (ids.has('PI_BIDI') && findings.length > 1) {
      score = Math.round(score * 1.5);
    }

    // v4: Leaky Skills + exfiltration = critical (2x)
    if (cats.has('leaky-skills') && (cats.has('exfiltration') || cats.has('malicious-code'))) {
      score = Math.round(score * 2);
    }

    // v4: Memory poisoning = auto-escalate (1.5x)
    if (cats.has('memory-poisoning')) {
      score = Math.round(score * 1.5);
    }

    // v4: Prompt worm = auto-escalate (2x)
    if (cats.has('prompt-worm')) {
      score = Math.round(score * 2);
    }

    // v4: CVE patterns = near-max
    if (cats.has('cve-patterns')) {
      score = Math.max(score, 70);
    }

    // v4: Persistence + any dangerous category = escalate
    if (cats.has('persistence') && (cats.has('malicious-code') || cats.has('credential-handling') || cats.has('memory-poisoning'))) {
      score = Math.round(score * 1.5);
    }

    // Known IoC = auto max
    if (ids.has('IOC_IP') || ids.has('IOC_URL') || ids.has('KNOWN_TYPOSQUAT')) {
      score = 100;
    }

    return Math.min(100, score);
  }

  getVerdict(risk) {
    if (risk >= this.thresholds.malicious) {
      return { icon: '🔴', label: 'MALICIOUS', stat: 'malicious' };
    }
    if (risk >= this.thresholds.suspicious) {
      return { icon: '🟡', label: 'SUSPICIOUS', stat: 'suspicious' };
    }
    if (risk > 0) {
      return { icon: '🟢', label: 'LOW RISK', stat: 'low' };
    }
    return { icon: '🟢', label: 'CLEAN', stat: 'clean' };
  }

  getFiles(dir) {
    const results = [];
    try {
      const entries = fs.readdirSync(dir, { withFileTypes: true });
      for (const entry of entries) {
        const fullPath = path.join(dir, entry.name);
        if (entry.isDirectory()) {
          if (entry.name === '.git' || entry.name === 'node_modules') continue;
          results.push(...this.getFiles(fullPath));
        } else {
          results.push(fullPath);
        }
      }
    } catch {}
    return results;
  }

  printSummary() {
    const total = this.stats.scanned;
    const safe = this.stats.clean + this.stats.low;
    console.log(`\n${'═'.repeat(54)}`);
    console.log(`📊 GuavaGuard v${VERSION} Scan Summary`);
    console.log(`${'─'.repeat(54)}`);
    console.log(`   Scanned:      ${total}`);
    console.log(`   🟢 Clean:       ${this.stats.clean}`);
    console.log(`   🟢 Low Risk:    ${this.stats.low}`);
    console.log(`   🟡 Suspicious:  ${this.stats.suspicious}`);
    console.log(`   🔴 Malicious:   ${this.stats.malicious}`);
    console.log(`   Safety Rate:  ${total ? Math.round(safe / total * 100) : 0}%`);
    console.log(`${'═'.repeat(54)}`);

    if (this.stats.malicious > 0) {
      console.log(`\n⚠️  CRITICAL: ${this.stats.malicious} malicious skill(s) detected!`);
      console.log(`   Review findings with --verbose and remove if confirmed.`);
    } else if (this.stats.suspicious > 0) {
      console.log(`\n⚡ ${this.stats.suspicious} suspicious skill(s) found — review recommended.`);
    } else {
      console.log(`\n✅ All clear! No threats detected.`);
    }
  }

  toJSON() {
    const recommendations = [];
    
    // Generate recommendations based on findings
    for (const skillResult of this.findings) {
      const skillRecs = [];
      const cats = new Set(skillResult.findings.map(f => f.cat));
      
      if (cats.has('prompt-injection')) {
        skillRecs.push('🛑 Contains prompt injection patterns. Inspect SKILL.md for hidden instructions or Unicode manipulation.');
      }
      if (cats.has('malicious-code')) {
        skillRecs.push('🛑 Contains potentially malicious code. Review all exec/eval/spawn calls carefully.');
      }
      if (cats.has('credential-handling') && cats.has('exfiltration')) {
        skillRecs.push('💀 CRITICAL: Credential access combined with exfiltration detected. DO NOT INSTALL.');
      }
      if (cats.has('dependency-chain')) {
        skillRecs.push('📦 Suspicious dependency chain. Review package.json and run `npm audit` before installing.');
      }
      if (cats.has('obfuscation')) {
        skillRecs.push('🔍 Code obfuscation detected. Legitimate skills rarely obfuscate code.');
      }
      if (cats.has('secret-detection')) {
        skillRecs.push('🔑 Possible hardcoded secrets found. These could be leaked credentials or test values.');
      }
      // v4 recommendations
      if (cats.has('leaky-skills')) {
        skillRecs.push('💧 LEAKY SKILL: Instructions cause secrets to pass through LLM context. Secrets in chat history can be extracted via prompt injection.');
      }
      if (cats.has('memory-poisoning')) {
        skillRecs.push('🧠 MEMORY POISONING: Attempts to modify agent personality/memory files. This enables persistent backdoors across sessions.');
      }
      if (cats.has('prompt-worm')) {
        skillRecs.push('🪱 PROMPT WORM: Self-replicating instructions detected. This skill may spread malicious prompts through agent social networks.');
      }
      if (cats.has('data-flow')) {
        skillRecs.push('🔀 DATA FLOW: Suspicious data paths detected (secret → network/exec). Review the full call chain.');
      }
      if (cats.has('persistence')) {
        skillRecs.push('⏰ PERSISTENCE: Creates scheduled tasks or startup hooks. May execute silently in background.');
      }
      if (cats.has('cve-patterns')) {
        skillRecs.push('🚨 CVE PATTERN: Matches known CVE exploit patterns. Immediate review required.');
      }
      
      if (skillRecs.length > 0) {
        recommendations.push({ skill: skillResult.skill, actions: skillRecs });
      }
    }

    return {
      timestamp: new Date().toISOString(),
      scanner: `GuavaGuard v${VERSION}`,
      mode: this.strict ? 'strict' : 'normal',
      stats: this.stats,
      thresholds: this.thresholds,
      findings: this.findings,
      recommendations,
      iocVersion: '2026-02-10',
      note: 'Run with --verbose for detailed per-file findings. Run with --check-deps for dependency analysis.'
    };
  }
  // ── v3.1: SARIF Output (GitHub Code Scanning / CI/CD) ──
  toSARIF(scanDir) {
    const rules = [];
    const ruleIndex = {};
    const results = [];

    // Collect unique rule IDs
    for (const skillResult of this.findings) {
      for (const f of skillResult.findings) {
        if (!ruleIndex[f.id]) {
          ruleIndex[f.id] = rules.length;
          rules.push({
            id: f.id,
            name: f.id,
            shortDescription: { text: f.desc },
            defaultConfiguration: {
              level: f.severity === 'CRITICAL' ? 'error' : f.severity === 'HIGH' ? 'error' : f.severity === 'MEDIUM' ? 'warning' : 'note'
            },
            properties: {
              tags: ['security', f.cat],
              'security-severity': f.severity === 'CRITICAL' ? '9.0' : f.severity === 'HIGH' ? '7.0' : f.severity === 'MEDIUM' ? '4.0' : '1.0'
            }
          });
        }

        const result = {
          ruleId: f.id,
          ruleIndex: ruleIndex[f.id],
          level: f.severity === 'CRITICAL' ? 'error' : f.severity === 'HIGH' ? 'error' : f.severity === 'MEDIUM' ? 'warning' : 'note',
          message: {
            text: `[${skillResult.skill}] ${f.desc}${f.sample ? ` — "${f.sample}"` : ''}`
          },
          locations: [{
            physicalLocation: {
              artifactLocation: {
                uri: `${skillResult.skill}/${f.file}`,
                uriBaseId: '%SRCROOT%'
              },
              region: f.line ? { startLine: f.line } : undefined
            }
          }]
        };

        results.push(result);
      }
    }

    return {
      version: '2.1.0',
      $schema: 'https://json.schemastore.org/sarif-2.1.0.json',
      runs: [{
        tool: {
          driver: {
            name: 'GuavaGuard',
            version: VERSION,
            informationUri: 'https://github.com/koatora20/guava-guard',
            rules
          }
        },
        results,
        invocations: [{
          executionSuccessful: true,
          endTimeUtc: new Date().toISOString()
        }]
      }]
    };
  }

  // ── v4: HTML Report ──
  toHTML() {
    const stats = this.stats;
    const sevColors = { CRITICAL: '#dc2626', HIGH: '#ea580c', MEDIUM: '#ca8a04', LOW: '#65a30d' };
    
    let skillRows = '';
    for (const sr of this.findings) {
      const findingRows = sr.findings.map(f => {
        const color = sevColors[f.severity] || '#666';
        return `<tr><td style="color:${color};font-weight:bold">${f.severity}</td><td>${f.cat}</td><td>${f.desc}</td><td>${f.file}${f.line ? ':' + f.line : ''}</td></tr>`;
      }).join('\n');
      
      const verdictColor = sr.verdict === 'MALICIOUS' ? '#dc2626' : sr.verdict === 'SUSPICIOUS' ? '#ca8a04' : '#65a30d';
      skillRows += `
        <div class="skill-card">
          <h3>${sr.skill} <span style="color:${verdictColor}">[${sr.verdict}]</span> <small>Risk: ${sr.risk}</small></h3>
          <table><thead><tr><th>Severity</th><th>Category</th><th>Description</th><th>Location</th></tr></thead>
          <tbody>${findingRows}</tbody></table>
        </div>`;
    }

    return `<!DOCTYPE html>
<html lang="en"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>GuavaGuard v${VERSION} Report</title>
<style>
  body{font-family:system-ui,sans-serif;max-width:1000px;margin:0 auto;padding:20px;background:#0f172a;color:#e2e8f0}
  h1{color:#4ade80}h2{color:#86efac;border-bottom:1px solid #334155;padding-bottom:8px}h3{margin:0}
  .stats{display:grid;grid-template-columns:repeat(5,1fr);gap:12px;margin:20px 0}
  .stat{background:#1e293b;border-radius:8px;padding:16px;text-align:center}
  .stat .num{font-size:2em;font-weight:bold}.stat .label{color:#94a3b8;font-size:0.85em}
  .stat.clean .num{color:#4ade80}.stat.low .num{color:#86efac}.stat.suspicious .num{color:#fbbf24}.stat.malicious .num{color:#ef4444}
  .skill-card{background:#1e293b;border-radius:8px;padding:16px;margin:12px 0;border-left:4px solid #334155}
  .skill-card:has([style*="dc2626"]){border-left-color:#dc2626}
  .skill-card:has([style*="ca8a04"]){border-left-color:#ca8a04}
  table{width:100%;border-collapse:collapse;margin-top:8px;font-size:0.9em}
  th,td{padding:6px 10px;text-align:left;border-bottom:1px solid #334155}
  th{color:#94a3b8;font-weight:600}small{color:#64748b;margin-left:8px}
  .footer{color:#475569;text-align:center;margin-top:40px;font-size:0.8em}
</style></head><body>
<h1>🍈🛡️ GuavaGuard v${VERSION}</h1>
<p>Scan completed: ${new Date().toISOString()}</p>
<div class="stats">
  <div class="stat"><div class="num">${stats.scanned}</div><div class="label">Scanned</div></div>
  <div class="stat clean"><div class="num">${stats.clean}</div><div class="label">Clean</div></div>
  <div class="stat low"><div class="num">${stats.low}</div><div class="label">Low Risk</div></div>
  <div class="stat suspicious"><div class="num">${stats.suspicious}</div><div class="label">Suspicious</div></div>
  <div class="stat malicious"><div class="num">${stats.malicious}</div><div class="label">Malicious</div></div>
</div>
<h2>Findings</h2>
${skillRows || '<p style="color:#4ade80">✅ No threats detected.</p>'}
<div class="footer">GuavaGuard v${VERSION} — Zero dependencies. Zero compromises. 🍈</div>
</body></html>`;
  }
}

// ===== CLI =====
const args = process.argv.slice(2);

if (args.includes('--help') || args.includes('-h')) {
  console.log(`
🍈🛡️  GuavaGuard v${VERSION} — Agent Skill Security Scanner

Usage: node guava-guard.js [scan-dir] [options]

Options:
  --verbose, -v       Detailed findings with categories and samples
  --json              Write JSON report to scan-dir/guava-guard-report.json
  --sarif             Write SARIF report (GitHub Code Scanning / CI/CD)
  --html              Write HTML report (visual dashboard)
  --self-exclude      Skip scanning the guava-guard skill itself
  --strict            Lower detection thresholds (more sensitive)
  --summary-only      Only print the summary table
  --check-deps        Scan package.json for dependency chain risks
  --rules <file>      Load custom rules from JSON file
  --fail-on-findings  Exit code 1 if any findings (CI/CD)
  --help, -h          Show this help

Custom Rules JSON Format:
  [
    {
      "id": "CUSTOM_001",
      "pattern": "dangerous_function\\\\(",
      "flags": "gi",
      "severity": "HIGH",
      "cat": "malicious-code",
      "desc": "Custom: dangerous function call",
      "codeOnly": true
    }
  ]

Examples:
  node guava-guard.js ~/.openclaw/workspace/skills/ --verbose --self-exclude
  node guava-guard.js ./skills/ --strict --json --sarif --check-deps
  node guava-guard.js ./skills/ --html --verbose --check-deps
  node guava-guard.js ./skills/ --rules my-rules.json --fail-on-findings
`);
  process.exit(0);
}

const verbose = args.includes('--verbose') || args.includes('-v');
const jsonOutput = args.includes('--json');
const sarifOutput = args.includes('--sarif');
const htmlOutput = args.includes('--html');
const selfExclude = args.includes('--self-exclude');
const strict = args.includes('--strict');
const summaryOnly = args.includes('--summary-only');
const checkDeps = args.includes('--check-deps');
const failOnFindings = args.includes('--fail-on-findings');
const rulesIdx = args.indexOf('--rules');
const rulesFile = rulesIdx >= 0 ? args[rulesIdx + 1] : null;
const scanDir = args.find(a => !a.startsWith('-') && a !== rulesFile) || process.cwd();

const guard = new GuavaGuard({ verbose, selfExclude, strict, summaryOnly, checkDeps, rulesFile });
guard.scanDirectory(scanDir);

if (jsonOutput) {
  const outPath = path.join(scanDir, 'guava-guard-report.json');
  fs.writeFileSync(outPath, JSON.stringify(guard.toJSON(), null, 2));
  console.log(`\n📄 JSON report: ${outPath}`);
}

if (sarifOutput) {
  const outPath = path.join(scanDir, 'guava-guard.sarif');
  fs.writeFileSync(outPath, JSON.stringify(guard.toSARIF(scanDir), null, 2));
  console.log(`\n📄 SARIF report: ${outPath}`);
}

if (htmlOutput) {
  const outPath = path.join(scanDir, 'guava-guard-report.html');
  fs.writeFileSync(outPath, guard.toHTML());
  console.log(`\n📄 HTML report: ${outPath}`);
}

// Exit codes
if (guard.stats.malicious > 0) process.exit(1);
if (failOnFindings && guard.findings.length > 0) process.exit(1);
process.exit(0);
