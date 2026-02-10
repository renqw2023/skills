# Changelog

## 1.0.1

### Added
- **Configuration system** — `~/.briefing-room/config.json` with all settings
  - Configurable location (city, lat/lon, timezone) for weather
  - Configurable language (en, sk, de, or any macOS-supported)
  - Per-language voice settings (engine, voice, speed, blend)
  - Configurable sections list
  - Configurable output folder
- **Multi-language TTS** — per-language engine selection
  - English: MLX-Audio Kokoro (fast, local)
  - Slovak: Apple Laura (Enhanced)
  - German: Apple Petra (Premium)
  - Any language: add a `voices` entry + pick from `say -v '?'`
- **Auto-detect TTS engines** — finds mlx-audio and kokoro automatically
- **Config CLI** — `scripts/config.py` with status, get, set, init, reset
- **Voice blend support** — resolves pre-blended .safetensors from HF cache
- **Helper script uses config** — weather/crypto commands read location from config

### Changed
- Removed all hardcoded paths and coordinates
- Weather API uses configured location instead of hardcoded Bratislava
- Local news section uses configured city name
- SKILL.md uses `SKILL_DIR` placeholder for portable paths
- Broke long curl/command lines to prevent horizontal overflow
- Updated README with multi-language examples and config docs

### Fixed
- Long code lines causing horizontal scroll on ClawHub
- Silent config corruption now warns on stderr
- `init` command uses deep_copy to avoid mutating defaults
- `set` CLI verifies write succeeded (no false "Set" on failure)
- Moved `glob` and `shutil` imports to top-level (consistent, errors surface at import)
- Added `sys` to top-level imports (was inline in error handler)

## 1.0.0

- Initial release
- 9 sections: Weather, Social, Local, World, Politics, Tech, Sports, Markets, Crypto
- MLX-Audio Kokoro TTS (English)
- Apple Laura TTS (Slovak)
- DOCX + MP3 output
- Sub-agent pattern for non-blocking generation
