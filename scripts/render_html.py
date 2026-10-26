#!/usr/bin/env python3
"""Render any HTML page that exposes window.DUR (seconds) and window.seek(t) (e.g. a paused GSAP timeline) to a silent mp4.
Usage: render_html.py page.html out.mp4 [fps]"""
import os, shutil, subprocess, sys, tempfile, time
from pathlib import Path
from leafreel import motion, config

def render_html(page, out, fps=25, workers=8):
    page = Path(page).resolve(); tmp = motion.short_tmp(); fr = tmp / "f"; fr.mkdir(); w = tmp / "w.mjs"; w.write_text(motion.RENDER)
    env = {**os.environ, "LEAFREEL_ROOT": str(motion.ROOT), "CHROMIUM_PATH": config.CHROMIUM, "TMPDIR": str(tmp), "HOME": str(tmp)}
    ps = [subprocess.Popen([motion.NODE, str(w), str(page), str(fr), str(fps), "1280", str(k), str(workers)], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, env=env) for k in range(workers)]
    for p in ps:
        _, err = p.communicate()
        if p.returncode: raise RuntimeError(err[-400:])
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-framerate", str(fps), "-i", str(fr / "f%05d.jpg"), "-c:v", "libx264", "-crf", "17", "-pix_fmt", "yuv420p", str(out)], check=True)
    n = len(list(fr.glob("*.jpg"))); shutil.rmtree(tmp, ignore_errors=True); return n

if __name__ == "__main__":
    t = time.time(); n = render_html(sys.argv[1], sys.argv[2], int(sys.argv[3]) if len(sys.argv) > 3 else 25); print(f"{n} frames in {time.time()-t:.0f}s -> {sys.argv[2]}")
