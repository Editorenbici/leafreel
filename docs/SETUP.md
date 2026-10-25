# Setup

PageReel needs four things: a **ComfyUI** with the models below (behind `comfy-api-proxy`, or a Comfy API deployment / Comfy Cloud),
an **OpenAI-compatible vision LLM**, a **narration backend**, and `ffmpeg`. Python 3.10+.

## 1. Install PageReel

```bash
git clone <this repo> && cd pagereel
python3 -m venv .venv && . .venv/bin/activate
pip install -e .
# only for the code-rendered styles (flat, chalkboard, kinetic):
scripts/setup_motion.sh        # installs gsap + playwright-core locally; then export CHROMIUM_PATH=/path/to/chromium
```

## 2. ComfyUI + the Comfy SDK proxy

PageReel talks to ComfyUI through the **Comfy SDK** (`comfy-sdk`). For a self-hosted ComfyUI run the open-source proxy next to it:

```bash
pip install comfy-api-proxy
comfy-api-proxy start                 # serves the Comfy API v2 on http://127.0.0.1:8189 and forwards to ComfyUI on :8188
export COMFY_BASE_URL=http://127.0.0.1:8189
```

For a Comfy API deployment use `COMFY_BASE_URL=https://<deployment>.run.comfy.app` and `COMFY_API_KEY=<key>`; for Comfy Cloud leave `COMFY_BASE_URL` unset.

### Models and custom nodes used by the bundled workflows

| Workflow | Files (ComfyUI model folders) | Custom nodes |
|---|---|---|
| `flux2_klein_t2i`, `flux2_klein_ref` | `flux-2-klein-4b-fp8.safetensors` (diffusion_models), `qwen_3_4b_fp8_mixed.safetensors` (text_encoders), `flux2-vae.safetensors` (vae) | none |
| `ltx25_i2v` | `ltx-2.5-22b-distilled-UD-Q4_K_XL.gguf` (unet), `ltx-2.5-video-vae-conv-bf16.safetensors`, `ltx-2.5-audio-vae-bf16.safetensors` (vae), `gemma4-12b-with-proj-ltx-2.5-bf16.safetensors` (text_encoders), `ltx-2.5-latent-spatial-upscaler-x2-bf16-1.0.safetensors` (latent_upscale_models) | ComfyUI-GGUF (`UnetLoaderGGUF`) |
| `acestep15_music` | `acestep_v1.5_xl_turbo_bf16.safetensors` (diffusion_models), `qwen_0.6b_ace15.safetensors`, `qwen_4b_ace15.safetensors` (text_encoders), `ace_1.5_vae.safetensors` (vae) | none |

Tip: open the matching official template in ComfyUI once (FLUX.2 klein text-to-image, LTX-2.5 image-to-video, ACE-Step 1.5) and it will list/download these files.
If your file names differ, edit the JSON in `pagereel/workflows/` (the parameter→node map in `pagereel/comfy.py` stays valid) — `pytest` checks it.

Use only the styles you have models for: the `watercolor`, `papercut`, `pixel`, `clay` styles need FLUX only; `flat`, `chalkboard`, `kinetic` need none of the video models; `cinematic` needs LTX.

## 3. LLM (script, fact-check, vision QA)

Any OpenAI-compatible server with a **vision** model: llama.cpp (`llama-server --jinja -m <model> --mmproj <mmproj>`), vLLM, LM Studio…

```bash
export LLM_BASE_URL=http://127.0.0.1:8090/v1 LLM_MODEL=<served model name>
```

## 4. Narration

* **`TTS_BACKEND=qwen3tts` (default):** `pip install qwen-tts soundfile` on a GPU machine; PageReel runs `pagereel/tts_qwen3.py` locally, or on a remote GPU box over ssh:
  `export TTS_SSH=user@gpu-box TTS_PYTHON=/path/to/venv/bin/python`.
  Voices are *designed from a text description* (see `voice` in each style pack), never cloned from a person.
* **`TTS_BACKEND=http`:** any OpenAI-compatible `/v1/audio/speech` server (Kokoro-FastAPI, Orpheus…):
  `export TTS_HTTP_URL=http://127.0.0.1:8880/v1/audio/speech TTS_HTTP_MODEL=kokoro TTS_HTTP_VOICE=af_heart`.

## 5. Run

```bash
pagereel serve                       # web app on http://127.0.0.1:8100
pagereel styles                      # list style packs
pagereel make examples/volcanoes.md --style papercut --language English
```

Optional: `GPU_COOLDOWN=40` pauses 40 s between LTX clips (useful on a hot or marginal GPU).

## Troubleshooting

* `Connection refused` on the first call → `comfy-api-proxy status`, and check `COMFY_BASE_URL`.
* Clips take minutes → that is LTX-2.5 22B on a 24 GB card; use fewer scenes or another style.
* Vision QA flags a fine frame → it retries up to 3 rounds and then keeps the last attempt; the report lists what remained.
