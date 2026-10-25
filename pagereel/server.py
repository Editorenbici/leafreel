"""Web app: upload a document, pick a style, watch the pipeline run, get the video. One job at a time (protects the GPU)."""
import asyncio, io, json, queue, shutil, threading, time, uuid
from pathlib import Path
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from . import config, styles, pipeline

UI = Path(__file__).parent / "ui"
app = FastAPI(title="PageReel")
JOBS: dict[str, dict] = {}
Q: "queue.Queue[str]" = queue.Queue()

def _doc_text(name, data: bytes) -> str:
    if name.lower().endswith(".pdf"):
        from pypdf import PdfReader
        return "\n".join(p.extract_text() or "" for p in PdfReader(io.BytesIO(data)).pages)
    return data.decode("utf-8", errors="replace")

def _worker():
    while True:
        jid = Q.get(); job = JOBS[jid]; job["status"] = "running"; job["started"] = time.time()
        def progress(stage, pct, msg, job=job): job["events"].append(dict(t=round(time.time() - job["started"], 1), stage=stage, pct=pct, msg=msg)); job["stage"], job["pct"], job["msg"] = stage, pct, msg
        try:
            r = pipeline.make(job.get("text", ""), job["style"], config.DATA_DIR / "runs" / jid, job["language"], job["audience"], progress, spec=job.get("spec_in"))
            job.update(status="done", result={k: v for k, v in r.items() if k != "spec"}, spec=r["spec"])
        except Exception as e:
            job.update(status="error", error=repr(e)); progress("error", 100, repr(e))
threading.Thread(target=_worker, daemon=True).start()

@app.get("/api/styles")
def api_styles(): return list(styles.load_all().values())

@app.post("/api/jobs")
async def create_job(style: str = Form(...), language: str = Form("English"), audience: str = Form("curious learners aged 8-12"), text: str = Form(""), file: UploadFile | None = File(None)):
    if file is not None and file.filename: text = _doc_text(file.filename, await file.read())
    if len(text.strip()) < 200: raise HTTPException(400, "Please provide at least a few sentences of text (200+ characters).")
    styles.get(style); jid = uuid.uuid4().hex[:10]
    JOBS[jid] = dict(id=jid, style=style, language=language, audience=audience, text=text, status="queued", events=[], stage="queued", pct=0, msg=f"{Q.qsize()} ahead in the queue", created=time.time())
    Q.put(jid); return {"id": jid}

def _public(j): return {k: v for k, v in j.items() if k not in ("text", "spec_in")}

@app.post("/api/jobs/{jid}/remake")
async def remake(jid: str, edits: dict):
    """Edit narration lines / visual prompts of a finished reel and rebuild it. Unchanged frames and clips are reused from cache."""
    src = JOBS.get(jid)
    if not src or src["status"] != "done": raise HTTPException(404, "finished job not found")
    spec = json.loads(json.dumps(src["spec"])); by_id = {e["id"]: e for e in edits.get("scenes", [])}
    for sc in spec["scenes"]:
        e = by_id.get(sc["id"], {})
        for k in ("n", "p", "v"):
            if e.get(k) and k in sc: sc[k] = e[k].strip()
        sc.pop("p_simple", None) if e.get("p") else None; sc.pop("v_simple", None) if e.get("v") else None
    new = uuid.uuid4().hex[:10]; a, b = config.DATA_DIR / "runs" / jid, config.DATA_DIR / "runs" / new
    shutil.copytree(a, b, ignore=shutil.ignore_patterns("video.mp4", "result.json", "verification.json", "qa_frames", "frames"))
    JOBS[new] = dict(id=new, style=src["style"], language=src["language"], audience=src["audience"], spec_in=spec, status="queued", events=[], stage="queued", pct=0,
                     msg=f"{Q.qsize()} ahead in the queue", created=time.time(), parent=jid)
    Q.put(new); return {"id": new}

@app.get("/api/jobs/{jid}")
def get_job(jid: str):
    if jid not in JOBS: raise HTTPException(404)
    return _public(JOBS[jid])

@app.get("/api/jobs/{jid}/events")
async def events(jid: str):
    if jid not in JOBS: raise HTTPException(404)
    async def gen():
        sent = 0
        while True:
            j = JOBS[jid]
            while sent < len(j["events"]): yield f"data: {json.dumps(j['events'][sent])}\n\n"; sent += 1
            if j["status"] in ("done", "error"): yield f"event: end\ndata: {json.dumps(_public(j))}\n\n"; return
            await asyncio.sleep(0.5)
    return StreamingResponse(gen(), media_type="text/event-stream")

@app.get("/api/jobs/{jid}/video")
def video(jid: str):
    p = config.DATA_DIR / "runs" / jid / "video.mp4"
    if not p.exists(): raise HTTPException(404)
    return FileResponse(p, media_type="video/mp4", filename=f"pagereel_{jid}.mp4")

@app.get("/api/jobs/{jid}/file/{name}")
def job_file(jid: str, name: str):
    p = (config.DATA_DIR / "runs" / jid / "assets" / name).resolve()
    if not str(p).startswith(str((config.DATA_DIR / "runs" / jid).resolve())) or not p.exists(): raise HTTPException(404)
    return FileResponse(p)

@app.get("/api/health")
def health(): return {"ok": True, "comfy": config.COMFY_BASE_URL, "llm": config.LLM_BASE_URL}

EX = Path(__file__).parent / "examples"
if EX.exists(): app.mount("/examples", StaticFiles(directory=EX), name="examples")
app.mount("/", StaticFiles(directory=UI, html=True), name="ui")
