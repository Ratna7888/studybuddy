"""ChromaDB vector store operations — persistent, local, free.

Only loads heavy imports when LIGHTWEIGHT_MODE is not enabled.
"""

import os
from config import settings

LIGHTWEIGHT = os.environ.get("LIGHTWEIGHT_MODE", "false").lower() == "true"

_client = None


def get_chroma_client():
    if LIGHTWEIGHT:
        raise RuntimeError("ChromaDB not available in lightweight mode")
    import chromadb
    from chromadb.config import Settings as ChromaSettings
    global _client
    if _client is None:
        _client = chromadb.PersistentClient(
            path=settings.chroma_persist_dir,
            settings=ChromaSettings(anonymized_telemetry=False),
        )
    return _client


def get_collection(user_id: int):
    """Each user gets their own ChromaDB collection for isolation."""
    client = get_chroma_client()
    return client.get_or_create_collection(
        name=f"user_{user_id}",
        metadata={"hnsw:space": "cosine"},
    )


def add_chunks(
    user_id: int,
    ids: list[str],
    texts: list[str],
    embeddings: list[list[float]],
    metadatas: list[dict],
):
    """Store document chunks with their embeddings."""
    collection = get_collection(user_id)
    collection.add(
        ids=ids,
        documents=texts,
        embeddings=embeddings,
        metadatas=metadatas,
    )


def search_chunks(
    user_id: int,
    query_embedding: list[float],
    top_k: int = 10,
) -> dict:
    """Semantic search for relevant chunks."""
    collection = get_collection(user_id)

    if collection.count() == 0:
        return {"ids": [[]], "documents": [[]], "metadatas": [[]], "distances": [[]]}

    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=min(top_k, collection.count()),
        include=["documents", "metadatas", "distances"],
    )
    return results


def delete_document_chunks(user_id: int, document_id: int):
    """Remove all chunks for a specific document from the vector store."""
    collection = get_collection(user_id)
    try:
        results = collection.get(
            where={"document_id": document_id},
            include=[],
        )
        if results["ids"]:
            collection.delete(ids=results["ids"])
    except Exception:
        pass