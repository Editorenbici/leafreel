# Use PageReel from an agent

PageReel ships an **MCP server** (stdio), so any MCP-capable agent can make reels: Hermes Agent, OpenClaw, pi, Claude Code, Cursor, … Tested with Hermes Agent.

Tools: `list_styles`, `start_reel`, `reel_status` (long-poll with `wait_seconds`), `reel_result`, `remake_reel` (asynchronous: a reel takes 2–6 minutes, `cinematic` ~35).

## Install

```bash
pip install -e '.[agents]'        # adds the `mcp` package and the `pagereel-mcp` command
```

## Hermes Agent

Add to `~/.hermes/config.yaml` (MCP support ships with Hermes):

```yaml
mcp_servers:
  pagereel:
    command: /path/to/pagereel/.venv/bin/pagereel-mcp
    env:
      COMFY_BASE_URL: "http://127.0.0.1:8189"        # comfy-api-proxy in front of ComfyUI
      LLM_BASE_URL: "http://127.0.0.1:8090/v1"       # your vision LLM node
      LLM_MODEL: "Qwen3.8-Flash-Next"
```

Optionally copy the skill so the agent knows *when* and *how* to use it:

```bash
mkdir -p ~/.hermes/skills/creative && cp -r integrations/hermes/pagereel ~/.hermes/skills/creative/
```

Then, in the TUI, Telegram or Discord: *"Make a 1-minute pixel-art video from this PDF"* (attach the file). Hermes calls `start_reel`, reports progress and sends back the mp4.

## Other agents

Same stdio server, each client's own syntax:

```json
{ "mcpServers": { "pagereel": { "command": "/path/to/pagereel/.venv/bin/pagereel-mcp", "env": { "COMFY_BASE_URL": "http://127.0.0.1:8189" } } } }
```

(Claude Code: `claude mcp add pagereel -- /path/to/pagereel/.venv/bin/pagereel-mcp`; the JSON above also works in Cursor-style configs.)
Agents that cannot use MCP can call the CLI (`pagereel make …`) or the HTTP API of `pagereel serve` (`POST /api/jobs`, `GET /api/jobs/{id}`).

## Why an agent front-end matters

The web UI is for people at a desk; the agent front-end lets a teacher send a PDF from their phone and get the reel back in the same chat,
with the agent explaining what was fact-corrected. The generation still runs on your own two nodes with open weights.
