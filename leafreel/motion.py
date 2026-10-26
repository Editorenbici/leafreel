"""Code-rendered styles: scene spec (layouts + data) + narration timings -> HTML with a paused GSAP timeline ->
deterministic frames captured by headless Chromium (parallel workers) -> ffmpeg. Themes: flat, chalkboard, kinetic.
Needs `npm install gsap playwright-core` (see scripts/setup_motion.sh) and a Chromium binary (CHROMIUM_PATH)."""
import json, os, re, subprocess, html, time, shutil
from pathlib import Path
from . import config, assemble

ROOT = Path(__file__).resolve().parent.parent
GSAP = f"file://{ROOT}/node_modules/gsap/dist/gsap.min.js"
NODE = os.environ.get("NODE_BIN", "node")
LEAD = 0.5
E = lambda s: html.escape(str(s), quote=True)

THEMES = {
"flat": dict(bg="#F3F8FF", fg="#1B2B4B", acc=["#2F6FED", "#FF8A3D", "#2BB673", "#E8456B"], font="DejaVu Sans", card="#FFFFFF", ease="back.out(1.6)",
  css="""body{background:#F3F8FF} .blob{position:absolute;border-radius:50%;opacity:.35} .card{background:#fff;border-radius:28px;box-shadow:0 10px 0 rgba(27,43,75,.10),0 18px 40px rgba(27,43,75,.10)}
  .h{background:var(--a0);color:#fff;border-radius:40px;padding:10px 34px;font-weight:800;letter-spacing:1px}"""),
"chalkboard": dict(bg="#1E3A2F", fg="#F4F1E6", acc=["#FFF3A0", "#9FE3FF", "#FFB3C7", "#B8F5B0"], font="DejaVu Sans", card="transparent", ease="power2.out",
  css="""body{background:radial-gradient(ellipse at 30% 20%,#2A4D3E 0%,#1E3A2F 55%,#162B23 100%)} .marco{position:absolute;inset:0;border:22px solid #7a5230;box-shadow:inset 0 0 60px rgba(0,0,0,.45);pointer-events:none;z-index:20}
  .card{border:5px dashed var(--fg);border-radius:18px;filter:url(#rough)} .ic{filter:grayscale(1) brightness(1.7) contrast(1.15)} .h{color:var(--a0);font-weight:800;border-bottom:6px solid var(--a0);padding:0 8px 4px;filter:url(#rough)}
  .t,.s,.big{filter:url(#rough);text-shadow:0 0 6px rgba(255,255,255,.25)}"""),
"kinetic": dict(bg="#0E1330", fg="#FFFFFF", acc=["#FFD23F", "#3EE6C3", "#FF5C8A", "#7C8CFF"], font="DejaVu Sans", card="transparent", ease="expo.out",
  css="""body{background:linear-gradient(135deg,#0E1330 0%,#1B1F5E 60%,#2B1B5E 100%)} .barra{position:absolute;height:14px;border-radius:7px;opacity:.9} .pal{display:inline-block;margin:0 .18em;will-change:transform} .kw{color:var(--a0)}"""),
}

def emoji_de(e):
    if e.get("emoji"): return e["emoji"]
    d = e.get("d") or {}
    if isinstance(d, dict):
        if d.get("emoji"): return d["emoji"]
        for k in ("items",):
            for it in d.get(k, []) if isinstance(d.get(k), list) else []:
                if isinstance(it, dict) and it.get("emoji"): return it["emoji"]
        for k in ("left", "right"):
            if isinstance(d.get(k), dict) and d[k].get("emoji"): return d[k]["emoji"]
    return "⭐"

def tok(line, keys):
    ps = line.split(); cl = {re.sub(r"\W", "", c.lower()) for k in keys for c in k.split()}
    return [(p, re.sub(r"\W", "", p.lower()) in cl) for p in ps]

def contenido(e, i, theme):
    """HTML de una escena según layout. Devuelve (html, lista de selectores a animar en orden)."""
    L, d = e["layout"], e.get("d", {}) or {}; a = THEMES[theme]["acc"]
    ic = lambda s: f'<div class="ic">{E(s or "⭐")}</div>'
    def card(it, k): return f'<div class="card it" style="--c:{a[k % 4]}">{ic(it.get("emoji"))}<div class="t">{E(it.get("title",""))}</div><div class="s">{E(it.get("text",""))}</div></div>'
    enc = f'<div class="h hd">{E(d.get("heading",""))}</div>' if d.get("heading") else ""
    if L == "title": return f'<div class="tit">{ic(d.get("emoji"))}<h1 class="it">{E(d.get("title",""))}</h1><div class="sub it">{E(d.get("subtitle",""))}</div></div>'
    if L == "cards": return f'{enc}<div class="fila">' + "".join(card(it, k) for k, it in enumerate(d.get("items", [])[:4])) + "</div>"
    if L == "steps": return f'{enc}<div class="fila">' + "".join(f'<div class="card it paso" style="--c:{a[k%4]}"><div class="num">{k+1}</div>{ic(it.get("emoji"))}<div class="t">{E(it.get("title",""))}</div></div>' for k, it in enumerate(d.get("items", [])[:3])) + "</div>"
    if L == "compare": return f'{enc}<div class="fila">' + card(d.get("left", {}), 0) + '<div class="vs it">VS</div>' + card(d.get("right", {}), 1) + "</div>"
    if L == "stat": return f'<div class="dato">{ic(d.get("emoji"))}<div class="big it">{E(d.get("big",""))}</div><div class="s it">{E(d.get("text",""))}</div></div>'
    if L == "quote": return f'<div class="dato">{ic(d.get("emoji"))}<div class="cita it">{E(d.get("text",""))}</div></div>'
    if L == "cycle": return f'{enc}<div class="fila ciclo">' + '<div class="flecha it">➜</div>'.join(f'<div class="card it" style="--c:{a[k%4]}">{ic(it.get("emoji"))}<div class="t">{E(it.get("title",""))}</div></div>' for k, it in enumerate(d.get("items", [])[:4])) + "</div>"
    if L == "list": return f'{enc}<ul class="lista">' + "".join(f'<li class="it" style="--c:{a[k%4]}">{E(x)}</li>' for k, x in enumerate(d.get("items", [])[:4])) + "</ul>"
    return f'<div class="dato"><div class="cita it">{E(e["n"])}</div></div>'

CSS = """*{box-sizing:border-box;margin:0}html,body{width:1280px;height:720px;overflow:hidden;font-family:'DejaVu Sans','Noto Sans',sans-serif;color:var(--fg)}
#stage{position:relative;width:1280px;height:720px;overflow:hidden}.scene{position:absolute;inset:0;display:flex;flex-direction:column;align-items:center;justify-content:center;gap:24px;padding:50px 70px 140px;opacity:0}
.fila{display:flex;align-items:stretch;justify-content:center;gap:26px;width:100%}.card{flex:1;max-width:330px;padding:26px 20px;display:flex;flex-direction:column;align-items:center;gap:10px;text-align:center;border-color:var(--c)}
.ic{font-size:92px;line-height:1.1;font-family:'Noto Color Emoji'}.t{font-size:32px;font-weight:800;line-height:1.15}.s{font-size:24px;line-height:1.25;opacity:.92}
.h{font-size:34px;text-transform:uppercase;font-weight:800}.tit{display:flex;flex-direction:column;align-items:center;gap:16px;text-align:center}.tit h1{font-size:76px;line-height:1.05}.sub{font-size:34px;opacity:.9}
.dato{display:flex;flex-direction:column;align-items:center;gap:14px;text-align:center;max-width:1000px}.big{font-size:150px;font-weight:900;line-height:1;color:var(--a1)}.cita{font-size:54px;font-weight:800;line-height:1.2}
.num{width:60px;height:60px;border-radius:50%;background:var(--c);color:#fff;font-size:36px;font-weight:900;display:flex;align-items:center;justify-content:center}.vs{font-size:44px;font-weight:900;align-self:center;color:var(--a2)}
.flecha{font-size:56px;align-self:center;color:var(--a1)}.ciclo .card{max-width:260px}.lista{list-style:none;display:flex;flex-direction:column;gap:10px;width:900px}
.lista li{font-size:32px;font-weight:700;padding:9px 24px 9px 36px;border-left:14px solid var(--c);background:rgba(255,255,255,.08);border-radius:10px}
#sub{position:absolute;left:0;right:0;bottom:34px;text-align:center;z-index:30;padding:0 90px}#sub span{display:inline-block;background:rgba(0,0,0,.62);color:#fff;font-size:30px;font-weight:700;line-height:1.3;padding:8px 22px;border-radius:12px}
.kin{position:absolute;inset:0;display:flex;flex-direction:column;align-items:center;justify-content:center;text-align:center;padding:60px 90px;opacity:0}.kin .txt{font-size:70px;font-weight:900;line-height:1.18}.kin .ic{font-size:120px;margin-bottom:10px}
"""

def build(spec, T, theme):
    TH = THEMES[theme]; esc = spec["scenes"]; S = [(a + LEAD, b + LEAD) for a, b, _ in T]; fin = S[-1][1] + 1.2
    ends = [S[i+1][0] if i + 1 < len(S) else fin for i in range(len(S))]
    vars_ = f":root{{--fg:{TH['fg']};" + "".join(f"--a{k}:{c};" for k, c in enumerate(TH["acc"])) + "}"
    body = []; js = ["const tl=gsap.timeline({paused:true});", f"const EASE='{TH['ease']}';"]
    if theme == "flat":
        for k, (x, y, s, c) in enumerate([(-80, 480, 360, "#CFE0FF"), (1080, -60, 300, "#FFE0C2"), (900, 520, 240, "#CDEFD9")]):
            body.append(f'<div class="blob" id="b{k}" style="left:{x}px;top:{y}px;width:{s}px;height:{s}px;background:{c}"></div>'); js.append(f"tl.to('#b{k}',{{y:{(-1)**k*60},x:{(-1)**(k+1)*40},duration:{fin},ease:'none'}},0);")
    if theme == "chalkboard": body.append('<div class="marco"></div>')
    if theme == "kinetic":
        for k in range(6):
            body.append(f'<div class="barra" id="r{k}" style="left:{-300+k*220}px;top:{60+k*110}px;width:{260+k*30}px;background:{TH["acc"][k%4]};opacity:.18"></div>'); js.append(f"tl.to('#r{k}',{{x:{(1 if k%2 else -1)*500},duration:{fin},ease:'none'}},0);")
    for i, e in enumerate(esc):
        a0, a1 = S[i][0] - 0.12, ends[i]; sid = f"sc{i}"
        if theme == "kinetic":
            ws = tok(e["n"], e.get("key", [])); n = len(ws); t0, t1 = S[i]; pal = "".join(f'<span class="pal{" kw" if k else ""}" id="w{i}_{j}">{E(w)}</span>' for j, (w, k) in enumerate(ws))
            body.append(f'<div class="kin" id="{sid}"><div class="ic" id="e{i}">{E(emoji_de(e))}</div><div class="txt">{pal}</div></div>')
            js.append(f"tl.set('#{sid}',{{opacity:1}},{a0:.3f});tl.from('#e{i}',{{scale:0,rotation:-25,duration:.5,ease:'back.out(2)'}},{a0:.3f});")
            for j in range(n):
                tw = t0 + (t1 - t0) * (j / max(n, 1)) * 0.92; js.append(f"tl.from('#w{i}_{j}',{{y:70,opacity:0,scale:.6,rotation:{(-6 if j%2 else 6)},duration:.38,ease:EASE}},{tw:.3f});")
            js.append(f"tl.to('#{sid}',{{opacity:0,duration:.3}},{ends[i]-0.3:.3f});tl.set('#{sid}',{{opacity:0}},{ends[i]:.3f});")
            continue
        h = contenido(e, i, theme); body.append(f'<div class="scene" id="{sid}">{h}</div>')
        js.append(f"tl.set('#{sid}',{{opacity:1}},{a0:.3f});const its{i}=document.querySelectorAll('#{sid} .hd,#{sid} .it,#{sid} .ic');")
        js.append(f"tl.from(its{i},{{y:60,opacity:0,scale:.82,duration:.55,ease:EASE,stagger:{min(0.35,(S[i][1]-S[i][0])/(2.5*max(1,3))):.2f}}},{a0+0.05:.3f});")
        js.append(f"tl.to('#{sid}',{{scale:1.03,duration:{ends[i]-a0:.2f},ease:'none'}},{a0:.3f});tl.to('#{sid}',{{opacity:0,duration:.3}},{ends[i]-0.3:.3f});tl.set('#{sid}',{{opacity:0,scale:1}},{ends[i]:.3f});")
    if theme != "kinetic":
        body.append('<div id="sub"><span></span></div>')
        for i, (a, b, txt) in enumerate(T):
            js.append(f"tl.call(()=>{{const s=document.querySelector('#sub span');s.textContent={json.dumps(txt, ensure_ascii=False)};s.style.visibility='visible'}},null,{a+LEAD:.3f});tl.call(()=>{{document.querySelector('#sub span').style.visibility='hidden'}},null,{b+LEAD+0.2:.3f});")
    filt = '<svg width="0" height="0"><filter id="rough"><feTurbulence type="fractalNoise" baseFrequency="0.03" numOctaves="2" seed="3"/><feDisplacementMap in="SourceGraphic" scale="5"/></filter></svg>'
    LANG = (spec.get('language') or 'en')[:2].lower()
    page = (f'<!doctype html><html lang="{LANG}"><head><meta charset="utf-8"><style>{vars_}{CSS}{TH["css"]}</style><script src="{GSAP}"></script></head><body>{filt}<div id="stage">' + "".join(body) +
            "</div><script>" + "\n".join(js) + f"\nwindow.DUR={fin:.3f};window.seek=t=>{{tl.time(t,false)}};document.querySelector('#sub span')&&(document.querySelector('#sub span').style.visibility='hidden');</script></body></html>")
    return page, fin

RENDER = r"""
import { createRequire } from 'module'; import fs from 'fs'; import path from 'path';
const require = createRequire(process.env.LEAFREEL_ROOT + '/package.json'); const { chromium } = require('playwright-core');
const [,, file, outdir, fps, w, k, K] = process.argv; const FPS = +fps, W = +w, KK = +k, NK = +K;
const browser = await chromium.launch({ executablePath: process.env.CHROMIUM_PATH || undefined, args: ['--no-sandbox', '--disable-dev-shm-usage', '--disable-gpu', '--allow-file-access-from-files', '--force-color-profile=srgb'] });
const page = await browser.newPage({ viewport: { width: 1280, height: 720 } }); await page.goto('file://' + path.resolve(file)); await page.waitForFunction(() => window.seek && window.gsap);
await page.waitForTimeout(400);
const dur = await page.evaluate(() => window.DUR), N = Math.ceil(dur * FPS);
for (let f = KK; f < N; f += NK) { await page.evaluate((t) => window.seek(t), f / FPS); await page.screenshot({ path: `${outdir}/f${String(f).padStart(5, '0')}.jpg`, type: 'jpeg', quality: 92 }); }
await browser.close(); console.log(N);
"""

def short_tmp() -> Path:
    """A private temp dir with a SHORT path (Chromium's unix sockets fail on long TMPDIR paths)."""
    import tempfile
    return Path(tempfile.mkdtemp(prefix="pr", dir="/tmp" if os.path.isdir("/tmp") and os.access("/tmp", os.W_OK) else None))

def render(work, spec, timings, theme, fps=25, workers=8, log=print):
    """Render the HTML timeline to a silent mp4. Returns its path."""
    work = Path(work); page, total = build(spec, timings, theme)
    (work / "index.html").write_text(page); (work / "render_worker.mjs").write_text(RENDER)
    fr = work / "frames"; shutil.rmtree(fr, ignore_errors=True); fr.mkdir()
    # Chromium puts unix sockets under TMPDIR; a path over ~100 chars (common in agent sandboxes) kills it at launch with SIGTRAP.
    # Give it a private, SHORT temp dir (also covers a missing/unwritable HOME or TMPDIR).
    scratch = short_tmp()
    env = {**os.environ, "LEAFREEL_ROOT": str(ROOT), "CHROMIUM_PATH": config.CHROMIUM, "TMPDIR": str(scratch), "HOME": str(scratch)}
    t0 = time.time(); ps = [subprocess.Popen([NODE, str(work / "render_worker.mjs"), str(work / "index.html"), str(fr), str(fps), "1280", str(k), str(workers)],
                                              stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, env=env) for k in range(workers)]
    for p in ps:
        _, err = p.communicate()
        if p.returncode: raise RuntimeError("render: " + err[-400:])
    log(f"{len(os.listdir(fr))} frames in {time.time()-t0:.0f}s with {workers} workers ({total:.1f}s of video)")
    silent = work / "silent.mp4"
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-framerate", str(fps), "-i", str(fr / "f%05d.jpg"), "-c:v", "libx264", "-crf", "17", "-pix_fmt", "yuv420p", str(silent)], check=True)
    shutil.rmtree(fr, ignore_errors=True); shutil.rmtree(scratch, ignore_errors=True); return silent
