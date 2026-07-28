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


def test_transcribe_video_caches_the_transcript_to_disk(tmp_path):
    video_path = tmp_path / "comcare-steps.mp4"
    video_path.write_bytes(b"fake video bytes")
    cache_dir = tmp_path / "processed"
    client = FakeClient("ComCare pays monthly cash assistance.")

    result = transcribe_video(video_path, client, cache_dir=cache_dir)

    assert result == "ComCare pays monthly cash assistance."
    cached = cache_dir / "comcare-steps.txt"
    assert cached.read_text(encoding="utf-8") == "ComCare pays monthly cash assistance."


def test_transcribe_video_reuses_a_cached_transcript_without_calling_gemini(tmp_path):
    """Re-indexing must not re-upload and re-transcribe every video."""
    video_path = tmp_path / "comcare-steps.mp4"
    video_path.write_bytes(b"fake video bytes")
    cache_dir = tmp_path / "processed"
    cache_dir.mkdir()
    (cache_dir / "comcare-steps.txt").write_text("cached transcript", encoding="utf-8")

    client = FakeClient("should never be requested")
    result = transcribe_video(video_path, client, cache_dir=cache_dir)

    assert result == "cached transcript"
    assert client.calls == []


def test_transcribe_video_ignores_a_cache_older_than_the_video(tmp_path):
    """A re-downloaded/edited video must invalidate its stale transcript."""
    import os

    video_path = tmp_path / "comcare-steps.mp4"
    video_path.write_bytes(b"fake video bytes")
    cache_dir = tmp_path / "processed"
    cache_dir.mkdir()
    cached = cache_dir / "comcare-steps.txt"
    cached.write_text("stale transcript", encoding="utf-8")
    video_mtime = video_path.stat().st_mtime
    os.utime(cached, (video_mtime - 100, video_mtime - 100))

    client = FakeClient("fresh transcript")
    result = transcribe_video(video_path, client, cache_dir=cache_dir)

    assert result == "fresh transcript"
    assert len(client.calls) == 1
    assert cached.read_text(encoding="utf-8") == "fresh transcript"


def test_transcribe_video_does_not_cache_an_empty_transcript(tmp_path):
    """Caching an empty result would permanently poison that video."""
    video_path = tmp_path / "comcare-steps.mp4"
    video_path.write_bytes(b"fake video bytes")
    cache_dir = tmp_path / "processed"
    client = FakeClient("   ")

    transcribe_video(video_path, client, cache_dir=cache_dir)

    assert not (cache_dir / "comcare-steps.txt").exists()
