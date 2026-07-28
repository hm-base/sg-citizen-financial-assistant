from pathlib import Path
from typing import Protocol

VIDEO_TRANSCRIPTION_PROMPT = (
    "Transcribe all spoken speech in this video, and separately describe any "
    "on-screen graphics, flowcharts, or tables (eligibility criteria, payout "
    "amounts, steps) in structured plain text. Do not add commentary."
)


class VideoTranscriptionClient(Protocol):
    def transcribe(self, video_path: Path, prompt: str) -> str: ...


def transcribe_video(path: Path, client: VideoTranscriptionClient) -> str:
    if not path.exists():
        raise FileNotFoundError(f"Video file not found: {path}")
    return client.transcribe(path, VIDEO_TRANSCRIPTION_PROMPT)
