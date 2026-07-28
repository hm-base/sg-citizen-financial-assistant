import numpy as np

from retrieval.embed import embed_texts, get_device, load_embedder


def test_get_device_returns_cpu_or_cuda():
    assert get_device() in ("cpu", "cuda")


def test_embed_texts_returns_normalized_float32_matrix():
    embedder = load_embedder("sentence-transformers/all-MiniLM-L6-v2", device="cpu")
    texts = ["Baby Bonus gives cash gifts.", "CDC vouchers help with groceries."]

    vectors = embed_texts(texts, embedder)

    assert vectors.shape == (2, 384)
    assert vectors.dtype == np.float32
    assert np.allclose(np.linalg.norm(vectors, axis=1), 1.0, atol=1e-4)
