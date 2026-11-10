import re
from llm import chat

SYSTEM = """You write a daily audio show on Indian philosophy for one thoughtful adult listener.
Goal: leave one idea lodged in his mind for the rest of the day.
Voice: warm, plain spoken English, short sentences, a wise storyteller talking across a table.
Output only spoken words: no headings, labels, markdown, bullets or stage directions.
Never write Devanagari. Never quote or attribute sayings to any named teacher.
Avoid cliches: no rain, thunder, storms, flickering lights, fluorescent lights, metallic tastes,
"weight on his shoulders", "knot in his stomach", "let's dive in", "in conclusion".
Prefer fresh, specific, unexpected details over atmosphere."""

SECTIONS = {"story": 0.46, "meaning": 0.18, "real_world": 0.30, "closing_question": 0.06}

BANNED = re.compile(r"\b(fluorescent|thunder\w*|flicker\w*|tapestry|metallic)\b|dive in|in conclusion", re.I)


def instruction(name, topic, src):
    if name == "story":
        if src.get("story_material"):
            return ("Write the opening STORY as a faithful retelling of the scene in STORY MATERIAL. "
                    "Use the names given there. Do not change events and do not invent dialogue beyond "
                    "what the material says; you may add sensory and emotional detail. End at the moment "
                    "of deepest stuckness. Do NOT explain the verse and do NOT state the lesson.")
        if topic.get("story_seed"):
            return ("Write the opening STORY by expanding the STORY SEED. Keep every event of the seed; "
                    "add nothing that changes the plot. Retell it vividly, with small sensory details. "
                    "End at the moment of deepest stuckness. Do NOT state the lesson.")
        return ("Write the opening STORY as a clearly framed modern parable (begin with a phrase like "
                "'Picture a man...'). Use ordinary names, never names from scripture. Begin mid-scene. "
                "Choose an unexpected setting, not an office. One or two small, specific, surprising "
                "details. No character may explain the lesson or say the idea of the verse out loud. "
                "End at the moment of deepest stuckness. Never present it as scripture.")
    if name == "meaning":
        return ("Write the MEANING for the listener, addressed as 'you'. Do not address any story "
                "character. First explain the verse in about six plain spoken lines, covering EVERY "
                "clause of it, including the parts that guard against misreading. Then, in a few "
                "sentences, show how this idea answers the stuck moment in the story. Use at most two "
                "Sanskrit words, each explained.")
    if name == "real_world":
        return ("Write the REAL WORLD part: one concrete modern scenario in detail, then one specific "
                "thing the listener can do today. The advice must honour the WHOLE verse and must never "
                "suggest ignoring consequences, avoiding facts or doing less work.")
    return ("Write ONE closing question only: under 35 words, no setup, no preamble. It must be "
            "concrete and personal to today, and slightly uncomfortable in a good way.")


def context(topic, src):
    parts = [f"Topic: {topic['title']}", f"Source: {src['citation']}",
             f"Verse (context only, never quote it): {src['devanagari']}",
             f"Transliteration: {src['transliteration']}",
             "Reference meanings (stay within these):\n" + "\n".join(src["reference_meanings"]),
             f"Angle hint: {topic.get('angle', '')}"]
    if src.get("story_material"):
        parts.append("STORY MATERIAL (from the same text):\n" + src["story_material"])
    if topic.get("story_seed"):
        parts.append("STORY SEED:\n" + topic["story_seed"])
    return "\n".join(parts)


def clean(t):
    t = re.sub(r"[*#`>]+", "", t)
    t = re.sub(r"(?im)^\s*(story|meaning|real world|real_world|closing question)\s*:\s*", "", t)
    return t.strip()


def check(name, text, topic, src, target):
    p = []
    if re.search(r"[\u0900-\u097F]", text):
        p.append("contains Devanagari; remove it")
    allowed = set(re.findall(r"\d+", src["citation"]))
    for m in re.findall(r"(?i)(?:chapter|verse|adhyaya|shloka)\s+(\d+)", text):
        if m not in allowed:
            p.append(f"mentions number {m}, which is not part of the citation")
    if BANNED.search(text):
        p.append("uses a banned cliche word; rewrite those parts with fresh details")
    n = len(text.split())
    if name == "closing_question":
        if text.count("?") != 1 or n > 45:
            p.append("must be exactly one question, under 35 words, with no setup")
    elif n < target * 0.7:
        p.append(f"too short: {n} words, aim for about {target}")
    if name == "story" and not (src.get("story_material") or topic.get("story_seed")):
        if re.search(r"\b(Arjun\w*|Krishna|Rama|Sita|Hanuman|Bhima|Karna)\b", text):
            p.append("do not use scripture character names in a modern parable")
    return p


def write_section(name, topic, src, words, so_far, avoid):
    target = int(words * SECTIONS[name])
    problems, draft = [], ""
    for attempt in range(3):
        parts = [context(topic, src)]
        if so_far:
            parts.append("Script so far:\n" + so_far)
        parts += [instruction(name, topic, src), f"Aim for about {target} words."]
        if avoid:
            parts.append("A fact-checker rejected an earlier version; avoid these problems:\n- "
                         + "\n- ".join(avoid))
        if problems:
            parts.append("Your previous draft had problems: " + "; ".join(problems))
            if draft and any("too short" in x for x in problems):
                parts.append("Previous draft. Expand it with more scene, specifics and "
                             "dialogue, not repetition:\n" + draft)
        draft = clean(chat([{"role": "system", "content": SYSTEM},
                            {"role": "user", "content": "\n\n".join(parts)}]))
        problems = check(name, draft, topic, src, target)
        if not problems:
            return draft
        print(f"[{topic['id']}/{name}] attempt {attempt + 1} rejected: {problems}")
    if name != "closing_question" and all("too short" in x for x in problems) \
            and len(draft.split()) >= target * 0.5:
        print(f"[{topic['id']}/{name}] accepting shorter draft")
        return draft
    raise RuntimeError(f"Could not write {name} for {topic['id']}: {problems}")


def audit(src, script):
    prompt = f"""You are a strict reviewer of Indian philosophy audio scripts.
Source: {src['citation']}
Verse: {src['devanagari']}
Reference meanings:
{chr(10).join(src['reference_meanings'])}

STORY: {script['story']}
MEANING: {script['meaning']}
REAL WORLD: {script['real_world']}
CLOSING QUESTION: {script['closing_question']}

Check ALL of these and FAIL if any is violated:
1. COMPLETENESS: the meaning covers every clause of the verse, including warnings against misreading
   (for example, a clause against inaction or against the opposite extreme).
2. FAITHFULNESS: the meaning does not contradict or go beyond the reference meanings.
3. MISAPPLICATION: the real-world advice follows the whole verse and does not suggest ignoring
   facts, consequences, or effort.
4. STORY: no character states the lesson; any scripture or epic episode matches the source and has
   nothing invented; an invented parable is clearly framed as one.
5. No invented quotes, names or details presented as fact.
Reply with exactly one line starting with PASS or FAIL. If FAIL, write FAIL: then each problem,
separated by semicolons, phrased as an instruction for fixing it."""
    out = chat([{"role": "user", "content": prompt}], temperature=0.1, max_tokens=1000, offset=2)
    found = re.findall(r"(?im)^\s*(PASS|FAIL)\b[:\s]*(.*)$", out)
    if not found:
        return ["audit reply was unparseable"]
    verdict, rest = found[-1]
    if verdict.upper() == "PASS":
        return []
    return [x.strip() for x in rest.split(";") if x.strip()] or ["audit failed"]


def generate(topic, src, words):
    avoid = []
    for rnd in range(2):
        script, so_far = {}, ""
        for name in SECTIONS:
            script[name] = write_section(name, topic, src, words, so_far, avoid)
            so_far += f"\n[{name.upper()}]\n{script[name]}\n"
        problems = audit(src, script)
        if not problems:
            return script
        print(f"[{topic['id']}] audit round {rnd + 1} failed: {problems}")
        avoid = problems
    raise RuntimeError(f"No verified script for {topic['id']}: {avoid}")