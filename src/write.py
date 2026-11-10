import os
from google import genai
from google.genai.errors import APIError
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

SYSTEM_PROMPT = """You are a master storyteller and teacher of Indian philosophy.
Your voice blends:
1. Natural, earthy, relatable storytelling and psychological sharpness (like Sadhguru's parables and Sri Ramakrishna's everyday metaphors).
2. Rigorous Sanskrit word-root (pada-artha) unpacking and textual fidelity (like Bannanje Govindacharya, Dushyanth Sridhar, Vidwan Jagadeesha Sharma, and Ami Ganatra).
3. Piercing Vedantic inquiry and practical real-world application (like Swami Sarvapriyananda, Swami Vivekananda, Adi Shankara, and Chaitanya Charan).

STRICT RULES:
- Use ONLY the verified original Sanskrit/Awadhi text and translation provided in the prompt. Never invent shlokas.
- Never fabricate fake quotes claiming a modern speaker said something they didn't.
- Write for spoken audio: warm, conversational Indian English, natural pauses, vivid narrative scenes, zero markdown bullet lists or robotic headings.
- Always show how to implement the insight in real-world modern life (career pressure, family friction, ego, focus) and end with a question that stays in the listener's mind all evening."""


@retry(
    retry=retry_if_exception_type((APIError, Exception)),
    stop=stop_after_attempt(4),
    wait=wait_exponential(multiplier=2, min=4, max=30),
    reraise=True,
)
def _generate_section(client: genai.Client, model: str, prompt: str) -> str:
    response = client.models.generate_content(
        model=model,
        contents=f"{SYSTEM_PROMPT}\n\nTask:\n{prompt}",
    )
    return (response.text or "").strip()


def generate(topic: dict, source: dict, target_words: int = 2800) -> dict:
    """
    Generates a multi-section spoken podcast script dictionary {section_name: text}.
    """
    client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))
    model = os.environ.get("LLM_MODEL", "gemini-1.5-flash")

    if "original_text" in source:
        per_sec = max(450, target_words // 3)
        sections_spec = {
            "part_1_story_and_verse": (
                f"Write Part 1 (~{per_sec} words) of an evening podcast on {source['reference']}.\n"
                f"Original Verse:\n{source['original_text']}\n"
                f"Transliteration:\n{source['transliteration']}\n"
                f"Word Meanings:\n{source['word_meanings']}\n"
                f"Verified Translation ({source['translator']}):\n{source['translation']}\n\n"
                "Open with a gripping real-life story, recite the transliterated verse clearly, "
                "and unpack each Sanskrit word root."
            ),
            "part_2_philosophical_depth": (
                f"Write Part 2 (~{per_sec} words) continuing the exploration of {source['reference']}.\n"
                "Tell an authentic story from the Mahabharata/Gita context and unpack the deeper "
                "psychological trap of attachment to results vs. mastery of action."
            ),
            "part_3_real_world_implementation": (
                f"Write Part 3 (~{per_sec} words) concluding the episode on {source['reference']}.\n"
                "Give concrete real-world implementation for tomorrow's work and relationships, "
                "and close with a piercing contemplation question that wakes up the inner mind."
            ),
        }
    else:
        per_sec = max(850, target_words // 3)
        b_src = source["bhajan_breakdown"]
        i_src = source["itihasa_story"]
        g_src = source["gita_awakening"]

        sections_spec = {
            "segment_1_bhajan": (
                f"Write Segment 1 (~{per_sec} words): Bhajan & Stotra Wisdom.\n"
                f"Source: {b_src['reference']}\n"
                f"Original 6 Lines:\n{b_src['original_text']}\n"
                f"Transliteration:\n{b_src['transliteration']}\n"
                f"Word Meanings:\n{b_src['word_meanings']}\n"
                f"Translation:\n{b_src['translation']}\n"
                f"Focus: {topic['segments']['bhajan_breakdown']['focus']}\n\n"
                "Quote the transliterated lines naturally, explain the exact meaning of each line, "
                "tell a vivid story illustrating 'man-mukuru' (the mirror of the mind), and share "
                "how to apply these 6 lines in real life tonight."
            ),
            "segment_2_itihasa": (
                f"Write Segment 2 (~{per_sec} words): Itihasa & Purana Story in the Real World.\n"
                f"Source: {i_src['reference']}\n"
                f"Original Text:\n{i_src['original_text']}\n"
                f"Transliteration:\n{i_src['transliteration']}\n"
                f"Word Meanings:\n{i_src['word_meanings']}\n"
                f"Translation:\n{i_src['translation']}\n"
                f"Focus: {topic['segments']['itihasa_story']['focus']}\n\n"
                "Narrate the Mahabharata story with immersive detail, quote the Sanskrit shloka, "
                "and connect it directly to how we live our modern lives."
            ),
            "segment_3_gita_awakening": (
                f"Write Segment 3 (~{per_sec} words): Bhagavad Gita Inner Awakening.\n"
                f"Source: {g_src['reference']}\n"
                f"Original Text:\n{g_src['original_text']}\n"
                f"Transliteration:\n{g_src['transliteration']}\n"
                f"Word Meanings:\n{g_src['word_meanings']}\n"
                f"Translation:\n{g_src['translation']}\n"
                f"Focus: {topic['segments']['gita_awakening']['focus']}\n"
                f"Closing Contemplation Question: {topic.get('core_question', '')}\n\n"
                "Unpack the Sanskrit terms deeply, contrast how an ordinary mind vs. an awakened mind "
                "acts in the real world, and end with the Closing Contemplation Question."
            ),
        }

    output = {}
    for key, prompt in sections_spec.items():
        print(f"Generating [{key}] using model {model}...")
        output[key] = _generate_section(client, model, prompt)
    return output