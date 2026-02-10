# Security Notes for Listing Swarm

## What This Skill Accesses

### External Services (User Provides Credentials)

| Service | Why | User Action Required |
|---------|-----|---------------------|
| 2captcha.com | Solve captchas on directory forms | User creates account, provides their own API key |
| IMAP (Gmail, etc.) | Read verification emails | User provides their own email credentials |

**⚠️ NO CREDENTIALS ARE STORED IN THIS SKILL**

The skill does NOT include any API keys or passwords. Users must:
1. Get their own 2captcha API key from https://2captcha.com
2. Set up their own email with IMAP access (optional)

### Files Accessed

| File | Access | Purpose |
|------|--------|---------|
| directories.json | Read | List of 70+ AI directories |
| submissions.json | Read/Write | Track submission status |
| User's product config | Read | Fill directory forms |

### Network Requests

| Destination | Purpose |
|-------------|---------|
| 2captcha.com/in.php | Submit captcha for solving (user's key) |
| 2captcha.com/res.php | Get captcha solution (user's key) |
| User's IMAP server | Check for verification emails (user's credentials) |
| AI directory websites | Submit product listings |

## What This Skill Does NOT Do

- ❌ Store any credentials
- ❌ Access user's personal files
- ❌ Make payments
- ❌ Create accounts without user knowledge
- ❌ Send data to LinkSwarm or third parties (except captcha service user configured)

## Why External API Calls?

1. **Captcha solving**: Directories have captchas. User's 2captcha account solves them.
2. **Email verification**: Directories send verification emails. User's IMAP access lets agent auto-verify.

Both are optional and require the USER to provide their own credentials.

## Source Code

All code is readable in this skill folder:
- `captcha.js` - 2captcha integration
- `email.js` - IMAP verification
- `directories.json` - Static list of directories

No obfuscation. No hidden functionality.
