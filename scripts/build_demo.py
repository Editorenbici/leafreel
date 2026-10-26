#!/usr/bin/env python3
"""Assemble the ≤2-minute demo: real UI recording (timelapsed), cards, a grid of example reels, designed-voice narration and ACE-Step music.
Every segment lasts exactly as long as the narration lines it illustrates, so picture and voice stay in sync.
Usage: build_demo.py REC_DIR NARRATION_DIR MUSIC.mp3 OUT.mp4   (REC_DIR has the .webm + marks.json; NARRATION_DIR has narration.wav + narration_timings.json)"""
import json, os, subprocess, sys, glob
from pathlib import Path
rec, nar, music, out = Path(sys.argv[1]).resolve(), Path(sys.argv[2]).resolve(), str(Path(sys.argv[3]).resolve()), Path(sys.argv[4]).resolve()
root = Path(__file__).resolve().parent.parent; tmp = out.parent / "demo_tmp"; tmp.mkdir(exist_ok=True)
webm = (glob.glob(str(rec / "rec.mp4")) or glob.glob(str(rec / "*.webm")))[0]; M = json.loads((rec / "marks.json").read_text()); T = json.loads((nar / "narration_timings.json").read_text())
FPS, PAD = 25, 0.55
# The browser's screencast clock and the script's Date.now() do not advance at the same rate (and not uniformly), so marks are re-anchored on what the
# recording itself shows: the moment the black <video> player of the finished reel first appears (after the card-preview hovers at the start).
import numpy as np
rec_len = float(subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", webm], text=True))
raw = subprocess.run(["ffmpeg", "-loglevel", "error", "-i", webm, "-vf", "fps=1,scale=128:72", "-f", "rawvideo", "-pix_fmt", "gray", "-"], capture_output=True).stdout
g = np.frombuffer(raw, dtype=np.uint8).reshape(-1, 72, 128); dark = (g < 25).mean(axis=(1, 2))
t_done = next(i for i in range(int(M["running"] * 1.1) + 30, len(dark)) if dark[i] > 0.008)
k1 = t_done / M["done"]; k2 = (rec_len - t_done) / (M["remade"] + 2.8 - M["done"])
M = {k: (v * k1 if v <= M["done"] else t_done + (v - M["done"]) * k2) for k, v in M.items()}; print(f"anchors: done at {t_done}s (x{k1:.3f} before, x{k2:.3f} after)")
def sh(*a): subprocess.run(a, check=True)
def span(i, j): return T[i][0], T[j][1] + PAD                       # narration lines i..j (0-based) -> [start, end]
ES = Path(os.environ.get("DEMO_ES", ""))   # Spanish example reel (full frame)
EXTRA = {"diagram": Path(os.environ.get("DEMO_DIAGRAM", root / "../runs/diagram.mp4")), "terminal": Path(os.environ.get("DEMO_TERMINAL", root / "../runs/terminal.mp4"))}
LAYOUT = [  # (kind, first narration line, last line, source, badge shown top-left)
    ("card", 0, 1, root / "demo/card_title.png", ""),
    ("rec", 2, 2, (M["start"], M["press"] + 1.5), "The web app"),
    ("video", 3, 3, EXTRA["diagram"], ""),
    ("rec", 4, 4, (M["running"], M["done"]), "Real run on the RTX 3090 · timelapse"),
    ("rec", 5, 5, (M.get("qa", M["played"]) - 0.5, M["facts"] + 2.0), "Vision QA and fact-check, shown"),
    ("grid", 6, 6, None, "Same document · six styles"),
    ("video", 7, 7, ES, "Spanish narration · same pipeline"),
    ("video", 8, 8, EXTRA["terminal"], "Hermes Agent + local Qwen · recorded session"),
    ("rec", 9, 9, (M["facts"], M["remade"]), "Edit and remake · cached frames reused"),
    ("card", 10, 10, root / "demo/card_end.png", ""),
]
vids, auds = [], []
starts = []; clock = 0.0
for n, (kind, i, j, src, badge) in enumerate(LAYOUT):
    a, b = span(i, j); D = b - a + (2.5 if kind == "grid" else 0.0); v = tmp / f"v{n}.mp4"; w = tmp / f"a{n}.wav"
    sh("ffmpeg", "-y", "-loglevel", "error", "-ss", f"{a:.3f}", "-i", str(nar / "narration.wav"), "-af", f"atrim=0:{b - a:.3f},apad=whole_dur={D:.3f}", "-ar", "48000", "-ac", "1", str(w))
    if kind == "card":
        sh("ffmpeg", "-y", "-loglevel", "error", "-loop", "1", "-i", str(src), "-vf", f"scale=1280:720,fps={FPS},format=yuv420p,fade=t=in:d=0.4", "-t", f"{D:.3f}", "-c:v", "libx264", "-crf", "18", str(v))
    elif kind == "rec":
        s0, s1 = src; f = D / max(s1 - s0, 0.1)                          # f < 1 -> speed up; f > 1 -> slow down / hold last frame
        sh("ffmpeg", "-y", "-loglevel", "error", "-ss", f"{s0:.3f}", "-t", f"{s1 - s0:.3f}", "-i", webm, "-vf", f"setpts={f:.5f}*PTS,fps={FPS},tpad=stop_mode=clone:stop_duration=2,scale=1280:720,format=yuv420p", "-t", f"{D:.3f}", "-an", "-c:v", "libx264", "-crf", "18", str(v))
    elif kind == "video":  # a finished clip, stretched/held to the narration length (full frame, silent)
        cd = float(subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(src)], text=True)); f = D / cd
        sh("ffmpeg", "-y", "-loglevel", "error", "-i", str(src), "-vf", f"scale=1280:720,setpts={f:.5f}*PTS,fps={FPS},tpad=stop_mode=clone:stop_duration=3,format=yuv420p", "-t", f"{D:.3f}", "-an", "-c:v", "libx264", "-crf", "18", str(v))
    else:  # grid of example reels
        names = ["watercolor", "papercut", "pixel", "clay", "chalkboard", "cinematic"]; ex = [root / f"leafreel/examples/outputs/volcanoes_{n}.mp4" for n in names]
        inputs = []; fc = []
        for k, p in enumerate(ex):
            inputs += ["-stream_loop", "-1", "-ss", f"{8 + 3 * k}", "-i", str(p)]
            fc.append(f"[{k}:v]scale=420:236,setsar=1,drawtext=text='{names[k]}':x=10:y=h-30:fontsize=22:fontcolor=white:box=1:boxcolor=black@0.55:boxborderw=6:font=DejaVu Sans[t{k}]")
        lay = "0_0|420_0|840_0|0_236|420_236|840_236"
        fc.append("".join(f"[t{k}]" for k in range(6)) + f"xstack=inputs=6:layout={lay}[g]")
        fc.append(f"color=c=0x0d1020:s=1280x720:d={D:.3f}[bg];[bg][g]overlay=10:124,fps={FPS},format=yuv420p[o]")
        sh("ffmpeg", "-y", "-loglevel", "error", *inputs, "-filter_complex", ";".join(fc), "-map", "[o]", "-t", f"{D:.3f}", "-an", "-c:v", "libx264", "-crf", "18", str(v))
    if badge:
        b = tmp / f"vb{n}.mp4"; txt = badge.replace("'", "").replace(":", " -").replace("·", "-")   # drawtext mismeasures multi-byte glyphs
        sh("ffmpeg", "-y", "-loglevel", "error", "-i", str(v), "-vf", f"drawtext=text='{txt}':x=28:y=26:fontsize=26:fontcolor=white:box=1:boxcolor=0x0d1020@0.80:boxborderw=14:font=DejaVu Sans", "-an", "-c:v", "libx264", "-crf", "18", str(b)); v = b
    starts.append((clock, i, j)); clock += D
    vids.append(v); auds.append(w)
for name, files in (("video", vids), ("audio", auds)):
    (tmp / f"{name}.txt").write_text("".join(f"file '{f}'\n" for f in files))
sh("ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", str(tmp / "video.txt"), "-c", "copy", str(tmp / "video.mp4"))
sh("ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", str(tmp / "audio.txt"), "-c", "copy", str(tmp / "voice.wav"))
d = float(subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(tmp / "voice.wav")], text=True))
def ts(x): return f"{int(x//3600):02d}:{int(x%3600//60):02d}:{x%60:06.3f}".replace(".", ",")
import textwrap
with open(tmp / "demo.srt", "w") as f:
    c = 0
    for seg_start, i, j in starts:
        for k in range(i, j + 1):
            a0 = seg_start + (T[k][0] - T[i][0]); b0 = seg_start + (T[k][1] - T[i][0]) + 0.15; c += 1
            f.write(f"{c}\n{ts(a0)} --> {ts(b0)}\n" + "\n".join(textwrap.wrap(T[k][2], 54)) + "\n\n")
STYLE = "FontName=DejaVu Sans,FontSize=9,Bold=1,PrimaryColour=&H00FFFFFF,OutlineColour=&H00000000,BackColour=&HAA000000,BorderStyle=3,Outline=5,Shadow=0,MarginV=14"
fa = f"[1:a]aloop=loop=-1:size=2e9,atrim=0:{d:.2f},volume=0.16,afade=t=in:d=1,afade=t=out:st={d-3:.2f}:d=3[m];[0:a][m]amix=inputs=2:duration=first:normalize=0,loudnorm=I=-16:TP=-2:LRA=11,aresample=48000[a]"
sh("ffmpeg", "-y", "-loglevel", "error", "-i", str(tmp / "voice.wav"), "-i", music, "-i", str(tmp / "video.mp4"), "-filter_complex", fa, "-map", "2:v", "-map", "[a]", "-vf", f"subtitles={tmp}/demo.srt:force_style='{STYLE}'", "-c:v", "libx264", "-crf", "20", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "160k", "-shortest", "-movflags", "+faststart", str(out))
print(f"demo: {d:.1f} s -> {out} ({out.stat().st_size/1e6:.1f} MB)")
