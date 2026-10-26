"""Vision QA loop: a vision LLM inspects every generated frame; bad ones are regenerated with a simpler prompt."""
from concurrent.futures import ThreadPoolExecutor
from . import llm

QA_PROMPT = ('Review this image for a children\'s educational video. Reply ONLY with JSON: {"text_visible": bool (legible or garbled letters, words, numbers), '
             '"deformed": bool (deformed hands, faces or bodies, extra or fused limbs, deformed animals/objects), "disturbing": bool (fear, harm, violence), '
             '"n_people": int, "style_match": bool (true only if it clearly looks like: %s, and NOT a plain photo or generic 3D render), "description": "one sentence"}')

def inspect(path, style_name, no_people=False):
    r = llm.vision(path, QA_PROMPT % style_name)
    bad = r.get("text_visible") or r.get("deformed") or r.get("disturbing") or r.get("style_match") is False or (no_people and r.get("n_people", 0) > 0)
    return bool(bad), r

def inspect_all(paths, style_name, no_people=False):
    with ThreadPoolExecutor(4) as ex: return list(ex.map(lambda p: inspect(p, style_name, no_people), paths))

def simplify(prompt, level=1):
    """Rewrite a prompt dropping what usually fails (writing, hands, screens; at level 2 also animals/vehicles/people)."""
    extra = " Also remove animals, vehicles and people: keep only landscape, objects, plants, water, textures and light." if level >= 2 else ""
    return llm.text("You rewrite image prompts. Remove signs, posters, blackboards, papers, postcards, maps or drawings with writing, screens, open books and close-up hands; "
                    "replace them with things without writing (plants, plain objects, landscape, large simple shapes)." + extra + " Keep place, intent and mood. Return ONLY the prompt, in English, no quotes.",
                    prompt, max_tokens=800, temperature=0.4).strip()

def simplify_motion(motion, new_scene):
    return llm.text("You rewrite short image-to-video motion prompts in English so they match a new scene. Allowed: slow camera moves, wind, light shifts, steam, water, falling grains, leaves. "
                    "Forbidden: writing, hands, people, animals moving, vehicles moving. 1-2 sentences ending with 'no people'. Return ONLY the prompt.",
                    f"New scene: {new_scene}\nOld motion prompt: {motion}", max_tokens=300, temperature=0.4).strip()
