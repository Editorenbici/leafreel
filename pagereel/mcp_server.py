"""MCP server (stdio): lets any MCP-capable agent (Hermes, OpenClaw, pi, Claude Code, Cursor…) make reels with PageReel.

Reels take minutes, so the tools are asynchronous: `start_reel` returns a job id, `reel_status` reports the stage, `reel_result` returns the video.
Run:  pagereel-mcp      (or: python -m pagereel.mcp_server)
"""
import json, logging, os, threading, time, traceback, uuid
from pathlib import Path
try:                                   # mcp >= 2
    from mcp.server.mcpserver import MCPServer as FastMCP
except ImportError:                    # mcp 1.x
    from mcp.server.fastmcp import FastMCP
from . import config, styles

mcp = FastMCP("pagereel", instructions="Make narrated explainer videos from a document. Call start_reel, then reel_status(job_id, wait_seconds=90) until done, then reel_result. "
              "Reels take 2-6 minutes (the 'cinematic' style ~35). Only one reel runs at a time.")
JOBS: dict[str, dict] = {}
log = logging.getLogger("pagereel.mcp")
LOCK = threading.Lock()   # one GPU job at a time

def _setup_log():
    """Tool calls and job errors go to <data dir>/mcp.log (stdout is the MCP protocol channel; never print there)."""
    config.DATA_DIR.mkdir(parents=True, exist_ok=True)
    h = logging.FileHandler(config.DATA_DIR / "mcp.log"); h.setFormatter(logging.Formatter("%(asctime)s [pid %(process)d] %(message)s"))
    log.addHandler(h); log.setLevel(logging.INFO); log.propagate = False

def _doc(document: str) -> str:
    p = Path(document).expanduser() if len(document) < 400 and "\n" not in document else None
    if p and p.exists():
        from .cli import read_doc
        return read_doc(p)
    return document

def _run(jid, doc, style, language, audience, camera, spec=None):
    from . import pipeline
    job = JOBS[jid]
    def progress(stage, pct, msg): job.update(stage=stage, pct=pct, msg=msg)
    with LOCK:
        job["status"] = "running"; t0 = time.time()
        try:
            r = pipeline.make(doc, style, config.DATA_DIR / "runs" / jid, language, audience, progress, spec=spec, camera=camera)
            job.update(status="done", result=r, seconds=round(time.time() - t0))
        except Exception as e:
            log.error("job %s failed:\n%s", jid, traceback.format_exc()); job.update(status="error", error=repr(e)[:300])

def _start(doc, style, language, audience, camera, spec=None, parent=None):
    styles.get(style); jid = uuid.uuid4().hex[:10]
    JOBS[jid] = dict(id=jid, status="queued", stage="queued", pct=0, msg="", style=style, language=language, audience=audience, camera=camera, parent=parent)
    threading.Thread(target=_run, args=(jid, doc, style, language, audience, camera, spec), daemon=True).start(); return jid

@mcp.tool()
def list_styles() -> list[dict]:
    """List the available visual styles (id, name, engine, one-line description)."""
    return [{"id": s["id"], "name": s["name"], "engine": s["engine"], "about": s.get("blurb", "")} for s in styles.load_all().values()]

@mcp.tool()
def start_reel(document: str, style: str = "watercolor", language: str = "English", audience: str = "curious learners aged 8-12", camera: str = "auto") -> dict:
    """Start making a narrated explainer video from a document.

    document: the text itself, or a path to a .pdf/.md/.txt file on this machine.
    style: one of list_styles() ids. language: narration language (English, Spanish, Portuguese, French, German, Italian, Japanese, Chinese, Korean, Russian).
    camera (cinematic style only): auto, push-in, pull-back, pan, orbit, crane-up, handheld, static.
    Returns {"job_id": ...}; poll reel_status."""
    log.info("start_reel style=%s language=%s document=%.80r", style, language, document)
    doc = _doc(document)
    if len(doc.strip()) < 200: return {"error": "document too short (need at least ~200 characters)"}
    return {"job_id": _start(doc, style, language, audience, camera)}

@mcp.tool()
def reel_status(job_id: str, wait_seconds: int = 0) -> dict:
    """Progress of a reel: status (queued/running/done/error), stage, percent and a message.

    wait_seconds (0-120): block up to this long and return early as soon as the job finishes. Use 60-90 to avoid polling in a tight loop."""
    log.info("reel_status %s wait=%s", job_id, wait_seconds)
    j = JOBS.get(job_id)
    if not j: return {"error": "unknown job_id"}
    end = time.time() + max(0, min(int(wait_seconds), 120))
    while j["status"] in ("queued", "running") and time.time() < end: time.sleep(1)
    return {k: j.get(k) for k in ("status", "stage", "pct", "msg", "error", "seconds")}

@mcp.tool()
def reel_result(job_id: str) -> dict:
    """Result of a finished reel: video path, title, narration lines, what the fact-checker changed, timings and the verification report."""
    j = JOBS.get(job_id)
    if not j: return {"error": "unknown job_id"}
    if j["status"] != "done": return {"status": j["status"], "hint": "not finished yet; poll reel_status"}
    r = j["result"]; spec = r["spec"]
    return {"video": r["video"], "title": spec["title"], "narration": [s["n"] for s in spec["scenes"]], "fact_check_changes": spec.get("fact_check", []),
            "seconds": r["total_s"], "timings": r["timings"], "verification": r["verification"]}

@mcp.tool()
def remake_reel(job_id: str, edits: list[dict]) -> dict:
    """Rebuild a finished reel with edits. edits: [{"id": "03", "n": "new narration line", "p": "new visual prompt (image styles)"}]. Unchanged frames/clips are reused from cache."""
    j = JOBS.get(job_id)
    if not j or j["status"] != "done": return {"error": "job not finished"}
    spec = json.loads(json.dumps(j["result"]["spec"])); by = {e["id"]: e for e in edits}
    for sc in spec["scenes"]:
        e = by.get(sc["id"], {})
        for k in ("n", "p", "v"):
            if e.get(k) and k in sc: sc[k] = e[k].strip()
        if e.get("p"): sc.pop("p_simple", None)
        if e.get("v"): sc.pop("v_simple", None)
    import shutil
    new = uuid.uuid4().hex[:10]; a, b = config.DATA_DIR / "runs" / job_id, config.DATA_DIR / "runs" / new
    shutil.copytree(a, b, ignore=shutil.ignore_patterns("video.mp4", "result.json", "verification.json", "qa_frames", "frames"))
    JOBS[new] = dict(id=new, status="queued", stage="queued", pct=0, msg="", style=j["style"], language=j["language"], audience=j["audience"], camera=j["camera"], parent=job_id)
    threading.Thread(target=_run, args=(new, "", j["style"], j["language"], j["audience"], j["camera"], spec), daemon=True).start()
    return {"job_id": new}

def main():
    _setup_log(); log.info("pagereel-mcp started (pid %s)", os.getpid()); mcp.run()

if __name__ == "__main__": main()
