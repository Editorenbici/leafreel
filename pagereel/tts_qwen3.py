#!/usr/bin/env python3
"""Qwen3-TTS VoiceDesign helper (needs `pip install qwen-tts soundfile` and a GPU). One narration line per input line.
Usage: tts_qwen3.py [--seed N] [--language L] [--voice DESCRIPTION] lines.txt out.wav  ->  out.wav + out_timings.json"""
import argparse, json, numpy as np, soundfile as sf, torch
from qwen_tts import Qwen3TTSModel
ap = argparse.ArgumentParser(); ap.add_argument("--seed", type=int, default=7); ap.add_argument("--language", default="English")
ap.add_argument("--voice", default="warm clear narrator"); ap.add_argument("src"); ap.add_argument("dest"); a = ap.parse_args()
m = Qwen3TTSModel.from_pretrained("Qwen/Qwen3-TTS-12Hz-1.7B-VoiceDesign", device_map="cuda:0", dtype=torch.bfloat16)
lines = [l.strip() for l in open(a.src, encoding="utf-8") if l.strip()]
audio, timings, t, sr = [], [], 0.0, 24000
for line in lines:
    torch.manual_seed(a.seed)  # same seed per line keeps the timbre constant across the video
    w, sr = m.generate_voice_design(text=line, language=a.language, instruct=a.voice)
    seg = np.asarray(w[0], dtype=np.float32); pause = np.zeros(int(sr * 0.45), dtype=np.float32)
    timings.append([round(t, 2), round(t + len(seg) / sr, 2), line]); audio += [seg, pause]; t += (len(seg) + len(pause)) / sr
sf.write(a.dest, np.concatenate(audio), sr)
json.dump(timings, open(a.dest.rsplit(".", 1)[0] + "_timings.json", "w"), ensure_ascii=False)
print(f"{len(lines)} lines, {t:.1f}s -> {a.dest}")
