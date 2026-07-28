from pathlib import Path

from google import genai


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
        response = self._sdk_client.generate_content(self.model_name, prompt)
        return response.text


class _RealGenAIAdapter:
    def __init__(self, client):
        self.client = client

    def generate_content(self, model: str, contents):
        return self.client.models.generate_content(model=model, contents=contents)
