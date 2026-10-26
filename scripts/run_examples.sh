#!/usr/bin/env bash
# Build one example per style from examples/volcanoes.md, one after another (never in parallel: keeps the GPU safe).
set -u
cd "$(dirname "$0")/.."
for style in "$@"; do
  out=${RUNS:-$HOME/.leafreel/runs}/volcanoes_$style
  [ -f "$out/video.mp4" ] && { echo "skip $style"; continue; }
  .venv/bin/leafreel make examples/volcanoes.md --style "$style" --out "$out" > "$out.log" 2>&1 || echo "FAILED $style"
done
echo ALL_DONE
