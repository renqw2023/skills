#!/bin/bash

text=${1:-"Hello, Human!"}
model=mlx-community/Qwen3-TTS-12Hz-1.7B-VoiceDesign-bf16
outdir="$(mktemp -d)"
mlx_audio.tts.generate --play \
  --instruct="Be nice" \
  --output_path="${outdir}" \
  --model=${model} \
  --text="${text}"
