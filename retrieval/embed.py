import numpy as np
import torch
from sentence_transformers import SentenceTransformer


def get_device() -> str:
    return "cuda" if torch.cuda.is_available() else "cpu"


def load_embedder(model_name: str, device: str | None = None) -> SentenceTransformer:
    return SentenceTransformer(model_name, device=device or get_device())


def embed_texts(texts: list[str], embedder: SentenceTransformer) -> np.ndarray:
    vectors = embedder.encode(
        texts,
        convert_to_numpy=True,
        normalize_embeddings=True,
        show_progress_bar=False,
    )
    return np.asarray(vectors, dtype=np.float32)
