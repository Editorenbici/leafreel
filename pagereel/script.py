"""Document text -> scene spec (narration + visuals) for a style, then an automatic fact check against the source."""
from . import llm

BASE = """You are a scriptwriter of short educational videos for an audience of: {audience}. Language of narration and on-screen text: {language}. Friendly tone, nothing scary or harmful.
You receive the text of a document. Reply with ONE valid JSON object only (no markdown).
Common keys: "title" (short, catchy, max 8 words), "summary" (one sentence), "key_ideas" (3 ideas faithful to the document).
Content rules: never invent facts, figures or dates that are not in the document; no brands, party politics or religion; concrete examples; the last line connects to a question or invitation for the viewer.
Narration lines are short (about 10 words each), one per scene, about 110-125 words in total."""

MODES = {
"image": """Mode STORY ILLUSTRATED. Add "character" (a first name and a FIXED visual description of one protagonist suitable for the audience: hair, clothes and details that never change, one sentence) and "scenes": 12 objects {{"n": narration line, "p": visual prompt}}.
Lines: 1 introduces the protagonist; 2-10 develop the key ideas with concrete examples; 11 connects to the viewer's own project; 12 closes with a question or invitation.
"p": written in English; start with {{character}} (literal) when the protagonist appears; concrete place, action and light; describe only what IS visible (no negations, no written text). Only the adults that are needed, with different clothes. Visual style of the video: {image_style}.""",
"motion": """Mode MOTION GRAPHICS (animated graphics drawn by code; no characters or photos). Add "scenes": 10 objects {{"n": narration line, "layout": one of [title, cards, steps, compare, stat, quote, cycle, list], "d": layout data, "key": [1-3 EXACT words from the line], "emoji": one emoji that represents the line}}.
Layouts and their "d":
- title: {{"title","subtitle","emoji"}} (scene 1 only)
- cards: {{"heading","items":[{{"emoji","title","text"}}] (2 to 4)}}
- steps: {{"heading","items":[{{"emoji","title"}}] (exactly 3)}}
- compare: {{"heading","left":{{"emoji","title","text"}},"right":{{"emoji","title","text"}}}}
- stat: {{"emoji","big" (one short word or figure),"text"}}
- quote: {{"emoji","text" (a question or short message)}}
- cycle: {{"heading","items":[{{"emoji","title"}}] (3 or 4)}}
- list: {{"heading","items":[short text] (3 to 4)}}
One emoji character per emoji field. On-screen text very short (max 5 words per title, 9 per text). Vary the layouts; the last scene is a "quote". Speak directly to the viewer.""",
"cinematic": """Mode CINEMATIC DOCUMENTARY (video clips generated from still images; NO people or faces: landscapes, objects, places, animals at rest). Add "scenes": 10 objects {{"n": narration line, "p": prompt of the first frame (English; concrete landscape/object/place, light and composition, no negations, avoid maps, signs, books, postcards or anything with writing), "v": motion prompt in English (slow camera move and natural movement such as wind, light, steam, water; ambient sound; end with 'no people')}}.
Sober, poetic narration that links each image to the document's idea.""",
}

def _mode(style): return {"image": "image", "motion": "motion", "cinematic": "cinematic"}[style["engine"]]

def generate(doc_text, style, language="English", audience="curious learners aged 8-12", max_chars=26000):
    mode = _mode(style); n = {"image": 12, "motion": 10, "cinematic": 10}[mode]
    system = BASE.format(audience=audience, language=language) + "\n" + MODES[mode].format(image_style=style.get("image_style", ""))
    spec = llm.json_call(system, doc_text[:max_chars],
                         lambda j: len(j["scenes"]) == n and all(s.get("n") for s in j["scenes"]) and j.get("title"))
    for i, s in enumerate(spec["scenes"]): s["id"] = f"{i+1:02d}"
    spec["mode"] = mode; spec["style"] = style["id"]; spec["language"] = language
    spec["fact_check"] = fact_check(spec, doc_text)
    return spec

def fact_check(spec, doc_text):
    """Compare every narration line with the source; replace lines with unsupported concrete claims."""
    lines = [s["n"] for s in spec["scenes"]]
    chk = llm.json_call(
        "You are an accuracy reviewer comparing lines of a children's video script with the source document. Reply with ONLY JSON: "
        '{"problems":[{"line": number (1..N), "reason": "which concrete claim is not supported or is wrong", "fix": "corrected line, equally short, supported by the document, same language"}]}. '
        'Flag only concrete claims (figures, names, dates, assertions) that are absent from or contradict the document; general pedagogical lines are fine. If all is supported return {"problems":[]}.',
        "SOURCE DOCUMENT:\n" + doc_text[:20000] + "\n\nLINES:\n" + "\n".join(f"{i+1}. {l}" for i, l in enumerate(lines)),
        lambda j: isinstance(j.get("problems"), list), temperature=0)
    changes = []
    for p in chk["problems"]:
        try:
            i = int(p["line"]) - 1; changes.append({"line": i + 1, "before": spec["scenes"][i]["n"], "after": p["fix"], "reason": p["reason"]}); spec["scenes"][i]["n"] = p["fix"]
        except Exception: pass
    return changes
