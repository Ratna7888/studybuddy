"""Local embedding generation using sentence-transformers (100% free)."""

from sentence_transformers import SentenceTransformer
from config import settings

# Load model once at module level (cached in memory)
_model = None


def get_embedding_model() -> SentenceTransformer:
    global _model
    if _model is None:
        print(f"Loading embedding model: {settings.embedding_model}...")
        _model = SentenceTransformer(settings.embedding_model)
        print("Embedding model loaded.")
    return _model


def generate_embeddings(texts: list[str]) -> list[list[float]]:
    """Generate embeddings for a list of text strings."""
    model = get_embedding_model()
    embeddings = model.encode(texts, show_progress_bar=False, normalize_embeddings=True)
    return embeddings.tolist()


def generate_single_embedding(text: str) -> list[float]:
    """Generate embedding for a single text string."""
    return generate_embeddings([text])[0]