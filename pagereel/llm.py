"""OpenAI-compatible LLM client (text + vision). Any local server works: llama.cpp, vLLM, LM Studio..."""
import base64, json, re
import httpx
from . import config

def _chat(messages, max_tokens, temperature, timeout=1500):
    r = httpx.post(config.LLM_BASE_URL.rstrip("/") + "/chat/completions", timeout=timeout,
                   headers={"Authorization": f"Bearer {config.LLM_API_KEY}"},
                   json={"model": config.LLM_MODEL, "messages": messages, "max_tokens": max_tokens, "temperature": temperature})
    r.raise_for_status(); return r.json()["choices"][0]["message"]["content"]

def text(system, user, max_tokens=12000, temperature=0.7):
    return _chat([{"role": "system", "content": system}, {"role": "user", "content": user}], max_tokens, temperature)

def _json(out):
    m = re.search(r"\{.*\}", out, re.S)
    return json.loads(m.group(0))

def json_call(system, user, check=lambda j: True, tries=3, **kw):
    """Ask for a JSON object; retry until it parses and passes `check`."""
    last = None
    for _ in range(tries):
        try:
            j = _json(text(system, user, **kw)); assert check(j); return j
        except Exception as e: last = e
    raise RuntimeError(f"LLM did not return valid JSON: {last!r}")

def vision(image_path, prompt, max_tokens=700):
    b = base64.b64encode(open(image_path, "rb").read()).decode()
    mime = "image/jpeg" if str(image_path).lower().endswith((".jpg", ".jpeg")) else "image/png"
    out = _chat([{"role": "user", "content": [{"type": "image_url", "image_url": {"url": f"data:{mime};base64,{b}"}},
                                              {"type": "text", "text": prompt}]}], max_tokens, 0, timeout=300)
    try: return _json(out)
    except Exception: return {"raw": out}
