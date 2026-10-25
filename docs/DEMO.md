# How the demo video was made

`demo/pagereel_demo.mp4` (79 s, captioned) is built from real material, with the same open tools the app uses:

| Part | Source |
|---|---|
| Web app segments | A **real recorded session** of `pagereel serve` (Chromium DevTools screencast): sample document, style pick, a full run on the RTX 3090 shown as a timelapse, the vision-QA gallery and fact-check panel, then *Edit & remake*. |
| Two-node diagram | `demo/diagram.html`, rendered to video by `scripts/render_html.py` (numbers are the measured ones from `docs/BENCHMARKS.md`). |
| Spanish clip | `pagereel/examples/outputs/volcanoes_chalkboard_es.mp4`, made with `--language Spanish`. |
| Agent segment | A **real Hermes Agent session** (local Qwen3.8 Flash Next, shell/file tools disabled, only the PageReel MCP tools) replayed from its own `state.db` by `scripts/make_terminal_page.py`: prompts, tool calls, results and the final answer are the recorded ones; paths are shortened with “…”. |
| Narration | Qwen3-TTS **VoiceDesign** (a designed voice, no real person cloned). |
| Music | ACE-Step 1.5 through the Comfy SDK. |
| Assembly | `scripts/build_demo.py`: every segment lasts exactly as long as the narration lines it illustrates, so picture and voice stay in sync; captions are burned in for muted autoplay. |

Rebuild: record with `scripts/record_demo.mjs`, narrate with `pagereel.tts`, then `python scripts/build_demo.py REC_DIR AUDIO_DIR music.mp3 out.mp4`.
