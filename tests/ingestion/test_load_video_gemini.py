from pathlib import Path

from ingestion.load_video_gemini import transcribe_video


class FakeClient:
    def __init__(self, response: str):
        self.response = response
        self.calls = []

    def transcribe(self, video_path: Path, prompt: str) -> str:
        self.calls.append((video_path, prompt))
        return self.response


def test_transcribe_video_delegates_to_client(tmp_path):
    video_path = tmp_path / "baby_bonus_explainer.mp4"
    video_path.write_bytes(b"fake video bytes")
    client = FakeClient("Baby Bonus gives $8,000 to $10,000 per child.")

    result = transcribe_video(video_path, client)

    assert result == "Baby Bonus gives $8,000 to $10,000 per child."
    assert client.calls[0][0] == video_path
    assert "transcribe" in client.calls[0][1].lower() or "describe" in client.calls[0][1].lower()


def test_transcribe_video_rejects_missing_file(tmp_path):
    import pytest

    missing = tmp_path / "missing.mp4"
    client = FakeClient("irrelevant")
    with pytest.raises(FileNotFoundError):
        transcribe_video(missing, client)
