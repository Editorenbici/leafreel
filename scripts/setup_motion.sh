#!/usr/bin/env bash
# Dependencies for the code-rendered styles (flat, chalkboard, kinetic): GSAP + playwright-core + a Chromium binary.
set -euo pipefail
cd "$(dirname "$0")/.."
npm install --no-audit --no-fund gsap playwright-core
echo "Set CHROMIUM_PATH to a Chromium/Chrome binary (or run: npx playwright-core install chromium)."
