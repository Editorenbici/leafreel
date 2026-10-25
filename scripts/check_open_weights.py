#!/usr/bin/env python3
"""Fails (exit 1) if any bundled workflow uses a partner/API node. Offline allow-list check, plus a live check when COMFY_DIRECT_URL points at ComfyUI.
Usage: scripts/check_open_weights.py"""
import json, os, sys, urllib.request
from pagereel import open_weights as ow
bad = {k: v for k, v in ow.audit_offline().items() if v}
for k, v in ow.audit_offline().items(): print(f"{'OK ' if not v else 'BAD'} {k}: {', '.join(v) if v else 'only local nodes'}")
url = os.environ.get("COMFY_DIRECT_URL")
if url:
    try:
        oi = json.load(urllib.request.urlopen(url.rstrip("/") + "/object_info", timeout=60))
        live = {k: v for k, v in ow.audit_live(oi).items() if v}; bad.update(live); print("live check:", "clean" if not live else live)
    except Exception as e: print("live check skipped:", e)
sys.exit(1 if bad else 0)
