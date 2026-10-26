"""Style packs: JSON files in leafreel/styles/ (or $LEAFREEL_STYLES). Add your own by dropping a file there."""
import json, os
from pathlib import Path

def _dirs():
    d = [Path(__file__).parent / "styles"]
    if os.environ.get("LEAFREEL_STYLES"): d.append(Path(os.environ["LEAFREEL_STYLES"]))
    return d

def load_all():
    out = {}
    for d in _dirs():
        for f in sorted(d.glob("*.json")):
            s = json.loads(f.read_text()); out[s["id"]] = s
    return dict(sorted(out.items(), key=lambda kv: kv[1].get("order", 99)))

def get(style_id):
    s = load_all()
    if style_id not in s: raise KeyError(f"unknown style {style_id!r}; available: {', '.join(s)}")
    return s[style_id]
