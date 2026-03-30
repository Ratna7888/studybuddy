"""Local embedding generation using sentence-transformers (100% free).

Only loads when LIGHTWEIGHT_MODE is not enabled.
"""

import os

LIGHTWEIGHT = os.environ.get("LIGHTWEIGHT_MODE", "false").lower() == "true"

_model = None


def get_embedding_model():
    if LIGHTWEIGHT:
        raise RuntimeError("Embeddings not available in lightweight mode")
    from sentence_transformers import SentenceTransformer
    from config import settings
    global _model
    if _model is None:
        print(f"Loading embedding model: {settings.embedding_model}...")
        _model = SentenceTransformer(settings.embedding_model)
        print("Embedding model loaded.")
    return _model


def generate_embeddings(texts: list[str]) -> list[list[float]]:
    model = get_embedding_model()
    embeddings = model.encode(texts, show_progress_bar=False, normalize_embeddings=True)
    return embeddings.tolist()


def generate_single_embedding(text: str) -> list[float]:
    return generate_embeddings([text])[0]