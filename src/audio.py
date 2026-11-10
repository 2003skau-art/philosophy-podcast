import asyncio
from pathlib import Path
import edge_tts
from mutagen.mp3 import MP3

VOICE = "en-IN-PrabhatNeural"  # Warm, natural Indian English male voice


async def _synthesize_async(full_text: str, out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    communicate = edge_tts.Communicate(text=full_text, voice=VOICE, rate="-5%")
    await communicate.save(str(out_path))


def build_episode_mp3(sections: dict, out_path: Path) -> dict:
    full_script = "\n\n...\n\n".join(sections.values())
    asyncio.run(_synthesize_async(full_script, out_path))

    audio_info = MP3(str(out_path)).info
    return {
        "file_path": str(out_path),
        "file_size_bytes": out_path.stat().st_size,
        "duration_seconds": int(round(audio_info.length)),
    }