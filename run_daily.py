import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
import yaml

sys.path.insert(0, "src")
from sources import load_source
from write import generate
from audio import build_episode_mp3
from rss import update_apple_podcast_rss

BASE_DIR = Path(__file__).resolve().parent
DOCS_DIR = BASE_DIR / "docs"
EPISODES_JSON = DOCS_DIR / "episodes.json"
BASE_URL = os.environ.get("PODCAST_BASE_URL", "https://YOUR_GITHUB_USERNAME.github.io/philosophy-podcast")


def main():
    topics = yaml.safe_load((BASE_DIR / "topics.yaml").read_text(encoding="utf-8"))
    published = json.loads(EPISODES_JSON.read_text(encoding="utf-8")) if EPISODES_JSON.exists() else []
    published_ids = {ep["id"] for ep in published}

    # Pick the next unpublished topic
    next_topic = next((t for t in topics if t["id"] not in published_ids), None)
    if not next_topic:
        print("All topics in topics.yaml have been published!")
        return

    print(f"Generating script for: {next_topic['title']}...")
    source_data = load_source(next_topic)
    script_sections = generate(next_topic, source_data, target_words=2800)

    filename = f"{next_topic['id']}.mp3"
    mp3_path = DOCS_DIR / "episodes" / filename
    print(f"Synthesizing audio to {mp3_path}...")
    audio_meta = build_episode_mp3(script_sections, mp3_path)

    published.append({
        "id": next_topic["id"],
        "title": next_topic["title"],
        "description": f"Core Question: {next_topic.get('core_question', '')}",
        "filename": filename,
        "file_size_bytes": audio_meta["file_size_bytes"],
        "duration_seconds": audio_meta["duration_seconds"],
        "pub_date_iso": datetime.now(timezone.utc).isoformat(),
    })

    DOCS_DIR.mkdir(parents=True, exist_ok=True)
    EPISODES_JSON.write_text(json.dumps(published, indent=2, ensure_ascii=False), encoding="utf-8")
    feed_path = update_apple_podcast_rss(DOCS_DIR, BASE_URL, published)
    print(f"Done! RSS feed updated at: {feed_path}")


if __name__ == "__main__":
    main()