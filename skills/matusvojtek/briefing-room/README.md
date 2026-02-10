# Briefing Room 📻

**Your personal daily news briefing — audio + document.**

Ask for a briefing and get a comprehensive, conversational radio-host-style update on everything that matters today. Configurable location, language, and sections.

## Features

- 📻 **Radio-Host Style** — Natural, conversational monologue — not a list of headlines
- 🔊 **Audio Briefing** — ~10 minute MP3, perfect for your commute
- 📄 **Formatted Document** — DOCX with sections, key facts, and source links
- 🌍 **9 Sections** — Weather → Social Pulse → Local → World → Politics → Tech → Sports → Markets → Crypto
- 🌐 **Multi-Language** — English (MLX-Audio Kokoro), Slovak, German, or any macOS voice
- ⚙️ **Configurable** — Location, language, voice, sections — all in `~/.briefing-room/config.json`
- 🆓 **100% Free & Local** — Free APIs, local TTS, no subscriptions

## Quick Start

Just ask your agent:

- "Give me a briefing"
- "Morning update"
- "What's happening today?"
- "Ranný brífing" (Slovak mode)
- "Tägliches Briefing" (German mode)

## First Run

The skill auto-creates a config on first use. Customize your location:

```bash
python3 scripts/config.py set location.city "Vienna"
python3 scripts/config.py set location.latitude 48.21
python3 scripts/config.py set location.longitude 16.37
python3 scripts/config.py set location.timezone "Europe/Vienna"
```

Check your setup:
```bash
python3 scripts/config.py status
```

## What You Get

```
~/Documents/Briefing Room/2026-02-10/
├── briefing-2026-02-10-0830.docx    # Formatted document with sections
└── briefing-2026-02-10-0830.mp3     # Audio briefing (~10 min)
```

## Configuration

All settings in `~/.briefing-room/config.json`:

| Setting | Default | Description |
|---------|---------|-------------|
| `location.city` | Bratislava | City for weather + local news |
| `location.latitude` | 48.15 | Weather API latitude |
| `location.longitude` | 17.11 | Weather API longitude |
| `language` | en | Briefing language |
| `output.folder` | ~/Documents/Briefing Room | Where briefings are saved |
| `sections` | all 9 | Which sections to include |

### Voice Per Language

```json
{
  "voices": {
    "en": {"engine": "mlx", "mlx_voice": "af_heart", "speed": 1.05},
    "sk": {"engine": "builtin", "builtin_voice": "Laura (Enhanced)", "builtin_rate": 220},
    "de": {"engine": "builtin", "builtin_voice": "Petra (Premium)", "builtin_rate": 200}
  }
}
```

Add any language — just pick a voice from `say -v '?'` on macOS.

## Sections

| # | Section | Source |
|---|---------|--------|
| 1 | 🌤️ Weather | Open-Meteo API (your location) |
| 2 | 🐦 Social Pulse | Web search (X/Twitter trends) |
| 3 | 🏠 Local | Web search (your city) |
| 4 | 🌍 World | Web search |
| 5 | 🏛️ Politics | Web search |
| 6 | 💻 Tech & AI | Web search |
| 7 | ⚽ Sports | Web search |
| 8 | 📈 Markets | Web search + APIs |
| 9 | ₿ Crypto | Coinbase API + Web search |

## Dependencies

**Required:**
- macOS with `curl` (built-in)
- OpenClaw with `web_search`

**Recommended:**
- [MLX-Audio Kokoro](https://github.com/ml-explore/mlx-audio) — fast English TTS on Apple Silicon
- `pandoc` — DOCX generation (`brew install pandoc`)
- `ffmpeg` — MP3 conversion (`brew install ffmpeg`)

**Always available:**
- Apple `say` — multilingual TTS fallback (built into macOS)

## Install

```bash
clawhub install briefing-room
```
