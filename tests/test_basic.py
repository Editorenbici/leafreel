"""Offline tests (no GPU, no network): style packs, workflow wiring, motion HTML, script validation with a stubbed LLM."""
import json
from pathlib import Path
import pytest
from pagereel import styles, comfy, motion, assemble, script, llm

def test_styles_are_complete():
    s = styles.load_all(); assert {"watercolor", "papercut", "pixel", "clay", "cinematic", "flat", "chalkboard", "kinetic"} <= set(s)
    for st in s.values():
        assert st["engine"] in ("image", "cinematic", "motion") and st["voice"] and st["music"]["tags"]
        if st["engine"] != "motion": assert st["image_style"]
        else: assert st["theme"] in motion.THEMES

def test_workflow_parameters_point_to_real_nodes():
    for name, spec in comfy.SPEC.items():
        wf = json.loads((comfy.WF_DIR / spec["file"]).read_text()); assert spec["out"] in wf, name
        for key, targets in spec["params"].items():
            for node, inp in targets: assert node in wf and inp in wf[node]["inputs"], (name, key, node, inp)

def _spec():
    sc = [{"id": f"{i+1:02d}", "n": f"Line number {i+1} of the test script.", "layout": ["title", "cards", "steps", "compare", "stat", "quote", "cycle", "list", "cards", "quote"][i],
           "d": {"title": "T", "subtitle": "S", "heading": "H", "emoji": "🌋", "items": [{"emoji": "🔥", "title": "A", "text": "b"}, {"emoji": "💧", "title": "B", "text": "c"}, {"emoji": "🌱", "title": "C"}],
                 "left": {"emoji": "🅰", "title": "L", "text": "x"}, "right": {"emoji": "🅱", "title": "R", "text": "y"}, "big": "700", "text": "t"}, "key": ["Line"], "emoji": "🌋"} for i in range(10)]
    sc[7]["d"]["items"] = ["one", "two", "three"]
    return {"scenes": sc, "language": "English"}

@pytest.mark.parametrize("theme", ["flat", "chalkboard", "kinetic"])
def test_motion_html_builds(theme):
    timings = [[i * 4.0, i * 4.0 + 3.5, f"Line {i}"] for i in range(10)]
    page, total = motion.build(_spec(), timings, theme)
    assert "gsap" in page and total > 40 and "window.seek" in page

def test_srt(tmp_path):
    p = assemble.write_srt(tmp_path, [[0, 2.5, "Hello world"], [3, 5, "Second line"]]); t = p.read_text()
    assert "00:00:00,500 --> 00:00:03,200" in t and "Second line" in t

def test_script_generation_and_fact_check(monkeypatch):
    scenes = [{"n": f"Narration line {i}.", "layout": "quote", "d": {"text": "?"}, "key": [], "emoji": "❓"} for i in range(10)]
    calls = []
    def fake(system, user, check=lambda j: True, **kw):
        calls.append(system[:30])
        j = {"title": "T", "summary": "s", "key_ideas": ["a", "b", "c"], "scenes": scenes} if "scriptwriter" in system else {"problems": [{"line": 2, "reason": "unsupported", "fix": "Corrected line."}]}
        assert check(j); return j
    monkeypatch.setattr(llm, "json_call", fake)
    spec = script.generate("doc " * 100, styles.get("flat"))
    assert len(spec["scenes"]) == 10 and spec["scenes"][1]["n"] == "Corrected line." and spec["fact_check"][0]["line"] == 2 and spec["scenes"][0]["id"] == "01"

def test_chromium_scratch_dir_is_short(monkeypatch, tmp_path):
    long_tmp = tmp_path / ("deep_" * 30); long_tmp.mkdir(); monkeypatch.setenv("TMPDIR", str(long_tmp))
    d = motion.short_tmp(); assert len(str(d)) < 40 and d.exists(); d.rmdir()
