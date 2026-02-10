# Project Structure

```
security-skill-scanner/
│
├── SKILL.md                    # Main skill definition for ClawHub (REQUIRED)
├── README.md                   # Full documentation
├── QUICKSTART.md              # Quick reference (start here!)
├── GETTING_STARTED.md         # Detailed usage guide
├── CONTRIBUTING.md            # How to contribute
├── UPLOAD_CHECKLIST.md        # Pre-upload checklist
├── LICENSE                    # MIT License
│
├── scanner.js                 # Core scanner implementation
├── test.js                    # Test suite
├── package.json               # NPM package metadata
├── .gitignore                 # Git ignore rules
│
└── examples/                  # Test examples
    ├── clean-skill/
    │   └── SKILL.md          # Example of safe skill
    └── malicious-skill/
        └── SKILL.md          # Example of malicious skill
```

## File Descriptions

### Essential Files (Required for ClawHub)
- **SKILL.md** - The main file ClawHub needs. Contains skill metadata, documentation, and usage examples.

### Core Implementation
- **scanner.js** - The security scanner engine with 40+ malicious pattern detectors
- **test.js** - Automated tests to verify scanner works correctly
- **package.json** - NPM package configuration

### Documentation
- **README.md** - Comprehensive documentation with all features, examples, and usage
- **QUICKSTART.md** - Get started in 30 seconds (read this first!)
- **GETTING_STARTED.md** - Step-by-step guide for common use cases
- **CONTRIBUTING.md** - Guide for contributors
- **UPLOAD_CHECKLIST.md** - Checklist before uploading to ClawHub

### Examples
- **examples/clean-skill/** - Example of a safe skill that passes security checks
- **examples/malicious-skill/** - Example of a dangerous skill that triggers warnings

## File Sizes

| File | Description | Lines |
|------|-------------|-------|
| SKILL.md | 250+ | Main ClawHub file |
| scanner.js | 550+ | Core scanner |
| README.md | 350+ | Full docs |
| GETTING_STARTED.md | 400+ | Usage guide |
| CONTRIBUTING.md | 350+ | Contribution guide |

## What to Read First

1. **QUICKSTART.md** (5 min) - Get running immediately
2. **README.md** (15 min) - Understand features
3. **GETTING_STARTED.md** (20 min) - Learn all use cases
4. **UPLOAD_CHECKLIST.md** (10 min) - Before uploading

## What to Modify Before Upload

1. **SKILL.md** - Replace "YourGitHubUsername" with your username
2. **package.json** - Add your name and repository URL
3. **LICENSE** - Add your name
4. **README.md** - Update repository URLs

## Total Project Stats

- **~2,000 lines** of documentation
- **~550 lines** of code
- **40+ security patterns** detected
- **4 risk levels** (Critical/High/Medium/Low)
- **100% JavaScript** (no dependencies)
- **Works offline** (no API keys needed)
