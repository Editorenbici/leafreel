# 🎞️ LeafReel — drop a page, get a reel

**LeafReel turns any document into a narrated explainer video in eight completely different visual styles — with open-weight models, orchestrated through ComfyUI and the Comfy SDK.**

Paste text or drop a PDF, pick a look (storybook watercolor, cut-paper collage, 16-bit pixel game, claymation, cinematic LTX clips, flat motion graphics, chalkboard, kinetic typography), press one button. Minutes later you get a ~1 minute reel with designed voice, music and subtitles — plus a **quality report** that proves what was checked.

> **[Live page and demo](https://editorenbici.github.io/leafreel/)** · Built for the [Open Source Higgsfield](https://comfy.org/open-source-higgsfield) challenge. Category: **Open Weights Only** (no partner nodes, no paid APIs).

<p align="center"><a href="demo/leafreel_demo.mp4"><img src="docs/img/demo.gif" alt="LeafReel demo: a real run on two nodes" width="720"></a><br><sub>A real run, timelapsed. <a href="demo/leafreel_demo.mp4">Watch the 80-second demo</a> · <a href="https://editorenbici.github.io/leafreel/">live page with all the example films</a></sub></p>

<p align="center"><img src="docs/img/app.png" alt="LeafReel web app" width="860"></p>

## Why it is different

| | |
|---|---|
| **Same document, eight films** | A style is a small JSON "style pack" (engine, prompt style, transition, camera, soundtrack, narrator). Add yours in a minute; it appears in the UI and CLI. |
| **Frames are inspected, not trusted** | A vision LLM looks at *every* generated frame (garbled text, deformed hands, disturbing content, wrong style). Bad frames are regenerated with an automatically simplified prompt (up to 3 rounds). |
| **Facts are checked against your document** | After writing the script, the LLM re-reads your source and rewrites any concrete claim it cannot support. Every change is shown in the UI. |
| **Character lock** | The first frame becomes a reference (`ReferenceLatent` in FLUX.2 klein), so the protagonist keeps the same face, hair and clothes in all 12 scenes. |
| **Code + models, together** | Pixels from ComfyUI workflows; cards, chalk, and kinetic type are *rendered from code* (HTML + GSAP in headless Chromium), deterministic and parallel (1,200 frames in ~7 s). |
| **Edit & remake** | Change a narration line or reshoot one scene's prompt; only what changed is regenerated (frames and clips are cached by prompt). |
| **Honest verification** | Final video is measured (−16 LUFS, peak, black frames, silences) and 8 real frames are reviewed by the vision model. |
| **No voice cloning** | Narrators are *designed* from a text description (Qwen3-TTS VoiceDesign). No real person's voice is imitated. |
| **Agent-native** | An MCP server (`leafreel-mcp`) lets Hermes Agent, OpenClaw, pi, Claude Code… send a PDF from a chat app and get the reel back. Verified end to end with Hermes Agent driven by a local Qwen. See [docs/AGENT_INTEGRATION.md](docs/AGENT_INTEGRATION.md). |
| **A recipe, not a pile of parts** | Two nodes (a vision-LLM "brain" + a ComfyUI "studio"), systemd units and one command — `leafreel doctor` — that checks the LLM, vision input, the Comfy SDK proxy, every model file and which styles are ready. [docs/RECIPE.md](docs/RECIPE.md) |
| **Provably open weights** | `scripts/check_open_weights.py` fails if any bundled workflow contains a partner/API node (checked offline and, when ComfyUI is reachable, against its own `api_node` flags). It runs in CI. |
| **QA is visible** | The UI shows every frame the vision reviewer rejected next to its replacement, with the reason. |

## Built on the Comfy Developer Platform

Every generative step is a ComfyUI **API-format workflow** (`leafreel/workflows/*.api.json`) run with `comfy-sdk`:

```python
from comfy_sdk import Comfy
client = Comfy(api_key="local")                       # COMFY_BASE_URL picks local proxy, Comfy API deployment or Comfy Cloud
wf = client.workflows.from_file("leafreel/workflows/flux2_klein_ref.api.json")
wf.set_input("74", "text", prompt); wf.set_input("80", "image", client.assets.from_file("hero.png"))
client.run(wf).get_outputs("9")[0].to_file("scene.png")
```

Workflows: FLUX.2 klein text→image, FLUX.2 klein with reference (character lock), LTX-2.5 image→video **with ambient audio**, ACE-Step 1.5 music.
See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

## Styles

| Style | Engine | Look |
|---|---|---|
| `watercolor` | ComfyUI images | Hand-painted storybook with a recurring character |
| `papercut` | ComfyUI images | Layered cardstock and kraft paper, soft shadows |
| `pixel` | ComfyUI images + code | True 16-bit pixel grid, stepped retro camera pans |
| `clay` | ComfyUI images | Claymation: everything modelled in colored clay |
| `cinematic` | ComfyUI images → LTX-2.5 video | Photoreal establishing shots with ambient sound, no people |
| `flat` | Code-rendered | Vector cards, steps, charts |
| `chalkboard` | Code-rendered | Chalk look with wobbly edges |
| `kinetic` | Code-rendered | Words fly in on the narration |

Examples (same input, `examples/volcanoes.md`): `examples/outputs/`.

## Measured results

One ~52 s reel per style from the same 400-word document, on an RTX 3090 (24 GB) that was **thermally throttled** during all runs (details in [docs/BENCHMARKS.md](docs/BENCHMARKS.md)):

| Style family | End-to-end | Where the time goes |
|---|---|---|
| Code-rendered (`flat`, `chalkboard`, `kinetic`) | **2.2–2.7 min** | ~50 s script + fact-check, ~30 s voice, ~10 s render (1,200 frames, 8 parallel workers), music, verification |
| ComfyUI images (`papercut`, `pixel`, `watercolor`, `clay`) | **4.6–5.7 min** | 12 frames ≈ 80–120 s (character-locked), vision QA 35–90 s incl. regenerations |
| `cinematic` (FLUX frames → 10 LTX-2.5 clips with audio) | **35 min** | LTX-2.5 22B ≈ 140 s per 5-second clip (with a 40 s cooldown between clips) |

Edit & remake is cheaper because frames and clips are cached by prompt: a remake after changing one narration line took **225 s instead of 383 s** (road-safety sample, `papercut`).

All eight reels passed the automatic checks (−16 LUFS, no black frames or long silences, vision review of 8 real frames).

## Quick start

```bash
pip install -e '.[agents]' && scripts/setup_motion.sh
export COMFY_BASE_URL=http://127.0.0.1:8189      # comfy-api-proxy in front of your ComfyUI
export LLM_BASE_URL=http://127.0.0.1:8090/v1     # any OpenAI-compatible vision LLM
leafreel doctor                                  # checks every node/model and lists the styles ready on your hardware
leafreel serve                                   # http://127.0.0.1:8100
# or: leafreel make examples/volcanoes.md --style papercut --language Spanish
```

Full instructions, model files and custom nodes: [docs/SETUP.md](docs/SETUP.md). Models and licenses: [docs/MODELS.md](docs/MODELS.md). Measured timings: [docs/BENCHMARKS.md](docs/BENCHMARKS.md).

## Hardware

Developed on two boxes — an ARM mini-PC (121 GB unified memory: app, LLM, ffmpeg, Chromium) and one **RTX 3090 (24 GB)** running ComfyUI, `comfy-api-proxy` and Qwen3-TTS — but it all fits on one machine with a 24 GB GPU. Jobs run one at a time on purpose.

## Extending

* **New style:** add `leafreel/styles/<id>.json` (copy `pixel.json`).
* **New workflow step:** drop an API-format JSON in `leafreel/workflows/` and register parameter→node ids in `leafreel/comfy.py::SPEC`; `pytest` verifies the mapping.
* **Other languages:** pick the language in the UI/CLI (`--language Spanish`); the narrator speaks it and subtitles follow.
* **Other TTS / LLM:** `TTS_BACKEND=http`, `LLM_BASE_URL`.

## Limits (honest)

* LTX-2.5 22B clips take about 2–3 minutes each on a 3090, so the `cinematic` style is the slow one (~30 min per reel).
* The narrator is designed, not accent-specific: regional accents are not guaranteed.
* The QA model can flag a fine frame (scribbles inside a drawn map); after three rounds the last attempt is kept and listed in the report.
* Fact-checking compares with *your* document only; review before publishing. Generated media should be reviewed by a human.

## License

Apache-2.0 for the code. Model weights keep their own licenses ([docs/MODELS.md](docs/MODELS.md)). Example texts are original.
