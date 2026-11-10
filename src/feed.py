import json, os, pathlib
from email.utils import format_datetime
from xml.sax.saxutils import escape

REPO = os.environ.get("GITHUB_REPOSITORY", "user/repo")
OWNER, NAME = REPO.split("/")
SITE = f"https://{OWNER}.github.io/{NAME}"
DOCS = pathlib.Path("docs")

def add_episode(ep):
    DOCS.mkdir(exist_ok=True)
    idx = DOCS / "episodes.json"
    eps = json.loads(idx.read_text()) if idx.exists() else []
    eps.insert(0, ep)
    idx.write_text(json.dumps(eps, ensure_ascii=False, indent=1), encoding="utf-8")
    items = ""
    for e in eps:
        items += f"""
<item>
<title>{escape(e['title'])}</title>
<description>{escape(e['notes'])}</description>
<guid isPermaLink="false">{e['guid']}</guid>
<pubDate>{format_datetime(__import__('datetime').datetime.fromisoformat(e['date']))}</pubDate>
<enclosure url="{e['url']}" length="{e['size']}" type="audio/mpeg"/>
<itunes:duration>{e['duration']}</itunes:duration>
</item>"""
    (DOCS / "feed.xml").write_text(f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:itunes="http://www.itunes.com/dtds/podcast-1.0.dtd">
<channel>
<title>Dharma at Dusk</title>
<link>{SITE}</link>
<language>en</language>
<description>Daily Indian philosophy, told as stories, grounded in the original texts.</description>
<itunes:author>Daily Dharma Agent</itunes:author>
<itunes:explicit>false</itunes:explicit>{items}
</channel>
</rss>""", encoding="utf-8")