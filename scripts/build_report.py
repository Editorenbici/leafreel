#!/usr/bin/env python3
"""Measured timings and checks for every example run -> docs/BENCHMARKS.md. Usage: build_report.py RUNS_DIR"""
import json, sys
from pathlib import Path
runs = Path(sys.argv[1]); rows = []
for d in sorted(runs.glob("*/result.json")):
    r = json.loads(d.read_text()); t = r["timings"]; v = r["verification"]; style = d.parent.name.split("_", 1)[1]
    gen = t.get("images", 0) + t.get("video_clips", 0) + t.get("render", 0); qa = t.get("vision_qa", 0) + t.get("regeneration", 0)
    rows.append((style, v["duration_s"], r["total_s"], t.get("script", 0), t.get("narration", 0), gen, qa, t.get("music", 0), t.get("assemble", 0) + t.get("mix", 0), t.get("verification", 0), v["lufs"], "OK" if v["ok"] else "review"))
lines = ["# Measured timings", "", "One 53-second-ish reel per style from `examples/volcanoes.md`. App/LLM box: ARM mini-PC (121 GB unified memory). GPU box: RTX 3090 24 GB",
         "(thermally throttled during these runs, see README). Seconds, wall-clock, single job at a time.", "",
         "| Style | Video | Total | Script+fact-check | Voice | Visuals | Vision QA + redo | Music | Assemble+mix | Verify | LUFS | Check |", "|---|---|---|---|---|---|---|---|---|---|---|---|"]
for r in rows: lines.append(f"| {r[0]} | {r[1]:.0f} s | **{r[2]:.0f} s** | {r[3]:.0f} | {r[4]:.0f} | {r[5]:.0f} | {r[6]:.0f} | {r[7]:.0f} | {r[8]:.0f} | {r[9]:.0f} | {r[10]} | {r[11]} |")
Path("docs/BENCHMARKS.md").write_text("\n".join(lines) + "\n"); print("\n".join(lines))
