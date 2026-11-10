import json
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
CACHE_DIR = BASE_DIR / ".cache"
CORPUS_FILE = BASE_DIR / "corpus" / "verified_texts.json"


def _load_gita_verse(ch: int, v: int) -> dict:
    verses_path = CACHE_DIR / "verse.json"
    trans_path = CACHE_DIR / "translation.json"

    verses = json.loads(verses_path.read_text(encoding="utf-8"))
    translations = json.loads(trans_path.read_text(encoding="utf-8"))

    # Match chapter_number and verse_number to get the global 'id' (e.g., 94 for 2.47)
    verse_obj = next(
        (
            item for item in verses
            if int(item.get("chapter_number", 0)) == int(ch)
            and int(item.get("verse_number", 0)) == int(v)
        ),
        None,
    )
    if not verse_obj:
        raise ValueError(f"Verse not found in verse.json for Gita {ch}.{v}")

    global_id = verse_obj["id"]

    # Match verse_id == global_id with case-insensitive language check
    eng_translations = [
        t for t in translations
        if t.get("verse_id") == global_id
        and str(t.get("lang", "")).strip().lower() == "english"
        and str(t.get("description", "")).strip()
    ]

    if not eng_translations:
        raise ValueError(f"No English translation for Gita {ch}.{v}")

    # Prefer Swami Sivananda or Swami Gambirananda if present
    preferred = next(
        (
            t for t in eng_translations
            if "sivananda" in str(t.get("authorName", "")).lower()
            or "gambirananda" in str(t.get("authorName", "")).lower()
        ),
        eng_translations[0],
    )

    return {
        "source_type": "Bhagavad Gita",
        "reference": f"Bhagavad Gita {ch}.{v}",
        "original_text": verse_obj.get("text", "").strip(),
        "transliteration": verse_obj.get("transliteration", "").strip(),
        "word_meanings": verse_obj.get("word_meanings", "").strip(),
        "translation": preferred["description"].strip(),
        "translator": preferred.get("authorName", "Swami Sivananda").strip(),
    }


def _load_corpus_entry(entry_id: str) -> dict:
    if not CORPUS_FILE.exists():
        raise FileNotFoundError(f"Verified corpus file missing at {CORPUS_FILE}")
    corpus = json.loads(CORPUS_FILE.read_text(encoding="utf-8"))
    if entry_id not in corpus:
        raise ValueError(f"Entry '{entry_id}' not found in {CORPUS_FILE}")
    return corpus[entry_id]


def load_source(topic: dict) -> dict:
    """
    Loads verified original text for either:
    1. A single-source topic (compatible with your existing test command), or
    2. A multi-segment daily episode (Bhajan + Itihasa/Purana/Veda + Gita).
    """
    # Multi-segment episode format
    if "segments" in topic:
        loaded_segments = {}
        for seg_key, seg_cfg in topic["segments"].items():
            loaded_segments[seg_key] = load_source(seg_cfg)
        return loaded_segments

    # Single-source Gita lookup (supports 'chapter'/'verse', 'ch'/'v', or 'ref': '2.47')
    source_kind = str(topic.get("source", topic.get("type", "gita"))).lower()
    if "gita" in source_kind or "chapter" in topic or "ch" in topic:
        if "ref" in topic and "." in str(topic["ref"]):
            ch, v = map(int, str(topic["ref"]).split("."))
        else:
            ch = int(topic.get("chapter", topic.get("ch", 2)))
            v = int(topic.get("verse", topic.get("v", 47)))
        return _load_gita_verse(ch, v)

    # Bhajan / Ramayana / Mahabharata / Rig Veda / Purana lookup from verified_texts.json
    corpus_id = topic.get("corpus_id") or topic.get("id")
    if corpus_id:
        return _load_corpus_entry(corpus_id)

    raise ValueError(f"Cannot resolve source for topic: {topic}")