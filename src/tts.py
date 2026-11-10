
import asyncio
import os
from pathlib import Path

import edge_tts


VOICE = os.getenv("TTS_VOICE", "en-US-AriaNeural")
RATE = os.getenv("TTS_RATE", "+0%")


async def _generate_audio(text, output_path):
    communicate = edge_tts.Communicate(
        text=text,
        voice=VOICE,
        rate=RATE,
    )

    await communicate.save(str(output_path))


def make_mp3(paragraphs, output_path):
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    text = "\n\n".join(
        str(paragraph).strip()
        for paragraph in paragraphs
        if paragraph and str(paragraph).strip()
    )

    if not text:
        raise ValueError("No text provided for audio generation.")

    asyncio.run(_generate_audio(text, output_path))

    if not output_path.exists() or output_path.stat().st_size == 0:
        raise RuntimeError("Audio generation failed.")

    print(f"Audio created: {output_path}")
