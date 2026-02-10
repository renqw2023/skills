# 🚀 Getting Started with Security Skill Scanner

## Quick Start Guide

### Step 1: Download the Scanner

```bash
git clone https://github.com/anikrahman0/security-skill-scanner.git
cd security-skill-scanner
```

### Step 2: Run Your First Scan

```bash
# Scan the example malicious skill
node scanner.js examples/malicious-skill/SKILL.md

# Scan the example clean skill  
node scanner.js examples/clean-skill/SKILL.md
```

## Common Use Cases

### Before Installing a New Skill

```bash
# Download the skill you want to check
mkdir ~/Downloads/new-skill
cd ~/Downloads/new-skill
# ... download SKILL.md ...

# Scan it
node /path/to/security-skill-scanner/scanner.js ~/Downloads/new-skill/SKILL.md
```

### Audit All Your Installed Skills

```bash
# Scan your entire OpenClaw skills directory
node scanner.js ~/.openclaw/skills/

# This will check every installed skill
```

### Check Skills from ClawHub Before Installing

```bash
# Download from ClawHub first
clawhub download suspicious-skill --no-install

# Scan it
node scanner.js ~/.openclaw/downloads/suspicious-skill/

# Only install if it passes
clawhub install suspicious-skill
```

## Understanding the Output

### Risk Levels Explained

- **🔴 CRITICAL** - DO NOT INSTALL - Immediate threat to your system
  - External binary downloads
  - Credential harvesting
  - Known malware domains
  - Arbitrary code execution
  
- **🟠 HIGH** - NOT RECOMMENDED - Serious security concerns  
  - Suspicious API endpoints
  - Access to sensitive files
  - Obfuscated code (base64)
  - Unencrypted data transmission

- **🟡 MEDIUM** - CAUTION - Review carefully
  - Broad file access
  - HTTP instead of HTTPS
  - Dynamic code loading
  - Many dependencies

- **🟢 LOW** - LIKELY SAFE - Minor issues
  - Code quality problems
  - Missing error handling
  - Documentation gaps

- **ℹ️ INFO** - SAFE - No issues detected
  - Clean, well-written skill
  - Safe to install

### Reading the Report

```
═══════════════════════════════════════════════════
           SECURITY SCAN REPORT
═══════════════════════════════════════════════════

Skill: my-skill/SKILL.md
Scanned: 2024-02-09T14:30:22.000Z
Overall Risk: 🔴 CRITICAL        ← Overall assessment
Risk Score: 100/100               ← 0=safe, 100=critical

─────────────── FINDINGS ───────────────

1. [🔴 CRITICAL] External binary download detected
   Pattern: EXTERNAL_DOWNLOAD     ← What was detected
   Line(s): 45                     ← Where in the file
   Example: curl https://...       ← Actual code found
   ⚠️  DO NOT INSTALL - ...       ← What to do

─────────────── SUMMARY ─────────────────

Total Issues: 3
  🔴 Critical: 1                  ← Count by severity
  🟠 High: 1
  🟡 Medium: 1
  🟢 Low: 0

─────────────── RECOMMENDATION ──────────────

❌ DO NOT INSTALL - This skill has critical security issues
```

## Decision Making Guide

### When to Install

✅ **SAFE TO INSTALL** when:
- Risk level is INFO or LOW
- Author is known and trusted
- Code is open source and reviewable
- Skill is from official sources
- Many positive reviews/downloads

### When to Avoid

❌ **DO NOT INSTALL** when:
- Risk level is CRITICAL
- External downloads required
- Requests sensitive file access
- Connects to unknown domains
- Too good to be true

### When to Investigate

⚠️ **NEEDS REVIEW** when:
- Risk level is MEDIUM or HIGH
- Author is unknown
- Limited documentation
- Few reviews/downloads
- Unusual permissions requested

### Example Decision Tree

```
1. Scan the skill
   ↓
2. Check risk level
   ↓
   Is it CRITICAL? → DO NOT INSTALL
   ↓
   Is it HIGH? → Review findings carefully
   ↓            → Contact author for clarification
   ↓            → Only install if you trust them
   ↓
   Is it MEDIUM? → Check what files it accesses
   ↓             → Verify API endpoints are legitimate
   ↓             → Install with caution
   ↓
   Is it LOW/INFO? → Generally safe to install
                     → Still review from trusted sources only
```

## False Positives

Sometimes safe code gets flagged. Here's how to identify false positives:

### Example 1: Package Managers

```javascript
// This might get flagged as shell execution
exec('npm install package-name')
```

**Is it safe?** Generally YES if:
- Installing from npm/pip/yarn
- Package name is well-known
- Part of setup instructions
- No external downloads

### Example 2: GitHub URLs

```javascript
fetch('https://raw.githubusercontent.com/user/repo/main/config.json')
```

**Is it safe?** Generally YES if:
- Using HTTPS
- From known repository
- For configuration/data only
- No code execution

### Example 3: Config Files

```javascript
fs.writeFileSync('~/.myskill/config.json', data)
```

**Is it safe?** Generally YES if:
- Writing to its own directory
- Not accessing system files
- No sensitive data
- Clear documentation

## Advanced Tips

### Creating a Whitelist

If you frequently use skills from trusted sources:

```json
{
  "whitelistedDomains": [
    "api.yourcompany.com",
    "github.com/yourorg",
    "cdn.jsdelivr.net"
  ],
  "whitelistedCommands": [
    "npm install",
    "your-safe-command"
  ]
}
```

### Batch Scanning (Linux/Mac)

```bash
# Scan all .md files in a directory
find ~/.openclaw/skills -name "*.md" -exec node scanner.js {} \;

# Scan and save reports
for dir in ~/.openclaw/skills/*/; do
  node scanner.js "$dir" > "$dir/security-report.txt"
done
```

### Batch Scanning (Windows PowerShell)

```powershell
# Scan all .md files in a directory
Get-ChildItem -Path "$env:USERPROFILE\.openclaw\skills" -Filter "*.md" -Recurse | ForEach-Object { node scanner.js $_.FullName }
```

### Integration with Shell (Linux/Mac)

Add to your `.bashrc` or `.zshrc`:

```bash
alias skill-scan='node /path/to/security-skill-scanner/scanner.js'

# Usage: skill-scan ./SKILL.md
```

### Integration with PowerShell (Windows)

Add to your PowerShell profile:

```powershell
function skill-scan { node "E:\Personal Projects\agent skills-openclaw\security-skill-scanner\scanner.js" $args }

# Usage: skill-scan .\SKILL.md
```

### Pre-commit Hook

If you're developing skills:

```bash
#!/bin/sh
# .git/hooks/pre-commit

node /path/to/scanner.js ./SKILL.md

if [ $? -ne 0 ]; then
  echo "Security scan failed! Fix issues before committing."
  exit 1
fi
```

## Troubleshooting

### "Cannot find module"

```bash
# Make sure you're in the scanner directory
cd /path/to/security-skill-scanner

# Or use full path
node /full/path/to/scanner.js ./file.md
```

### "No such file or directory"

```bash
# Use full paths
node scanner.js ~/full/path/to/SKILL.md

# On Windows
node scanner.js C:\Users\YourName\Downloads\skill\SKILL.md
```

### Scanner reports too many false positives

1. Check if code is in documentation (markdown code blocks)
2. Add legitimate domains to whitelist
3. Use strict mode: `false` in config
4. Review each finding individually

## Best Practices

1. **Always scan before installing** - Make it a habit
2. **Update the scanner regularly** - New patterns added frequently
3. **Report suspicious skills** - Help the community
4. **Trust but verify** - Even trusted authors can make mistakes
5. **Keep logs** - Save scan reports for reference
6. **Share findings** - Warn others about malicious skills

## Getting Help

- **GitHub Issues**: https://github.com/anikrahman0/security-skill-scanner/issues
- **Discussions**: https://github.com/anikrahman0/security-skill-scanner/discussions
- **Security Concerns**: Report via GitHub Security tab

## Next Steps

1. ✅ Scan your currently installed skills
2. ✅ Add scanner to your workflow
3. ✅ Configure whitelist for your trusted sources
4. ✅ Report any malicious skills you find
5. ✅ Help improve the scanner by contributing patterns

---

**Remember: This tool is your first line of defense. Always use good judgment!** 🛡️
