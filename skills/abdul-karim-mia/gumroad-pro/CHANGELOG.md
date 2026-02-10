# Changelog

All notable changes to this project will be documented in this file.

## [1.2.1] - 2026-02-09

### Security
- Replaced `child_process.execSync` with `child_process.spawnSync` in `handler.js` to mitigate shell injection vulnerabilities identified by ClawHub security scan.
- Refactored all internal CLI calls to use argument arrays instead of concatenated strings.

## [1.2.0] - 2026-02-09

### Added
- Critical Protocol: Mandated use of interactive buttons on Telegram/Discord.
- Fallback Authentication: `gumroad-pro.js` now accepts `API_KEY` (mapped from `apiKey` config) as a valid token source, in addition to `GUMROAD_ACCESS_TOKEN`.

### Changed
- Updated `SKILL.md` with streamlined Setup instructions for API Key configuration.

## [1.1.0] - 2026-02-09

### Added
- Comprehensive CLI Technical Reference to `SKILL.md` (all commands and flags documented).
- LLM Operational Protocols for state management and UI orchestration.
- Command aliases: `/gumroad-pro` and `/gumroad_pro`.
- Standardized metadata (`_meta.json`).

### Changed
- Refined adaptive UI logic for improved channel compatibility.
- Synchronized `SKILL.md` with full internal script capabilities.

### Fixed
- Removed redundant and failing "Shown on Profile" field from Product Details view.

### Security
- Sanitized deployment protocols for public GitHub publication.
