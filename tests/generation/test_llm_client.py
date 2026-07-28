from pathlib import Path

from generation.gemini_client import GeminiClient


class FakeResponse:
    def __init__(self, text: str):
        self.text = text


class FakeGenAIClient:
    def __init__(self, text_response: str):
        self.text_response = text_response
        self.calls = []

    def generate_content(self, model: str, contents):
        self.calls.append((model, contents))
        return FakeResponse(self.text_response)


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
