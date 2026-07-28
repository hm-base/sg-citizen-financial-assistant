from pathlib import Path

from generation.gemini_client import GeminiClient


class FakeResponse:
    def __init__(self, text: str):
        self.text = text


class FakeUploadedFile:
    def __init__(self, path):
        self.path = path
        self.uri = f"files/{Path(path).name}"


class FakeGenAIClient:
    def __init__(self, text_response: str):
        self.text_response = text_response
        self.calls = []
        self.uploaded = []

    def generate_content(self, model: str, contents):
        self.calls.append((model, contents))
        return FakeResponse(self.text_response)

    def upload_file(self, path):
        self.uploaded.append(path)
        return FakeUploadedFile(path)


def test_gemini_client_generate_returns_response_text():
    fake_sdk = FakeGenAIClient("Answer: [Baby Bonus Scheme, p.2]")
    client = GeminiClient(api_key="fake-key", model_name="gemini-1.5-flash", sdk_client=fake_sdk)

    result = client.generate("What is Baby Bonus?")

    assert result == "Answer: [Baby Bonus Scheme, p.2]"
    assert fake_sdk.calls[0][0] == "gemini-1.5-flash"


def test_gemini_client_transcribe_passes_video_and_prompt(tmp_path):
    video_path = tmp_path / "video.mp4"
    video_path.write_bytes(b"fake bytes")
    fake_sdk = FakeGenAIClient("Transcript: scheme explainer content.")
    client = GeminiClient(api_key="fake-key", model_name="gemini-1.5-flash", sdk_client=fake_sdk)

    result = client.transcribe(video_path, "Transcribe this video.")

    assert result == "Transcript: scheme explainer content."
    # The video itself must be uploaded and attached, otherwise the model would
    # fabricate a transcript from the prompt alone.
    assert fake_sdk.uploaded == [video_path]
    model, contents = fake_sdk.calls[0]
    assert model == "gemini-1.5-flash"
    assert isinstance(contents, list)
    assert getattr(contents[0], "path", None) == video_path
    assert contents[1] == "Transcribe this video."


def test_gemini_client_transcribe_rejects_missing_video(tmp_path):
    import pytest

    fake_sdk = FakeGenAIClient("never used")
    client = GeminiClient(api_key="fake-key", model_name="gemini-1.5-flash", sdk_client=fake_sdk)

    with pytest.raises(FileNotFoundError):
        client.transcribe(tmp_path / "missing.mp4", "Transcribe this video.")

    assert fake_sdk.calls == []


def test_real_adapter_uploads_via_sdk_files_api():
    """The adapter must call the google-genai `client.files.upload(file=...)` API."""
    from generation.gemini_client import _RealGenAIAdapter

    class FakeFiles:
        def __init__(self):
            self.uploaded = []

        def upload(self, *, file):
            self.uploaded.append(file)
            return FakeUploadedFile(file)

    class FakeModels:
        def __init__(self):
            self.calls = []

        def generate_content(self, *, model, contents):
            self.calls.append((model, contents))
            return FakeResponse("ok")

    class FakeSDK:
        def __init__(self):
            self.files = FakeFiles()
            self.models = FakeModels()

    sdk = FakeSDK()
    adapter = _RealGenAIAdapter(sdk)

    uploaded = adapter.upload_file(Path("videos") / "clip.mp4")

    assert sdk.files.uploaded == [str(Path("videos") / "clip.mp4")]
    assert adapter.generate_content("gemini-1.5-flash", [uploaded, "prompt"]).text == "ok"
