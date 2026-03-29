"""
Lightweight retriever for production (low memory).
Uses BM25 only — no embeddings, no ChromaDB, no cross-encoder.
Stays under 512MB RAM easily.
"""

import os

# Check if we're in lightweight mode
LIGHTWEIGHT_MODE = os.environ.get("LIGHTWEIGHT_MODE", "false").lower() == "true"


if LIGHTWEIGHT_MODE:
    # ── BM25-only retrieval ──
    from core.sparse_retriever import search_bm25, add_to_bm25, remove_document_from_bm25

    def retrieve_for_production(user_id: int, query: str, top_k: int = 5) -> list[dict]:
        """BM25-only retrieval — no embeddings needed."""
        results = search_bm25(user_id, query, top_k=top_k * 2)
        return results[:top_k]

    def add_chunks_production(user_id: int, ids: list[str], texts: list[str], metadatas: list[dict]):
        """Index into BM25 only."""
        add_to_bm25(user_id, ids, texts, metadatas)

    def delete_chunks_production(user_id: int, document_id: int):
        """Remove from BM25 only."""
        remove_document_from_bm25(user_id, document_id)

else:
    # ── Full hybrid retrieval (local dev with models) ──
    retrieve_for_production = None
    add_chunks_production = None
    delete_chunks_production = None