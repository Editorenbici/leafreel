#!/usr/bin/env bash
# Poster frame + 4 s loop for each style card in the UI, and a compact copy of every example in examples/outputs/.
# Usage: scripts/make_previews.sh RUNS_DIR   (expects RUNS_DIR/<doc>_<style>/video.mp4)
set -euo pipefail
cd "$(dirname "$0")/.."
RUNS=${1:?runs dir}; PV=leafreel/examples/previews; OUT=leafreel/examples/outputs; mkdir -p "$PV" "$OUT"
for v in "$RUNS"/volcanoes_*/video.mp4; do
  style=$(basename "$(dirname "$v")"); style=${style#volcanoes_}; d=$(ffprobe -v error -show_entries format=duration -of csv=p=0 "$v")
  ffmpeg -y -loglevel error -ss "$(python3 -c "print($d*0.42)")" -i "$v" -frames:v 1 -vf scale=640:-1 -q:v 4 "$PV/$style.jpg"
  ffmpeg -y -loglevel error -ss "$(python3 -c "print($d*0.30)")" -t 4 -i "$v" -an -vf scale=480:-2,fps=20 -c:v libx264 -crf 30 -preset slow -pix_fmt yuv420p -movflags +faststart "$PV/$style.mp4"
  ffmpeg -y -loglevel error -i "$v" -vf scale=1280:-2 -c:v libx264 -crf 27 -preset slow -pix_fmt yuv420p -c:a aac -b:a 96k -movflags +faststart "$OUT/volcanoes_$style.mp4"
  echo "ok $style"
done
