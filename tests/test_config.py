import importlib
import os


def test_config_defaults(monkeypatch):
    monkeypatch.delenv("LLM_PROVIDER", raising=False)
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    import config
    importlib.reload(config)

    assert config.CHUNK_SIZE_WORDS == 350
    assert config.CHUNK_OVERLAP_WORDS == 50
    assert config.EMBEDDING_MODEL == "BAAI/bge-m3"
    assert config.TOP_K == 5
    assert 0.0 <= config.SIMILARITY_THRESHOLD <= 1.0
    assert config.RETRIEVAL_MODE == "dense"
    assert config.LLM_PROVIDER == "gemini"
    assert config.FALLBACK_MESSAGE == (
        "The available knowledge base does not contain enough information "
        "to answer this question."
    )


def test_config_reads_env_overrides(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "groq")
    monkeypatch.setenv("GEMINI_API_KEY", "fake-gemini-key")
    monkeypatch.setenv("GROQ_API_KEY", "fake-groq-key")
    import config
    importlib.reload(config)

    assert config.LLM_PROVIDER == "groq"
    assert config.GEMINI_API_KEY == "fake-gemini-key"
    assert config.GROQ_API_KEY == "fake-groq-key"
