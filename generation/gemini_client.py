from pathlib import Path

import google.generativeai as genai


class GeminiClient:
    def __init__(self, api_key: str, model_name: str, sdk_client=None):
        self.model_name = model_name
        if sdk_client is not None:
            self._sdk_client = sdk_client
        else:
            genai.configure(api_key=api_key)
            self._sdk_client = _RealGenAIAdapter()

    def generate(self, prompt: str) -> str:
        response = self._sdk_client.generate_content(self.model_name, prompt)
        return response.text

    def transcribe(self, video_path: Path, prompt: str) -> str:
        response = self._sdk_client.generate_content(self.model_name, prompt)
        return response.text


class _RealGenAIAdapter:
    def generate_content(self, model: str, contents):
        return genai.GenerativeModel(model).generate_content(contents)
