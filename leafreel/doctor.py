"""`leafreel doctor`: checks the whole recipe (LLM node, ComfyUI node, models, narration, ffmpeg, Chromium) and says which styles are ready."""
import json, os, shlex, shutil, subprocess, urllib.request
from pathlib import Path
import httpx
from . import config, styles, open_weights

WF_DIR = Path(__file__).parent / "workflows"
LOADERS = {"UNETLoader": ["unet_name"], "VAELoader": ["vae_name"], "CLIPLoader": ["clip_name"], "DualCLIPLoader": ["clip_name1", "clip_name2"],
           "UnetLoaderGGUF": ["unet_name"], "LatentUpscaleModelLoader": ["model_name"]}
NEEDS = {"image": ["flux2_klein_t2i.api.json", "flux2_klein_ref.api.json", "acestep15_music.api.json"],
         "cinematic": ["flux2_klein_t2i.api.json", "ltx25_i2v.api.json", "acestep15_music.api.json"], "motion": ["acestep15_music.api.json"]}

class R:
    def __init__(self): self.rows = []
    def add(self, name, ok, detail="", hint=""): self.rows.append((name, ok, detail, hint)); print(f"  {'✓' if ok else ('–' if ok is None else '✗')} {name}: {detail}" + (f"\n      → {hint}" if hint and not ok else ""))
    def ok(self, name): return next((o for n, o, *_ in self.rows if n == name), None)

def _sh(cmd, timeout=15):
    try: return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    except Exception as e: return subprocess.CompletedProcess(cmd, 1, "", str(e))

def check_models(object_info):
    """{workflow: [missing model files / node types]} against a live /object_info."""
    out = {}
    for f in sorted(WF_DIR.glob("*.api.json")):
        miss = []
        for n in json.loads(f.read_text()).values():
            ct = n["class_type"]
            if ct not in object_info: miss.append(f"node {ct} (custom node not installed)"); continue
            for field in LOADERS.get(ct, []):
                have = object_info[ct]["input"]["required"].get(field, [[]])[0]
                if isinstance(have, list) and n["inputs"].get(field) not in have: miss.append(f"{field}={n['inputs'].get(field)}")
        out[f.name] = sorted(set(miss))
    return out

def run():
    r = R(); print(f"LeafReel doctor — LLM {config.LLM_BASE_URL} · Comfy {config.COMFY_BASE_URL}\n")
    print("Tools"); r.add("ffmpeg", bool(shutil.which("ffmpeg") and shutil.which("ffprobe")), shutil.which("ffmpeg") or "not found", "install ffmpeg")
    print("\nLLM node (script, fact-check, vision QA)")
    try:
        models = httpx.get(config.LLM_BASE_URL.rstrip("/") + "/models", timeout=10).json()["data"]; r.add("LLM endpoint", True, ", ".join(m["id"] for m in models)[:90])
        from PIL import Image; import io, tempfile
        with tempfile.NamedTemporaryFile(suffix=".png") as f:
            Image.new("RGB", (96, 96), (220, 20, 20)).save(f.name); from . import llm
            v = llm.vision(f.name, 'What is the dominant color? Reply ONLY with JSON {"color": "..."}'); r.add("vision input", "red" in json.dumps(v).lower(), json.dumps(v)[:60], "serve a vision-capable model (mmproj) or set LLM_MODEL")
    except Exception as e: r.add("LLM endpoint", False, repr(e)[:80], "start an OpenAI-compatible server and set LLM_BASE_URL")
    print("\nGPU node (ComfyUI through the Comfy SDK proxy)")
    try:
        code = httpx.get(config.COMFY_BASE_URL.rstrip("/") + "/api/v2/jobs", timeout=10, headers={"Authorization": f"Bearer {config.COMFY_API_KEY}"}).status_code
        r.add("comfy-api-proxy", code < 500, f"HTTP {code}", "run `comfy-api-proxy start` next to ComfyUI and set COMFY_BASE_URL")
    except Exception as e: r.add("comfy-api-proxy", False, repr(e)[:80], "run `comfy-api-proxy start` next to ComfyUI and set COMFY_BASE_URL")
    direct = os.environ.get("COMFY_DIRECT_URL"); missing = {}
    if direct:
        try:
            oi = json.load(urllib.request.urlopen(direct.rstrip("/") + "/object_info", timeout=60)); missing = check_models(oi)
            for wf, m in missing.items(): r.add(f"models for {wf.split('.')[0]}", not m, "all present" if not m else "; ".join(m)[:110], "see docs/SETUP.md for the files and custom nodes")
            live = {k: v for k, v in open_weights.audit_live(oi).items() if v}; r.add("open weights (live)", not live, "no partner/API nodes" if not live else str(live))
        except Exception as e: r.add("ComfyUI model check", False, repr(e)[:80], "check COMFY_DIRECT_URL (ComfyUI itself, e.g. http://127.0.0.1:8188)")
    else: r.add("ComfyUI model check", None, "skipped", "set COMFY_DIRECT_URL=http://<comfyui-host>:8188 to verify model files and custom nodes")
    bad = {k: v for k, v in open_weights.audit_offline().items() if v}; r.add("open weights (workflows)", not bad, "only local nodes" if not bad else str(bad))
    print("\nNarration")
    if config.TTS_BACKEND == "http":
        try: r.add("TTS http", httpx.get(config.TTS_HTTP_URL.rsplit("/v1", 1)[0] + "/v1/models", timeout=10).status_code < 500, config.TTS_HTTP_URL)
        except Exception as e: r.add("TTS http", False, repr(e)[:80], "start a Kokoro-FastAPI/OpenAI-compatible TTS server")
    else:
        probe = "import qwen_tts, torch; print(torch.cuda.is_available())"
        # the remote login shell may be fish/zsh: hand it a single bash -c string
        cmd = ["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=8", config.TTS_SSH, "bash -c " + shlex.quote(f"{config.TTS_PYTHON} -c {shlex.quote(probe)}")] if config.TTS_SSH else [config.TTS_PYTHON, "-c", probe]
        o = _sh(cmd, 40); r.add("Qwen3-TTS" + (f" on {config.TTS_SSH}" if config.TTS_SSH else ""), o.returncode == 0 and "True" in o.stdout, "CUDA available" if "True" in o.stdout else ((o.stderr.strip().splitlines() or ["not importable"])[-1])[:80], "pip install qwen-tts soundfile on the GPU node; set TTS_SSH/TTS_PYTHON")
    print("\nCode-rendered styles")
    root = Path(__file__).resolve().parent.parent; gsap = (root / "node_modules/gsap/dist/gsap.min.js").exists()
    r.add("gsap", gsap, "node_modules/gsap", "run scripts/setup_motion.sh"); chrome = config.CHROMIUM and Path(config.CHROMIUM).exists()
    r.add("Chromium", bool(chrome), config.CHROMIUM or "CHROMIUM_PATH not set", "export CHROMIUM_PATH=/path/to/chromium")
    print("\nStyles ready")
    base = bool(r.ok("ffmpeg") and r.ok("LLM endpoint") and r.ok("comfy-api-proxy"))
    tts_ok = any(ok for n, ok, *_ in r.rows if n.startswith(("Qwen3-TTS", "TTS http")))
    wf_ok = lambda files: all(not missing.get(f) for f in files) if direct and missing else True
    ready = {}
    for sid, s in styles.load_all().items():
        eng = s["engine"]; ok = base and tts_ok and wf_ok(NEEDS[eng]) and (eng != "motion" or (gsap and chrome))
        ready[sid] = ok; print(f"  {'✓' if ok else '✗'} {sid:<11} {s['name']}")
    if not direct: print("  (model files were not verified; set COMFY_DIRECT_URL to be sure)")
    return 0 if any(ready.values()) else 1
