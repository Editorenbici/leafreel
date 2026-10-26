#!/usr/bin/env bash
# Assemble the static site (landing page + example reels + demo) into _site/ for GitHub Pages.
set -euo pipefail
cd "$(dirname "$0")/.."
rm -rf _site && mkdir -p _site/media
cp site/index.html _site/
cp leafreel/examples/outputs/volcanoes_*.mp4 _site/media/
[ -f demo/leafreel_demo.mp4 ] && cp demo/leafreel_demo.mp4 _site/media/
cp docs/img/social-preview.png _site/media/ 2>/dev/null || true
for f in _site/media/volcanoes_*.mp4; do n=$(basename "$f" .mp4); n=${n#volcanoes_}; [ -f "leafreel/examples/previews/$n.jpg" ] && cp "leafreel/examples/previews/$n.jpg" "_site/media/$n.jpg"; done
for f in _site/media/volcanoes_*.mp4; do n=$(basename "$f" .mp4); n=${n#volcanoes_}; [ -f "_site/media/$n.jpg" ] || ! command -v ffmpeg >/dev/null || ffmpeg -y -loglevel error -ss 20 -i "$f" -frames:v 1 -vf scale=640:-2 -q:v 4 "_site/media/$n.jpg"; done
[ -f docs/img/demo-poster.jpg ] && cp docs/img/demo-poster.jpg _site/media/
echo "site ready: $(du -sh _site | cut -f1)"
