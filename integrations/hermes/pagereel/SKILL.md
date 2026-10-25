---
name: pagereel
description: "Turn a document or PDF into a narrated explainer video (8 visual styles) with open-weight models on ComfyUI."
version: 0.1.0
author: PageReel contributors
license: Apache-2.0
platforms: [linux, macos]
metadata:
  hermes:
    tags: [Video, Education, ComfyUI, Open-weights, MCP]
    related_skills: [comfyui]
---

# PageReel: document -> reel

## When to use
The user wants a video from a document, article, lesson, chapter or PDF ("make a video from this", "explain this PDF as a short film",
"make it in pixel-art / claymation / chalkboard style"), or wants to change a reel you already made.

## Setup (once)
Register the MCP server in `~/.hermes/config.yaml` (see `docs/AGENT_INTEGRATION.md`):

```yaml
mcp_servers:
  pagereel:
    command: /path/to/pagereel/.venv/bin/pagereel-mcp
    env: { COMFY_BASE_URL: "http://127.0.0.1:8189", LLM_BASE_URL: "http://127.0.0.1:8090/v1", LLM_MODEL: "<served model>" }
```
Without MCP you can run the CLI: `pagereel make <doc> --style <id> --language <lang>`.

## How to work
1. Call `list_styles` if the user has not chosen a look. Suggestions: story with a character -> `watercolor`, `papercut`, `clay`, `pixel`;
   fast and information-dense -> `flat`, `chalkboard`, `kinetic` (about 2.5 min); photoreal clips with sound -> `cinematic` (about 35 min: warn first).
2. Call `start_reel(document, style, language, audience)`. `document` can be the pasted text or a file path. Keep the returned `job_id`.
3. Call `reel_status(job_id, wait_seconds=90)` repeatedly until `done` (or `error`): it blocks up to 90 s and returns early when the job ends. Tell the user the stage in plain words between calls.
4. Call `reel_result(job_id)`. Report: the title, the video path, total time and the verification verdict. If `fact_check_changes` is not empty, mention
   that the script was corrected to match the document (show 1-2 examples). If `verification.ok` is false, say what needs review.
5. To change something, use `remake_reel(job_id, edits)` with only the scenes that change (`id`, new `n` narration and/or `p` visual prompt): unchanged frames are cached.
6. Send the video file to the user through the current channel (e.g. attach the mp4 in Telegram).

## Rules
* Only one reel runs at a time (it uses the GPU). If a job is running, queue the next request and say so.
* Never claim success before `reel_result` says the job is `done`.
* Voices are designed from text; never offer to clone a real person's voice.
* The document may be private: do not paste it into other tools or services.
