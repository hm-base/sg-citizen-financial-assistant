from generation.grok_client import GrokClient


class FakeMessage:
    def __init__(self, content: str):
        self.content = content


class FakeChoice:
    def __init__(self, content: str):
        self.message = FakeMessage(content)


class FakeCompletion:
    def __init__(self, content: str):
        self.choices = [FakeChoice(content)]


class FakeGrokSDK:
    def __init__(self, content: str):
        self.content = content
        self.calls = []

    def chat_completions_create(self, model: str, messages: list[dict]):
        self.calls.append((model, messages))
        return FakeCompletion(self.content)


def test_grok_client_generate_returns_message_content():
    fake_sdk = FakeGrokSDK("Answer: [Silver Support Scheme, Eligibility]")
    client = GrokClient(api_key="fake-key", model_name="grok-2-latest", sdk_client=fake_sdk)

    result = client.generate("What is Silver Support?")

    assert result == "Answer: [Silver Support Scheme, Eligibility]"
    model, messages = fake_sdk.calls[0]
    assert model == "grok-2-latest"
    assert messages[0]["content"] == "What is Silver Support?"
