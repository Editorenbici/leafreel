# Models and licenses

LeafReel does **not** ship any weights. Everything below is downloaded by you and keeps its own license.
Nothing in the default configuration calls a partner node or a paid API.

| Role | Model (as used in the bundled workflows) | License (as published) | Notes |
|---|---|---|---|
| Images, character lock | FLUX.2 [klein] 4B (fp8), `flux2_klein_*.api.json` | Apache-2.0 | The 4B weights are Apache-2.0; the 9B weights are non-commercial. Black Forest Labs recommends output filtering/review. |
| Image → video + ambient audio | LTX-2.5 22B distilled (GGUF Q4), `ltx25_i2v.api.json` | LTX-2.x Community License | Free commercial/production use for entities under US$10M annual revenue; above that a paid agreement is needed. Open weights, not an OSI license. |
| Music | ACE-Step 1.5 XL turbo, `acestep15_music.api.json` | MIT (model card) | Card states generated music may be used commercially. |
| Narration | Qwen3-TTS 1.7B **VoiceDesign** (`tts_qwen3.py`) | Apache-2.0 (Qwen3-TTS family) | The voice is *designed from a text description*; no real person is cloned. Check the license field of the exact repo you download. |
| Script, fact-check, vision QA | Any OpenAI-compatible vision LLM; developed with Qwen3.8-Flash-Next | Check the weights you serve | Swap with `LLM_BASE_URL` / `LLM_MODEL`. |
| Code-rendered styles | GSAP (not bundled; `npm install`), Chromium, ffmpeg | GSAP: GreenSock standard license; Chromium: BSD; ffmpeg: LGPL/GPL depending on build | Installed locally by `scripts/setup_motion.sh`. |

## Responsible-use choices built in

* **No voice cloning.** Voices are generated from descriptions, so LeafReel never imitates a real person.
* **No third-party IP in examples.** The sample document is original text written for this repository.
* **Automatic review.** A vision model rejects frames with garbled text, deformed hands/faces or disturbing content and regenerates them;
  the script is compared with the source document and unsupported claims are rewritten (every change is listed in the UI).
* Generated media should still get a human review before publication.
