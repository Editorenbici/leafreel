"""Runtime configuration, all from environment variables (see README)."""
import os
from pathlib import Path

# ComfyUI through the Comfy SDK. Point COMFY_BASE_URL at a local `comfy-api-proxy` (self-hosted ComfyUI),
# a Comfy API deployment (*.run.comfy.app) or leave unset for Comfy Cloud.
COMFY_BASE_URL = os.environ.get("COMFY_BASE_URL", "http://127.0.0.1:8189")
COMFY_API_KEY = os.environ.get("COMFY_API_KEY", "local")

# Any OpenAI-compatible server with a vision-capable model (llama.cpp, vLLM, LM Studio, tensorfold...).
LLM_BASE_URL = os.environ.get("LLM_BASE_URL", "http://127.0.0.1:8090/v1")
LLM_MODEL = os.environ.get("LLM_MODEL", "Qwen3.8-Flash-Next")
LLM_API_KEY = os.environ.get("LLM_API_KEY", "none")

# Narration backend: "qwen3tts" (Qwen3-TTS VoiceDesign, GPU) or "http" (any OpenAI-compatible /v1/audio/speech server).
TTS_BACKEND = os.environ.get("TTS_BACKEND", "qwen3tts")
TTS_HTTP_URL = os.environ.get("TTS_HTTP_URL", "http://127.0.0.1:8880/v1/audio/speech")
TTS_HTTP_MODEL = os.environ.get("TTS_HTTP_MODEL", "kokoro")
TTS_HTTP_VOICE = os.environ.get("TTS_HTTP_VOICE", "af_heart")
# Optional: run the Qwen3-TTS helper on another machine over ssh (e.g. the GPU box): "user@host"
TTS_SSH = os.environ.get("TTS_SSH", "")
TTS_PYTHON = os.environ.get("TTS_PYTHON", "python3")

DATA_DIR = Path(os.environ.get("PAGEREEL_DATA", Path.home() / ".pagereel")).expanduser()
CHROMIUM = os.environ.get("CHROMIUM_PATH", "")  # for the code-rendered (motion graphics) styles
