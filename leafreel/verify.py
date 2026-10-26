"""Final-video verification: technical (ffprobe, LUFS, black frames, silences) + a vision LLM looking at real frames of the result."""
import json, re, subprocess
from pathlib import Path
from . import llm
from .assemble import duration

FRAME_PROMPT = ('A frame from an educational video with narration and subtitles. Reply ONLY with JSON: {"text_cut_or_illegible": bool (on-screen text cut off, overlapping or illegible), '
                '"gibberish_text": bool, "deformed": bool, "empty_screen": bool, "disturbing": bool, "note": "one sentence if something is off, else empty"}')

def verify(video, work, timings=None):
    work = Path(work); d = duration(video); r = {"duration_s": round(d, 1), "size_mb": round(Path(video).stat().st_size / 1e6, 1)}
    e = subprocess.run(["ffmpeg", "-nostats", "-i", str(video), "-af", "ebur128=peak=true,silencedetect=n=-45dB:d=2.5", "-vf", "blackdetect=d=0.4:pix_th=0.06", "-f", "null", "-"], capture_output=True, text=True).stderr
    li = re.findall(r"I:\s+(-?[\d.]+) LUFS", e); pk = re.findall(r"Peak:\s+(-?[\d.]+) dBFS", e)
    r.update(lufs=float(li[-1]) if li else None, peak_dbfs=float(pk[-1]) if pk else None, black_frames=len(re.findall("black_start", e)), long_silences=len(re.findall("silence_start", e)))
    r["technical_ok"] = r["lufs"] is not None and abs(r["lufs"] + 16) <= 1.0 and r["peak_dbfs"] <= -1.0 and r["black_frames"] == 0 and r["long_silences"] == 0
    qa = work / "qa_frames"; qa.mkdir(exist_ok=True)
    ends = [b + 0.5 for _, b, _ in timings] if timings else [d * (k + 0.5) / 8 for k in range(8)]  # sample when animations have finished
    picks = [ends[round(k * (len(ends) - 1) / 7)] for k in range(8)] if len(ends) >= 8 else ends
    frames = []
    for k, t in enumerate(picks):
        f = qa / f"f{k}.jpg"; subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-ss", f"{min(t, d-0.3):.2f}", "-i", str(video), "-frames:v", "1", "-q:v", "3", str(f)], check=True)
        frames.append(llm.vision(f, FRAME_PROMPT))
    r["frames"] = frames
    r["frame_issues"] = [i for i, v in enumerate(frames) if any(v.get(k) for k in ("text_cut_or_illegible", "gibberish_text", "deformed", "empty_screen", "disturbing"))]
    r["ok"] = r["technical_ok"] and not r["frame_issues"]
    (work / "verification.json").write_text(json.dumps(r, indent=1, ensure_ascii=False)); return r
