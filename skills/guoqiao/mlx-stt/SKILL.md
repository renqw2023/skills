---
name: mlx-stt
description: Speech-To-Text/ASR/Transcibe with MLX (Apple Silicon) and glm-asr-nano-2512 locally. Free and Accurate. No api key required, no server required.
metadata: {"openclaw":{"always":true,"emoji":"🦞","homepage":"https://github.com/guoqiao/skills/blob/main/mlx-stt/mlx-stt/SKILL.md","os":["darwin"],"tags":["latest","asr","stt","speech-to-text","audio","glm","glm-asr","glm-asr-nano-2512","glm-asr-nano-2512-8bit","macOS","MacBook","Mac mini","Apple Silicon","mlx","mlx-audio"],"requires":{"bins":["brew"]}}}
---

# MLX STT

Speech-To-Text/ASR/Transcibe with MLX (Apple Silicon) and glm-asr-nano-2512 locally. Free and Accurate. No api key required, no server required.

## Requirements

- `mlx`: macOS with Apple Silicon
- `brew`: used to install deps if not available

## Installation

```bash
bash ${baseDir}/install.sh
```
This script will use `brew` to install these cli tools if not available:
- `ffmpeg`: convert audio format when needed
- `uv`: install python package and run python script
- `mlx_audio`: do the real job

## Usage

To transcribe an audio file, run the `mlx-stt.py` script:

```bash
uv run  ${baseDir}/mlx-stt.py <audio_file_path>
```

The transcript result will be printed to stdout.
