"""Whole pipeline with stubbed LLM / Comfy / TTS: exercises script -> narration -> frames -> vision QA (with a retry) -> assemble -> mix -> verify.
Needs ffmpeg + ffprobe only (no GPU, no network)."""
import json, shutil, subprocess
from pathlib import Path
import numpy as np, pytest
from PIL import Image, ImageDraw
from pagereel import pipeline, tts, llm, comfy, script, qa

pytestmark = pytest.mark.skipif(not shutil.which("ffmpeg"), reason="ffmpeg not installed")

def _png(path, seed, size=(1280, 720)):
    im = Image.new("RGB", size, (40 + seed * 17 % 200, 90, 160)); d = ImageDraw.Draw(im); d.ellipse((400, 200, 880, 520), fill=(250, 200, 60)); im.save(path)

class FakeComfy:
    calls = []
    def image(self, prompt, dest, width=1280, height=720, seed=1, reference=None): FakeComfy.calls.append(("image", prompt, reference is not None)); _png(dest, seed)
    def music(self, tags, dest, seconds=75, bpm=100, seed=1):
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi", "-i", f"sine=frequency=220:duration={seconds}", str(dest)], check=True)
    def video(self, *a, **k): raise AssertionError("not used by image styles")

def fake_narrate(lines, voice, language, dest_dir, seed=7):
    import soundfile as sf
    sr, audio, t, tm = 24000, [], 0.0, []
    for line in lines:
        seg = (0.1 * np.sin(2 * np.pi * 180 * np.arange(int(sr * 2.4)) / sr)).astype("float32"); pause = np.zeros(int(sr * 0.45), dtype="float32")
        tm.append([round(t, 2), round(t + 2.4, 2), line]); audio += [seg, pause]; t += 2.85
    Path(dest_dir).mkdir(parents=True, exist_ok=True); sf.write(str(Path(dest_dir) / "narration.wav"), np.concatenate(audio), sr); return tm

def test_image_style_end_to_end(tmp_path, monkeypatch):
    qa_calls = {"n": 0}
    def fake_vision(path, prompt, max_tokens=700):
        if "children's educational video" in prompt and "style_match" in prompt:
            qa_calls["n"] += 1
            return {"text_visible": Path(path).name == "03.png" and qa_calls["n"] <= 12, "deformed": False, "disturbing": False, "n_people": 1, "style_match": True, "description": "ok"}
        return {"text_cut_or_illegible": False, "gibberish_text": False, "deformed": False, "empty_screen": False, "disturbing": False, "note": ""}
    scenes = [{"n": f"Scene {i+1} narration with enough words to read.", "p": "{character} stands in a place " + str(i)} for i in range(12)]
    def fake_json(system, user, check=lambda j: True, **kw):
        j = {"title": "T", "summary": "s", "key_ideas": ["a", "b", "c"], "character": "Ana, a girl in a red coat", "scenes": scenes} if "scriptwriter" in system else {"problems": []}
        assert check(j); return j
    monkeypatch.setattr(llm, "vision", fake_vision); monkeypatch.setattr(llm, "json_call", fake_json)
    monkeypatch.setattr(llm, "text", lambda *a, **k: "A simpler prompt of a plain landscape")
    monkeypatch.setattr(pipeline, "Comfy_", FakeComfy); monkeypatch.setattr(tts, "narrate", fake_narrate)
    stages = []
    r = pipeline.make("doc " * 100, "watercolor", tmp_path / "run", progress=lambda s, p, m: stages.append(s))
    video = Path(r["video"]); assert video.exists() and video.stat().st_size > 50_000
    assert r["verification"]["technical_ok"], r["verification"]
    assert "regeneration" in r["timings"], "QA should have rejected scene 03 and regenerated it"
    assert any(c[0] == "image" and c[2] for c in FakeComfy.calls), "frames after the first must use the character reference"
    assert {"script", "voice", "visuals", "qa", "assemble", "music", "mix", "verify", "done"} <= set(stages)
    d = float(subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(video)], text=True)); assert 25 < d < 45
    spec = json.loads((tmp_path / "run" / "spec.json").read_text()); assert any("p_simple" in s for s in spec["scenes"])
