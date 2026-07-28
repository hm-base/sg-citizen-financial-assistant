import logging
from pathlib import Path
from typing import Protocol

logger = logging.getLogger(__name__)

VIDEO_TRANSCRIPTION_PROMPT = (
    "Transcribe all spoken speech in this video, and separately describe any "
    "on-screen graphics, flowcharts, or tables (eligibility criteria, payout "
    "amounts, steps) in structured plain text. Do not add commentary."
)


class VideoTranscriptionClient(Protocol):
    def transcribe(self, video_path: Path, prompt: str) -> str: ...


def transcript_cache_path(path: Path, cache_dir: Path) -> Path:
    return Path(cache_dir) / f"{Path(path).stem}.txt"


def _read_fresh_cached_transcript(path: Path, cache_dir: Path) -> str | None:
    """Return the cached transcript, or None if absent/stale/unreadable."""
    cached = transcript_cache_path(path, cache_dir)
    if not cached.exists():
        return None
    if cached.stat().st_mtime < path.stat().st_mtime:
        logger.info("Cached transcript for %s is older than the video; re-transcribing.", path.name)
        return None
    try:
        text = cached.read_text(encoding="utf-8")
    except OSError:
        logger.warning("Could not read cached transcript %s; re-transcribing.", cached)
        return None
    return text if text.strip() else None


def transcribe_video(
    path: Path,
    client: VideoTranscriptionClient,
    *,
    cache_dir: Path | None = None,
) -> str:
    """Transcribe a video, reusing a cached transcript when one is still valid.

    Transcription is the only step in the whole build that costs money and
    minutes, and it produces the same text every time for an unchanged file. When
    `cache_dir` is given, the transcript is written to
    `<cache_dir>/<stem>.txt` and reused on later runs as long as it is not older
    than the video, so re-indexing skips the upload and Gemini call entirely.
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Video file not found: {path}")

    if cache_dir is not None:
        cached_text = _read_fresh_cached_transcript(path, cache_dir)
        if cached_text is not None:
            logger.info("Reusing cached transcript for %s", path.name)
            return cached_text

    if client is None:
        raise ValueError(
            f"No cached transcript for {path.name} and no transcription client available."
        )

    transcript = client.transcribe(path, VIDEO_TRANSCRIPTION_PROMPT)

    # Never cache an empty transcript — it would permanently mask a failed run.
    if cache_dir is not None and transcript and transcript.strip():
        cached = transcript_cache_path(path, cache_dir)
        cached.parent.mkdir(parents=True, exist_ok=True)
        cached.write_text(transcript, encoding="utf-8")
        logger.info("Cached transcript for %s at %s", path.name, cached)

    return transcript
