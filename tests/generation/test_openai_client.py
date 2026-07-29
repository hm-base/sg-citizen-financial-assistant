from generation.openai_client import OpenAIClient


class FakeMessage:
    def __init__(self, content: str):
        self.content = content


class FakeChoice:
    def __init__(self, content: str):
        self.message = FakeMessage(content)


class FakeCompletion:
    def __init__(self, content: str):
        self.choices = [FakeChoice(content)]


class FakeOpenAISDK:
    def __init__(self, content: str):
        self.content = content
        self.calls = []

    def chat_completions_create(self, model: str, messages: list[dict]):
        self.calls.append((model, messages))
        return FakeCompletion(self.content)


def test_openai_client_generate_returns_message_content():
    fake_sdk = FakeOpenAISDK("Answer: [Silver Support Scheme, Eligibility]")
    client = OpenAIClient(api_key="fake-key", model_name="gpt-5.4-mini", sdk_client=fake_sdk)

    result = client.generate("What is Silver Support?")

    assert result == "Answer: [Silver Support Scheme, Eligibility]"
    model, messages = fake_sdk.calls[0]
    assert model == "gpt-5.4-mini"
    assert messages[0]["content"] == "What is Silver Support?"
