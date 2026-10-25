#!/usr/bin/env python3
"""Turn a recorded Hermes Agent session (demo/data/hermes_session.json, taken from its own state.db) into a typed-terminal replay page for the demo.
Nothing is invented: prompts, tool calls, tool results and the final answer are the recorded ones (paths shortened with …)."""
import json, re, sys, html
from pathlib import Path
root = Path(__file__).resolve().parent.parent; ev = json.loads((root / "demo/data/hermes_session.json").read_text())
short = lambda s: re.sub(r"/[^\s\"]*?/pagereel_data/runs/", "…/runs/", re.sub(r"/home/maya/estudio/concurso-higgsfield/pagereel/", "", s))
lines = []   # (kind, text, hold_seconds)
for e in ev:
    k = e[0]
    if k == "user": lines.append(("you", short(e[1]).split(" Start it ONCE")[0], 0.5))
    elif k == "call" and e[1] == "tool_call":
        for c in json.loads(e[2])["calls"]:
            a = {k: (short(v) if isinstance(v, str) else v) for k, v in c["arguments"].items()}; name = c["name"].replace("mcp__pagereel__", "pagereel.")
            lines.append(("tool", f"{name}({', '.join(f'{k}={json.dumps(v)}' for k, v in a.items())})", 0.3))
    elif k == "result" and e[1].startswith("mcp__pagereel__"):
        try: j = json.loads(json.loads(e[2])["result"])
        except Exception: continue
        if "job_id" in j and len(j) == 1: lines.append(("out", f"job_id: {j['job_id']}", 0.2))
        elif "stage" in j: lines.append(("out", f"{j['status']} · {j['stage']} · {j['pct']}%" + (f" · {j['msg']}" if j['status'] == 'done' else ""), 0.2))
        elif "title" in j: lines.append(("out", f"title: {j['title']} · {len(j['narration'])} lines · fact-check changes: {len(j['fact_check_changes'])} · verification ok: {j['verification']['ok']}", 0.4))
    elif k == "say" and e is ev[-1]:
        for t in short(e[1]).split("\n"):
            if t.strip(): lines.append(("hermes", t.strip(), 0.0))
# schedule: user/hermes lines are typed char by char, tool/out lines appear fast
t = 0.6; items = []
for kind, text, hold in lines:
    speed = 0.012 if kind in ("tool", "out") else 0.016; d = max(0.25, len(text) * speed)
    items.append(dict(kind=kind, text=text, t0=round(t, 2), d=round(d, 2))); t += d + hold
DUR = round(t + 2.5, 2)
page = f'''<!doctype html><meta charset="utf-8"><style>
*{{box-sizing:border-box;margin:0}}html,body{{width:1280px;height:720px;overflow:hidden;background:#0d1020;font-family:'DejaVu Sans Mono','Noto Sans Mono',monospace}}
body{{background:radial-gradient(900px 500px at 85% 0%,rgba(124,140,255,.25),transparent),radial-gradient(800px 500px at 0% 100%,rgba(255,179,71,.18),transparent),#0d1020}}
.win{{position:absolute;left:60px;top:46px;width:1160px;height:628px;border-radius:16px;background:#0b0e1c;border:1px solid #2a3158;box-shadow:0 30px 80px rgba(0,0,0,.5);overflow:hidden}}
.bar{{height:44px;background:#151a30;display:flex;align-items:center;gap:8px;padding:0 16px;color:#9aa3cf;font-size:16px}}.dot{{width:12px;height:12px;border-radius:50%}}
.body{{padding:20px 26px;font-size:19px;line-height:1.5;color:#dfe3ff;white-space:pre-wrap;word-break:break-word}}
.you{{color:#7c8cff}}.tool{{color:#ffb347}}.out{{color:#8be9c1;padding-left:26px}}.hermes{{color:#eef1ff}}.lab{{font-weight:700;margin-right:10px}}
.cur{{display:inline-block;width:10px;height:20px;background:#ffb347;vertical-align:-3px}}
</style><body><div class="win"><div class="bar"><span class="dot" style="background:#ff5f56"></span><span class="dot" style="background:#ffbd2e"></span><span class="dot" style="background:#27c93f"></span><span style="margin-left:14px">Hermes Agent · local Qwen3.8 Flash Next · MCP: pagereel</span></div><div class="body" id="b"></div></div>
<script>
const items={json.dumps(items)};const b=document.getElementById('b');
const lab={{you:'you ▸ ',tool:'⚙ ',out:'↳ ',hermes:''}};
const els=items.map(i=>{{const d=document.createElement('div');d.className=i.kind;b.appendChild(d);return d}});
function seek(t){{let last=-1;items.forEach((i,k)=>{{const p=Math.max(0,Math.min(1,(t-i.t0)/i.d));
 if(t<i.t0){{els[k].style.display='none';return}} els[k].style.display='block';const n=Math.floor(i.text.length*p);
 els[k].innerHTML=(i.kind==='hermes'&&k>0&&items[k-1].kind!=='hermes'?'<span class="lab you">hermes ▸ </span>':(lab[i.kind]?'<span class="lab">'+lab[i.kind]+'</span>':''))+i.text.slice(0,n).replace(/&/g,'&amp;').replace(/</g,'&lt;');
 if(p<1||k===items.length-1&&t<{DUR}-1)last=k;}});
 if(last>=0)els[last].insertAdjacentHTML('beforeend','<span class="cur"></span>');
 b.style.transform='translateY('+(-Math.max(0,b.scrollHeight-560))+'px)';}}
window.DUR={DUR};window.seek=seek;window.gsap=true;seek(0);
</script>'''
Path(sys.argv[1] if len(sys.argv) > 1 else root / "demo/terminal.html").write_text(page); print(f"{len(items)} lines, {DUR}s")
