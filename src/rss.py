from datetime import datetime, timezone
from email.utils import format_datetime
from pathlib import Path
from xml.sax.saxutils import escape


def update_apple_podcast_rss(
    docs_dir: Path,
    base_url: str,
    episodes_meta: list[dict],
    podcast_title: str = "Indian Philosophy in the Real World",
    podcast_author: str = "Daily Dharma AI Agent",
    podcast_desc: str = "Daily 6 PM reflections on Bhajans, Bhagavad Gita, Upanishads, Ramayana, and Mahabharata in story format.",
) -> Path:
    docs_dir.mkdir(parents=True, exist_ok=True)
    items_xml = []

    for ep in sorted(episodes_meta, key=lambda x: x["pub_date_iso"], reverse=True):
        dt = datetime.fromisoformat(ep["pub_date_iso"]).astimezone(timezone.utc)
        rfc2822_date = format_datetime(dt)
        mp3_url = f"{base_url.rstrip('/')}/episodes/{ep['filename']}"

        items_xml.append(f"""    <item>
      <title>{escape(ep['title'])}</title>
      <description>{escape(ep['description'])}</description>
      <pubDate>{rfc2822_date}</pubDate>
      <enclosure url="{mp3_url}" length="{ep['file_size_bytes']}" type="audio/mpeg"/>
      <guid isPermaLink="false">{escape(ep['id'])}</guid>
      <itunes:duration>{ep['duration_seconds']}</itunes:duration>
      <itunes:explicit>false</itunes:explicit>
    </item>""")

    rss_content = f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0"
     xmlns:itunes="http://www.itunes.com/dtds/podcast-1.0.dtd"
     xmlns:content="http://purl.org/rss/1.0/modules/content/">
  <channel>
    <title>{escape(podcast_title)}</title>
    <link>{base_url}</link>
    <language>en-in</language>
    <itunes:author>{escape(podcast_author)}</itunes:author>
    <description>{escape(podcast_desc)}</description>
    <itunes:image href="{base_url.rstrip('/')}/cover.jpg"/>
    <itunes:explicit>false</itunes:explicit>
    <itunes:category text="Religion &amp; Spirituality">
      <itunes:category text="Hinduism"/>
    </itunes:category>
{chr(10).join(items_xml)}
  </channel>
</rss>
"""
    feed_path = docs_dir / "feed.xml"
    feed_path.write_text(rss_content, encoding="utf-8")
    return feed_path