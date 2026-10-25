"""MCP tool functions with a stubbed pipeline (no GPU): start -> status -> result -> remake."""
import time
import pytest
pytest.importorskip("mcp")
from pagereel import mcp_server as m, pipeline

def _fn(x): return getattr(x, "fn", x)

def test_reel_lifecycle(monkeypatch, tmp_path):
    seen = {}
    def fake_make(doc, style, work, language, audience, progress=None, spec=None, camera="auto"):
        seen.update(doc=doc, style=style, spec=spec); progress("script", 5, "writing"); progress("done", 100, "ok")
        sp = spec or {"title": "T", "scenes": [{"id": "01", "n": "Line one.", "p": "x"}], "fact_check": []}
        return {"video": str(tmp_path / "v.mp4"), "spec": sp, "timings": {"script": 1.0}, "total_s": 2.0, "verification": {"ok": True}}
    monkeypatch.setattr(pipeline, "make", fake_make); monkeypatch.setattr(m.config, "DATA_DIR", tmp_path)
    assert {s["id"] for s in _fn(m.list_styles)()} >= {"pixel", "kinetic"}
    assert "error" in _fn(m.start_reel)("too short")
    jid = _fn(m.start_reel)("word " * 100, style="pixel")["job_id"]
    for _ in range(50):
        if _fn(m.reel_status)(jid)["status"] == "done": break
        time.sleep(0.1)
    assert _fn(m.reel_status)(jid)["status"] == "done" and seen["style"] == "pixel"
    res = _fn(m.reel_result)(jid); assert res["title"] == "T" and res["narration"] == ["Line one."]
    (tmp_path / "runs" / jid).mkdir(parents=True, exist_ok=True)
    new = _fn(m.remake_reel)(jid, [{"id": "01", "n": "Edited line."}])["job_id"]
    for _ in range(50):
        if _fn(m.reel_status)(new)["status"] == "done": break
        time.sleep(0.1)
    assert _fn(m.reel_result)(new)["narration"] == ["Edited line."]
