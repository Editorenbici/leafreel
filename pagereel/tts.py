"""Narration. Backends: "qwen3tts" (Qwen3-TTS VoiceDesign: the voice is *designed* from a text description, no real person is cloned)
or "http" (any OpenAI-compatible /v1/audio/speech server). Returns narration.wav + per-line timings."""
import json, subprocess, shutil, tempfile, wave, struct
from pathlib import Path
import httpx
from . import config

HELPER = Path(__file__).with_name("tts_qwen3.py")

def narrate(lines, voice_description, language, dest_dir, seed=7):
    dest_dir = Path(dest_dir); dest_dir.mkdir(parents=True, exist_ok=True)
    wav = dest_dir / "narration.wav"; timings = dest_dir / "narration_timings.json"
    if config.TTS_BACKEND == "http": _http(lines, wav, timings)
    else: _qwen3(lines, voice_description, language, wav, timings, seed)
    return json.loads(timings.read_text())

def _qwen3(lines, desc, language, wav, timings, seed):
    txt = wav.with_name("narration.txt"); txt.write_text("\n".join(lines) + "\n")
    if config.TTS_SSH:
        r = f"pagereel_tts/{wav.parent.name}"; h = config.TTS_SSH
        subprocess.run(["ssh", "-o", "BatchMode=yes", h, f"mkdir -p {r}"], check=True)
        subprocess.run(["scp", "-q", str(HELPER), str(txt), f"{h}:{r}/"], check=True)
        subprocess.run(["ssh", "-o", "BatchMode=yes", h, f"cd {r} && {config.TTS_PYTHON} tts_qwen3.py --seed {seed} --language '{language}' --voice '{desc}' narration.txt narration.wav"], check=True)
        subprocess.run(["scp", "-q", f"{h}:{r}/narration.wav", f"{h}:{r}/narration_timings.json", str(wav.parent) + "/"], check=True)
    else:
        subprocess.run([config.TTS_PYTHON, str(HELPER), "--seed", str(seed), "--language", language, "--voice", desc, str(txt), str(wav)], check=True)

def _http(lines, wav, timings):
    """One request per line, concatenated with 0.45 s pauses (works with Kokoro-FastAPI, Orpheus, etc.)."""
    import numpy as np, soundfile as sf
    sr = 24000; audio, t, tm = [], 0.0, []
    for line in lines:
        r = httpx.post(config.TTS_HTTP_URL, timeout=300, json={"model": config.TTS_HTTP_MODEL, "voice": config.TTS_HTTP_VOICE, "input": line, "response_format": "wav"}); r.raise_for_status()
        with tempfile.NamedTemporaryFile(suffix=".wav") as f:
            f.write(r.content); f.flush(); seg, sr = sf.read(f.name, dtype="float32")
        if seg.ndim > 1: seg = seg.mean(axis=1)
        pause = np.zeros(int(sr * 0.45), dtype="float32"); tm.append([round(t, 2), round(t + len(seg) / sr, 2), line]); audio += [seg, pause]; t += (len(seg) + len(pause)) / sr
    sf.write(str(wav), np.concatenate(audio), sr); Path(timings).write_text(json.dumps(tm, ensure_ascii=False))
