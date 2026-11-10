import os, re, time
import requests
from openai import OpenAI

PROVIDERS = {
    "groq": {"base": "https://api.groq.com/openai/v1", "key": "GROQ_API_KEY"},
    "openrouter": {"base": "https://openrouter.ai/api/v1", "key": "OPENROUTER_API_KEY"},
}

# Order of preference on Groq (substring match against the live model list).
GROQ_PREFER = ["gpt-oss-120b", "llama-3.3-70b", "qwen3-32b", "llama-4", "kimi", "gpt-oss-20b"]
GROQ_SKIP = ("whisper", "guard", "tts", "playai", "orpheus", "distil",
             "safeguard", "compound", "8b")

_cache = {}


def _size(model_id):
    """Rough parameter count in billions, from the model name. 0 = skip."""
    m = model_id.lower()
    if any(s in m for s in ("lfm", "vision", "embed", "moderation", "image", "audio")):
        return 0
    nums = [int(x) for x in re.findall(r"(\d+)b", m)]
    if nums:
        return max(nums)
    known_big = ("deepseek", "kimi", "glm", "qwen", "gpt-oss", "minimax")
    return 30 if any(s in m for s in known_big) else 0


def _list(provider):
    if provider in _cache:
        return _cache[provider]
    cfg = PROVIDERS[provider]
    key = os.getenv(cfg["key"])
    ids = []
    if key:
        try:
            r = requests.get(cfg["base"] + "/models",
                             headers={"Authorization": f"Bearer {key}"}, timeout=30)
            r.raise_for_status()
            data = r.json()["data"]
            if provider == "groq":
                ids = [m["id"] for m in data
                       if not any(s in m["id"].lower() for s in GROQ_SKIP)]
                ids.sort(key=lambda i: next(
                    (n for n, p in enumerate(GROQ_PREFER) if p in i.lower()), 99))
            else:
                free = [m["id"] for m in data
                        if str(m.get("pricing", {}).get("prompt")) == "0"
                        and str(m.get("pricing", {}).get("completion")) == "0"]
                ids = sorted([i for i in free if _size(i) >= 20], key=_size, reverse=True)
        except Exception as e:
            print(f"[{provider}] could not list models: {e}")
    else:
        print(f"[{provider}] {cfg['key']} not set, skipping")
    forced = os.getenv("GROQ_MODEL" if provider == "groq" else "OR_MODEL")
    ids = ([forced] if forced else []) + [i for i in ids if i != forced]
    _cache[provider] = ids[:4]
    return _cache[provider]


def candidates():
    return [(p, m) for p in ("groq", "openrouter") for m in _list(p)]


def chat(messages, temperature=0.8, max_tokens=6000, offset=0):
    """offset rotates the model list, so the fact-checker can use a different model."""
    cands = candidates()
    if not cands:
        raise RuntimeError("No usable models. Check API keys, then run: python src/list_models.py")
    cands = cands[offset:] + cands[:offset]
    last = None
    for provider, model in cands:
        cfg = PROVIDERS[provider]
        client = OpenAI(base_url=cfg["base"], api_key=os.getenv(cfg["key"]), timeout=180)
        for attempt in range(2):
            try:
                r = client.chat.completions.create(
                    model=model, messages=messages,
                    temperature=temperature, max_tokens=max_tokens)
                text = r.choices[0].message.content or ""
                text = re.sub(r"<think>.*?</think>", "", text, flags=re.S).strip()
                if not text:
                    raise ValueError(f"empty response (finish={r.choices[0].finish_reason})")
                print(f"  (model: {provider}:{model})")
                return text
            except Exception as e:
                last = e
                msg = str(e)
                print(f"[{provider}:{model}] attempt {attempt + 1} failed: {msg[:160]}")
                if "429" in msg and attempt == 0:
                    time.sleep(20)       # rate limit: wait once, retry
                    continue
                break                    # anything else: try the next model
    raise RuntimeError(f"All models failed: {last}")