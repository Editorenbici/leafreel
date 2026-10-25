"""End-to-end pipeline: document -> script -> narration -> visuals (ComfyUI via Comfy SDK, with a vision QA loop) -> music -> mix -> verification.
Every stage reports progress and timing so the UI (and the metrics) can show where the time goes."""
import json, os, time, shutil
from pathlib import Path
from PIL import Image
from . import config, styles, script, qa, tts, assemble, verify
from .comfy import Comfy_

MAX_QA_ROUNDS = 3

def _cached(dest, key):
    """Sidecar <file>.json remembers which prompt produced a file, so edits only redo what changed."""
    side = Path(str(dest) + ".json")
    return Path(dest).exists() and side.exists() and json.loads(side.read_text()).get("key") == key

def _remember(dest, key, **extra): Path(str(dest) + ".json").write_text(json.dumps({"key": key, **extra}))

def pixelate(path, width=320, colors=40):
    im = Image.open(path).convert("RGB"); w, h = im.size
    small = im.resize((width, h * width // w), Image.BILINEAR).quantize(colors, dither=Image.Dither.NONE).convert("RGB")
    small.resize((w, h), Image.NEAREST).save(path)

class Job:
    def __init__(self, work, progress=None):
        self.work = Path(work); self.work.mkdir(parents=True, exist_ok=True); self.t0 = time.time(); self.timings = {}; self.cb = progress or (lambda *a: None)
    def stage(self, name, pct, msg=""):
        self.cb(name, pct, msg); print(f"[{time.time()-self.t0:6.0f}s] {name}: {msg}", flush=True)
    def timed(self, name):
        job = self
        class T:
            def __enter__(s): s.t = time.time()
            def __exit__(s, *a): job.timings[name] = round(job.timings.get(name, 0) + time.time() - s.t, 1)
        return T()

def _images(job, comfy, spec, style):
    esc = spec["scenes"]; w = job.work / "assets"; w.mkdir(exist_ok=True); char = spec.get("character", ""); cine = style["engine"] == "cinematic"
    prompt = lambda e: f"{style['image_style']}, " + (e.get("p_simple") or e["p"]).replace("{character}", char)
    anchor = None if cine or not style.get("character") else next((i for i, e in enumerate(esc) if "{character}" in e["p"]), None)
    ref = None; seeds = {}
    def make(i, e, force=False):
        dest = w / f"{e['id']}.png"; seed = 1000 + i + 7919 * seeds.get(e["id"], 0); key = prompt(e) + f"|{char}"
        if not force and _cached(dest, key): return
        comfy.image(prompt(e), dest, seed=seed, reference=ref if ref and "{character}" in e["p"] else None)
        if style.get("pixelate"): pixelate(dest)
        _remember(dest, key)
    with job.timed("images"):
        if anchor is not None: make(anchor, esc[anchor]); ref = w / f"{esc[anchor]['id']}.png"
        for i, e in enumerate(esc):
            job.stage("visuals", 25 + 30 * i / len(esc), f"image {i+1}/{len(esc)}")
            if i != anchor: make(i, e)
    report = {}
    for rnd in range(MAX_QA_ROUNDS):
        job.stage("qa", 55, f"vision QA round {rnd+1}")
        with job.timed("vision_qa"): res = qa.inspect_all([w / f"{e['id']}.png" for e in esc], style["name"], no_people=cine)
        bad = [e for e, (b, r) in zip(esc, res) if b]; report = {e["id"]: r for e, (b, r) in zip(esc, res)}
        if not bad or rnd == MAX_QA_ROUNDS - 1: break
        with job.timed("regeneration"):
            for e in bad:
                seeds[e["id"]] = seeds.get(e["id"], 0) + 1
                if "p_simple" not in e or seeds[e["id"]] > 1: e["p_simple"] = qa.simplify(e["p"].replace("{character}", char), level=seeds[e["id"]])
                job.stage("qa", 55, f"regenerating scene {e['id']} (simpler prompt)"); make(int(e["id"]) - 1, e, force=True)
    (job.work / "qa_images.json").write_text(json.dumps({"remaining": [e["id"] for e, (b, _) in zip(esc, res) if b], "report": report}, indent=1, ensure_ascii=False))
    return [w / f"{e['id']}.png" for e in esc]

def _clips(job, comfy, spec, style):
    c = job.work / "clips"; c.mkdir(exist_ok=True); out = []
    for i, e in enumerate(spec["scenes"]):
        job.stage("visuals", 55 + 25 * i / len(spec["scenes"]), f"video clip {i+1}/{len(spec['scenes'])} (LTX-2.5)")
        dest = c / f"{e['id']}.mp4"; src = job.work / "assets" / f"{e['id']}.png"; key = (e.get("v_simple") or e["v"]) + "|" + (json.loads(Path(str(src) + ".json").read_text())["key"] if Path(str(src) + ".json").exists() else "")
        if not _cached(dest, key):
            with job.timed("video_clips"): comfy.video(job.work / "assets" / f"{e['id']}.png", (e.get("v_simple") or e["v"]) + ", realistic documentary style, natural light, no people", dest, seed=3000 + i)
            _remember(dest, key)
        out.append(dest)
        cool = float(os.environ.get("GPU_COOLDOWN", "0"))  # optional pause between clips to let the GPU cool (long LTX runs)
        if cool and i < len(spec["scenes"]) - 1: job.stage("visuals", 55 + 25 * (i + 1) / len(spec["scenes"]), f"cooling down {cool:.0f}s"); time.sleep(cool)
    return out

def make(doc_text, style_id, work, language="English", audience="curious learners aged 8-12", progress=None, spec=None):
    """Run the whole pipeline. Returns a dict with paths, spec, timings and the verification report."""
    style = styles.get(style_id); job = Job(work, progress); comfy = Comfy_()
    if spec is None:
        job.stage("script", 5, "writing the script and fact-checking it against the document")
        with job.timed("script"): spec = script.generate(doc_text, style, language, audience)
    (job.work / "spec.json").write_text(json.dumps(spec, indent=1, ensure_ascii=False))
    lines = [s["n"] for s in spec["scenes"]]
    job.stage("voice", 15, "designing the voice and narrating")
    with job.timed("narration"): timings = tts.narrate(lines, style["voice"], language, job.work)
    ambient, music_tag = [], style["music"]
    if style["engine"] == "motion":
        from . import motion
        job.stage("visuals", 40, "rendering code-driven scenes")
        with job.timed("render"): silent = motion.render(job.work, spec, timings, style["theme"], log=lambda m: job.stage("visuals", 60, m))
        subs = False
    else:
        images = _images(job, comfy, spec, style)
        if style["engine"] == "cinematic": sources = _clips(job, comfy, spec, style)
        else: sources = images
        job.stage("assemble", 82, "cutting scenes together")
        with job.timed("assemble"): silent, ambient = assemble.scenes_to_video(job.work, sources, timings, style["transition"], style.get("camera", "drift"), ambient=style["engine"] == "cinematic")
        assemble.write_srt(job.work, timings); subs = True
    job.stage("music", 88, "composing the soundtrack (ACE-Step)")
    music = job.work / "music.mp3"
    with job.timed("music"): comfy.music(music_tag["tags"], music, seconds=int(assemble.duration(silent)) + 3, bpm=music_tag.get("bpm", 100), seed=11)
    job.stage("mix", 93, "mixing and normalizing to -16 LUFS")
    final = job.work / "video.mp4"
    with job.timed("mix"): assemble.mix(job.work, silent, music, style["id"], subs, ambient, final)
    job.stage("verify", 96, "verifying the result (audio levels + vision on real frames)")
    with job.timed("verification"): report = verify.verify(final, job.work, timings)
    total = round(time.time() - job.t0, 1); result = dict(video=str(final), spec=spec, timings=job.timings, total_s=total, verification={k: v for k, v in report.items() if k != "frames"})
    (job.work / "result.json").write_text(json.dumps(result, indent=1, ensure_ascii=False))
    job.stage("done", 100, f"done in {total:.0f}s; verification {'OK' if report['ok'] else 'needs review'}"); return result
