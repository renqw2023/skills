---
name: mlx-stt
description: Speech-To-Text with MLX (Apple Silicon) and GLM-ASR.
metadata: {"openclaw":{"always":true,"emoji":"🦞","homepage":"https://github.com/guoqiao/skills/blob/main/mlx-stt/mlx-stt/SKILL.md","os":["darwin"],"requires":{"bins":["brew"],"anyBins":[],"env":[],"config":[]},"install":[]}}
---

# MLX Speech to Text

Transcribe audio to text with MLX (Apple Silicon) and GLM-ASR. Free and Accurate.

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
