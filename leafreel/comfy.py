"""Thin layer over the Comfy SDK: run the bundled API-format workflows with named parameters.

Every heavy step (images, character-locked images, image->video with audio, music) is a ComfyUI workflow in
`leafreel/workflows/*.api.json`, executed through `comfy_sdk.Comfy`. Swap COMFY_BASE_URL to run the same
code on a local ComfyUI (comfy-api-proxy), a Comfy API deployment or Comfy Cloud.
"""
import json, subprocess, tempfile
from pathlib import Path
from comfy_sdk import Comfy
from . import config

WF_DIR = Path(__file__).parent / "workflows"
FPS_LTX = 24

# logical parameter -> [(node id, input name), ...]; "out" = output node id
SPEC = {
    "flux2_klein_t2i": dict(file="flux2_klein_t2i.api.json", out="9",
        params=dict(prompt=[("74", "text")], seed=[("73", "noise_seed")], width=[("62", "width"), ("66", "width")], height=[("62", "height"), ("66", "height")])),
    "flux2_klein_ref": dict(file="flux2_klein_ref.api.json", out="9",
        params=dict(prompt=[("74", "text")], seed=[("73", "noise_seed")], width=[("62", "width"), ("66", "width")], height=[("62", "height"), ("66", "height")], reference=[("80", "image")])),
    "ltx25_i2v": dict(file="ltx25_i2v.api.json", out="75",
        params=dict(image=[("395", "image")], prompt=[("364", "text")], seed=[("339", "noise_seed")], width=[("356", "width")], height=[("356", "height")],
                    length=[("356", "length")], audio_frames=[("366", "frames_number")])),
    "acestep15_music": dict(file="acestep15_music.api.json", out="111",
        params=dict(tags=[("94", "tags")], seed=[("94", "seed"), ("3", "seed")], bpm=[("94", "bpm")], duration=[("94", "duration")], seconds=[("98", "seconds")])),
}

class Comfy_:
    def __init__(self):
        import os
        os.environ["COMFY_BASE_URL"] = config.COMFY_BASE_URL
        self.client = Comfy(api_key=config.COMFY_API_KEY)

    def _run(self, name, params, dest):
        spec = SPEC[name]; wf = self.client.workflows.from_file(str(WF_DIR / spec["file"]))
        for key, val in params.items():
            for node, inp in spec["params"][key]:
                if isinstance(val, Path): val = self.client.assets.from_file(str(val))
                wf.set_input(node, inp, val)
        job = self.client.run(wf); outs = job.get_outputs(spec["out"])
        if not outs: raise RuntimeError(f"{name}: workflow returned no outputs")
        outs[0].to_file(str(dest)); return Path(dest)

    def image(self, prompt, dest, width=1280, height=720, seed=1, reference=None):
        """Text -> image with FLUX.2 klein; pass `reference` (an earlier image) to lock the same character/look."""
        p = dict(prompt=prompt, seed=seed, width=width, height=height)
        if reference: return self._run("flux2_klein_ref", {**p, "reference": Path(reference)}, dest)
        return self._run("flux2_klein_t2i", p, dest)

    def video(self, image, prompt, dest, seconds=5, width=1280, height=704, seed=1):
        """Image -> video clip (with ambient audio) with LTX-2.5. Image is cropped to width x height first."""
        with tempfile.TemporaryDirectory() as td:
            crop = Path(td) / "start.png"
            subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(image), "-vf", f"scale={width}:{height}:force_original_aspect_ratio=increase,crop={width}:{height}", str(crop)], check=True)
            n = seconds * FPS_LTX + 1
            return self._run("ltx25_i2v", dict(image=crop, prompt=prompt, seed=seed, width=width // 2, height=height // 2, length=n, audio_frames=n), dest)

    def music(self, tags, dest, seconds=75, bpm=100, seed=1):
        """Instrumental track with ACE-Step 1.5."""
        return self._run("acestep15_music", dict(tags=tags, seed=seed, bpm=bpm, duration=float(seconds), seconds=float(seconds)), dest)
