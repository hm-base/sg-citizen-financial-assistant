from generation.groq_client import GroqClient


class FakeMessage:
    def __init__(self, content: str):
        self.content = content


class FakeChoice:
    def __init__(self, content: str):
        self.message = FakeMessage(content)


class FakeCompletion:
    def __init__(self, content: str):
        self.choices = [FakeChoice(content)]


class FakeGroqSDK:
    def __init__(self, content: str):
        self.content = content
        self.calls = []

    def chat_completions_create(self, model: str, messages: list[dict]):
        self.calls.append((model, messages))
        return FakeCompletion(self.content)


def test_groq_client_generate_returns_message_content():
    fake_sdk = FakeGroqSDK("Answer: [Silver Support Scheme, Eligibility]")
    client = GroqClient(api_key="fake-key", model_name="llama-3.3-70b-versatile", sdk_client=fake_sdk)

    result = client.generate("What is Silver Support?")

    assert result == "Answer: [Silver Support Scheme, Eligibility]"
    model, messages = fake_sdk.calls[0]
    assert model == "llama-3.3-70b-versatile"
    assert messages[0]["content"] == "What is Silver Support?"
