"""Command line: `pagereel make doc.pdf --style pixel` / `pagereel styles` / `pagereel serve`."""
import argparse, sys, time
from pathlib import Path
from . import styles, config

def read_doc(path):
    p = Path(path)
    if p.suffix.lower() == ".pdf":
        from pypdf import PdfReader
        return "\n".join(pg.extract_text() or "" for pg in PdfReader(str(p)).pages)
    return p.read_text(encoding="utf-8")

def main(argv=None):
    ap = argparse.ArgumentParser(prog="pagereel"); sub = ap.add_subparsers(dest="cmd", required=True)
    m = sub.add_parser("make", help="make a video from a document"); m.add_argument("doc"); m.add_argument("--style", default="watercolor")
    m.add_argument("--language", default="English"); m.add_argument("--audience", default="curious learners aged 8-12"); m.add_argument("--camera", default="auto", help="cinematic style only: auto, push-in, pull-back, pan, orbit, crane-up, handheld, static"); m.add_argument("--out", default=None)
    sub.add_parser("styles", help="list style packs")
    s = sub.add_parser("serve", help="start the web app"); s.add_argument("--host", default="127.0.0.1"); s.add_argument("--port", type=int, default=8100)
    a = ap.parse_args(argv)
    if a.cmd == "styles":
        for st in styles.load_all().values(): print(f"{st['id']:<11} {st['engine']:<10} {st['name']} - {st.get('blurb','')}")
    elif a.cmd == "make":
        from . import pipeline
        out = Path(a.out or config.DATA_DIR / "runs" / f"{Path(a.doc).stem}_{a.style}_{int(time.time())}")
        r = pipeline.make(read_doc(a.doc), a.style, out, a.language, a.audience, camera=a.camera); print("\n->", r["video"])
    elif a.cmd == "serve":
        import uvicorn; uvicorn.run("pagereel.server:app", host=a.host, port=a.port)

if __name__ == "__main__": sys.exit(main())
