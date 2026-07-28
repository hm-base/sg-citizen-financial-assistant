from pathlib import Path

from generation.gemini_client import GeminiClient


class FakeResponse:
    def __init__(self, text: str):
        self.text = text


class FakeUploadedFile:
    def __init__(self, path, state="ACTIVE"):
        self.path = path
        self.uri = f"files/{Path(path).name}"
        self.name = f"files/{Path(path).name}"
        self.state = state


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


class FakeFiles:
    """Fake Files API that reports `states` in order across upload + get calls."""

    def __init__(self, states=("ACTIVE",)):
        self.uploaded = []
        self.get_names = []
        self._states = list(states)

    def _next(self, file):
        state = self._states.pop(0) if len(self._states) > 1 else self._states[0]
        return FakeUploadedFile(file, state=state)

    def upload(self, *, file):
        self.uploaded.append(file)
        return self._next(file)

    def get(self, *, name):
        self.get_names.append(name)
        return self._next(Path(name).name)


class FakeModels:
    def __init__(self):
        self.calls = []

    def generate_content(self, *, model, contents):
        self.calls.append((model, contents))
        return FakeResponse("ok")


class FakeSDK:
    def __init__(self, states=("ACTIVE",)):
        self.files = FakeFiles(states)
        self.models = FakeModels()


def test_real_adapter_uploads_via_sdk_files_api():
    """The adapter must call the google-genai `client.files.upload(file=...)` API."""
    from generation.gemini_client import _RealGenAIAdapter

    sdk = FakeSDK()
    adapter = _RealGenAIAdapter(sdk)

    uploaded = adapter.upload_file(Path("videos") / "clip.mp4")

    assert sdk.files.uploaded == [str(Path("videos") / "clip.mp4")]
    assert adapter.generate_content("gemini-flash-latest", [uploaded, "prompt"]).text == "ok"


def test_real_adapter_polls_until_uploaded_file_becomes_active():
    """An upload starts in PROCESSING; generate_content rejects a non-ACTIVE file.

    So the adapter must keep calling files.get() until the state clears, and
    return the refreshed ACTIVE handle rather than the stale PROCESSING one.
    """
    from generation.gemini_client import _RealGenAIAdapter

    sleeps = []
    sdk = FakeSDK(states=["PROCESSING", "PROCESSING", "ACTIVE"])
    adapter = _RealGenAIAdapter(sdk, sleep=sleeps.append)

    uploaded = adapter.upload_file(Path("clip.mp4"))

    assert uploaded.state == "ACTIVE"
    assert len(sdk.files.get_names) == 2
    assert sdk.files.get_names == ["files/clip.mp4", "files/clip.mp4"]
    # It must actually wait between polls rather than hammering the API.
    assert sleeps and all(delay > 0 for delay in sleeps)


def test_real_adapter_raises_when_file_processing_fails():
    import pytest

    from generation.gemini_client import _RealGenAIAdapter

    sdk = FakeSDK(states=["PROCESSING", "FAILED"])
    adapter = _RealGenAIAdapter(sdk, sleep=lambda _seconds: None)

    with pytest.raises(RuntimeError, match="FAILED"):
        adapter.upload_file(Path("clip.mp4"))

    assert sdk.models.calls == []


def test_real_adapter_times_out_if_file_never_becomes_active():
    import pytest

    from generation.gemini_client import _RealGenAIAdapter

    clock = iter([0.0, 0.0, 30.0, 61.0, 61.0])
    sdk = FakeSDK(states=["PROCESSING"])
    adapter = _RealGenAIAdapter(
        sdk, sleep=lambda _seconds: None, monotonic=lambda: next(clock)
    )

    with pytest.raises(TimeoutError):
        adapter.upload_file(Path("clip.mp4"))

    assert sdk.models.calls == []


def test_real_adapter_accepts_an_enum_valued_file_state():
    """The SDK returns types.FileState, not a bare string."""
    from generation.gemini_client import _RealGenAIAdapter

    class EnumState:
        name = "ACTIVE"

    class EnumStateFiles(FakeFiles):
        def upload(self, *, file):
            self.uploaded.append(file)
            return FakeUploadedFile(file, state=EnumState())

    sdk = FakeSDK()
    sdk.files = EnumStateFiles()
    adapter = _RealGenAIAdapter(sdk)

    uploaded = adapter.upload_file(Path("clip.mp4"))

    assert sdk.files.get_names == []
    assert uploaded.state.name == "ACTIVE"
