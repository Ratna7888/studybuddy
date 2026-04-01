"""
BM25 Sparse Retriever — Lexical/keyword-based chunk retrieval.

Complements the dense (embedding) retriever for hybrid search.
BM25 excels at exact keyword matches that embeddings sometimes miss.
"""

import re
import json
import math
from pathlib import Path
from dataclasses import dataclass, field
from rank_bm25 import BM25Okapi
from config import settings

# Simple tokenizer — avoids heavy NLTK downloads
def tokenize(text: str) -> list[str]:
    """Lowercase, split on non-alphanumeric, remove stopwords and short tokens."""
    # Basic English stopwords
    STOPWORDS = {
        "a", "an", "the", "is", "are", "was", "were", "be", "been", "being",
        "have", "has", "had", "do", "does", "did", "will", "would", "could",
        "should", "may", "might", "shall", "can", "need", "dare", "ought",
        "used", "to", "of", "in", "for", "on", "with", "at", "by", "from",
        "as", "into", "through", "during", "before", "after", "above", "below",
        "between", "out", "off", "over", "under", "again", "further", "then",
        "once", "here", "there", "when", "where", "why", "how", "all", "both",
        "each", "few", "more", "most", "other", "some", "such", "no", "nor",
        "not", "only", "own", "same", "so", "than", "too", "very", "just",
        "don", "now", "and", "but", "or", "if", "it", "its", "this", "that",
        "these", "those", "i", "me", "my", "we", "our", "you", "your", "he",
        "him", "his", "she", "her", "they", "them", "their", "what", "which",
        "who", "whom",
    }
    tokens = re.findall(r'[a-z0-9]+', text.lower())
    return [t for t in tokens if t not in STOPWORDS and len(t) > 1]


@dataclass
class BM25Index:
    """In-memory BM25 index for a user's document chunks."""
    corpus_tokens: list[list[str]] = field(default_factory=list)
    chunk_ids: list[str] = field(default_factory=list)
    chunk_texts: list[str] = field(default_factory=list)
    chunk_metadatas: list[dict] = field(default_factory=list)
    bm25: BM25Okapi | None = None

    def add_chunks(
        self,
        ids: list[str],
        texts: list[str],
        metadatas: list[dict],
    ):
        """Add chunks to the BM25 index."""
        for cid, text, meta in zip(ids, texts, metadatas):
            tokens = tokenize(text)
            if not tokens:
                continue
            self.chunk_ids.append(cid)
            self.chunk_texts.append(text)
            self.chunk_metadatas.append(meta)
            self.corpus_tokens.append(tokens)

        # Rebuild BM25 index
        if self.corpus_tokens:
            self.bm25 = BM25Okapi(self.corpus_tokens)

    def remove_by_document_id(self, document_id: int):
        """Remove all chunks belonging to a document."""
        indices_to_keep = [
            i for i, m in enumerate(self.chunk_metadatas)
            if m.get("document_id") != document_id
        ]
        self.chunk_ids = [self.chunk_ids[i] for i in indices_to_keep]
        self.chunk_texts = [self.chunk_texts[i] for i in indices_to_keep]
        self.chunk_metadatas = [self.chunk_metadatas[i] for i in indices_to_keep]
        self.corpus_tokens = [self.corpus_tokens[i] for i in indices_to_keep]

        if self.corpus_tokens:
            self.bm25 = BM25Okapi(self.corpus_tokens)
        else:
            self.bm25 = None

    def search(self, query: str, top_k: int = 10) -> list[dict]:
        """Search the BM25 index and return ranked chunks."""
        if not self.bm25 or not self.corpus_tokens:
            return []

        query_tokens = tokenize(query)
        if not query_tokens:
            return []

        scores = self.bm25.get_scores(query_tokens)

        # Get top-k indices sorted by score
        scored_indices = sorted(
            enumerate(scores), key=lambda x: x[1], reverse=True
        )[:top_k]

        results = []
        for idx, score in scored_indices:
            if score <= 0:
                continue
            results.append({
                "id": self.chunk_ids[idx],
                "text": self.chunk_texts[idx],
                "metadata": self.chunk_metadatas[idx],
                "bm25_score": float(score),
            })

        return results


# ────────────────────────────────────────────
# Global index store — one BM25 index per user
# ────────────────────────────────────────────
_user_indices: dict[int, BM25Index] = {}


def get_user_index(user_id: int) -> BM25Index:
    """Get or create a BM25 index for a user."""
    if user_id not in _user_indices:
        _user_indices[user_id] = BM25Index()
    return _user_indices[user_id]


def add_to_bm25(
    user_id: int,
    ids: list[str],
    texts: list[str],
    metadatas: list[dict],
):
    """Add document chunks to the user's BM25 index."""
    index = get_user_index(user_id)
    index.add_chunks(ids, texts, metadatas)


def search_bm25(user_id: int, query: str, top_k: int = 10) -> list[dict]:
    """Sparse retrieval: BM25 keyword search."""
    index = get_user_index(user_id)
    return index.search(query, top_k)


def remove_document_from_bm25(user_id: int, document_id: int):
    """Remove a document's chunks from the BM25 index."""
    index = get_user_index(user_id)
    index.remove_by_document_id(document_id)


async def rebuild_bm25_index(user_id: int, db_session):
    """
    Rebuild the entire BM25 index for a user from the database.
    Called on server startup or when index might be stale.
    """
    from sqlalchemy import select
    from models import Chunk, Document

    _user_indices[user_id] = BM25Index()
    index = _user_indices[user_id]

    result = await db_session.execute(
        select(Chunk, Document.title)
        .join(Document, Chunk.document_id == Document.id)
        .where(Document.user_id == user_id)
        .order_by(Chunk.chunk_index)
    )
    rows = result.all()

    if not rows:
        return

    ids = []
    texts = []
    metadatas = []
    for chunk, doc_title in rows:
        meta = chunk.metadata_json or {}
        meta["document_id"] = chunk.document_id
        meta["document_title"] = doc_title
        ids.append(chunk.chroma_id)
        texts.append(chunk.chunk_text)
        metadatas.append(meta)

    index.add_chunks(ids, texts, metadatas)
    print(f"BM25 index rebuilt for user {user_id}: {len(ids)} chunks indexed")