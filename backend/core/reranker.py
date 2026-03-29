"""Cross-encoder reranker for improving retrieval quality (free, local)."""

from sentence_transformers import CrossEncoder
from config import settings

_reranker = None


def get_reranker() -> CrossEncoder:
    global _reranker
    if _reranker is None:
        print(f"Loading reranker model: {settings.reranker_model}...")
        _reranker = CrossEncoder(settings.reranker_model, max_length=512)
        print("Reranker loaded.")
    return _reranker


def rerank_chunks(
    query: str,
    chunks: list[dict],  # each dict has 'text', 'metadata', 'id'
    top_k: int = None,
) -> list[dict]:
    """
    Rerank retrieved chunks using a cross-encoder model.
    Returns top_k chunks sorted by relevance score.
    """
    top_k = top_k or settings.rag_rerank_top_k

    if not chunks:
        return []

    reranker = get_reranker()

    # Build query-document pairs
    pairs = [(query, chunk["text"]) for chunk in chunks]
    scores = reranker.predict(pairs)

    # Attach scores and sort
    for chunk, score in zip(chunks, scores):
        chunk["rerank_score"] = float(score)

    ranked = sorted(chunks, key=lambda x: x["rerank_score"], reverse=True)

    # Filter by relevance threshold
    threshold = settings.relevance_threshold
    filtered = [c for c in ranked if c["rerank_score"] >= threshold]

    return filtered[:top_k] if filtered else ranked[:top_k]