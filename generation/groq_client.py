from openai import OpenAI

GROQ_BASE_URL = "https://api.groq.com/openai/v1"


class GroqClient:
    def __init__(self, api_key: str, model_name: str, sdk_client=None):
        self.model_name = model_name
        self._sdk_client = sdk_client or _RealOpenAIAdapter(api_key)

    def generate(self, prompt: str) -> str:
        completion = self._sdk_client.chat_completions_create(
            self.model_name, [{"role": "user", "content": prompt}]
        )
        return completion.choices[0].message.content


class _RealOpenAIAdapter:
    def __init__(self, api_key: str):
        self._client = OpenAI(api_key=api_key, base_url=GROQ_BASE_URL)

    def chat_completions_create(self, model: str, messages: list[dict]):
        return self._client.chat.completions.create(model=model, messages=messages)
