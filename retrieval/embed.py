import numpy as np
import torch
from sentence_transformers import SentenceTransformer


def get_device() -> str:
    return "cuda" if torch.cuda.is_available() else "cpu"


def load_embedder(model_name: str, device: str | None = None) -> SentenceTransformer:
    return SentenceTransformer(model_name, device=device or get_device())


def embed_texts(
    texts: list[str],
    embedder: SentenceTransformer,
    *,
    batch_size: int = 2,
    show_progress_bar: bool = True,
) -> np.ndarray:
    # Small batches avoid GPU/CPU thrashing on large models (e.g. BGE-M3 on 8GB).
    vectors = embedder.encode(
        texts,
        batch_size=batch_size,
        convert_to_numpy=True,
        normalize_embeddings=True,
        show_progress_bar=show_progress_bar,
    )
    return np.asarray(vectors, dtype=np.float32)
