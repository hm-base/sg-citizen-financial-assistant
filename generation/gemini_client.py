from pathlib import Path
from typing import Protocol

from google import genai


class GenAISdkClient(Protocol):
    def generate_content(self, model: str, contents): ...

    def upload_file(self, path): ...


class GeminiClient:
    def __init__(self, api_key: str, model_name: str, sdk_client=None):
        self.model_name = model_name
        if sdk_client is not None:
            self._sdk_client = sdk_client
        else:
            client = genai.Client(api_key=api_key)
            self._sdk_client = _RealGenAIAdapter(client)

    def generate(self, prompt: str) -> str:
        response = self._sdk_client.generate_content(self.model_name, prompt)
        return response.text

    def transcribe(self, video_path: Path, prompt: str) -> str:
        """Upload the video and transcribe it.

        The video must be attached to the request — prompting without it would
        make the model fabricate a transcript that later gets ingested as if it
        were grounded evidence.
        """
        video_path = Path(video_path)
        if not video_path.exists():
            raise FileNotFoundError(f"Video file not found: {video_path}")
        uploaded_file = self._sdk_client.upload_file(video_path)
        response = self._sdk_client.generate_content(self.model_name, [uploaded_file, prompt])
        return response.text


class _RealGenAIAdapter:
    def __init__(self, client):
        self.client = client

    def generate_content(self, model: str, contents):
        return self.client.models.generate_content(model=model, contents=contents)

    def upload_file(self, path):
        return self.client.files.upload(file=str(path))
