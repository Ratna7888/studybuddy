"""
Hybrid Retriever — Fuses BM25 (sparse) + Embedding (dense) results.

Architecture:
    Query
      │
      ├──► BM25 Sparse Search ──────► ranked list A
      │
      ├──► Dense Embedding Search ──► ranked list B
      │
      └──► Reciprocal Rank Fusion (RRF)
              │
              ▼
          Fused ranked list
              │
              ▼
          Cross-Encoder Reranker (optional)
              │
              ▼
          Final top-k chunks for context
"""

from dataclasses import dataclass
from enum import Enum
from core.embeddings import generate_single_embedding
from core.vector_store import search_chunks as dense_search
from core.sparse_retriever import search_bm25
from core.reranker import rerank_chunks
from config import settings


class RetrievalMode(str, Enum):
    SPARSE = "sparse"       # BM25 only
    DENSE = "dense"         # Embedding only (original behavior)
    HYBRID = "hybrid"       # BM25 + Embedding fusion


@dataclass
class RetrievalConfig:
    """Configuration for hybrid retrieval."""
    mode: RetrievalMode = RetrievalMode.HYBRID
    sparse_top_k: int = 15        # BM25 candidates
    dense_top_k: int = 15         # Embedding candidates
    fusion_top_k: int = 10        # After fusion
    final_top_k: int = 5          # After reranking
    use_reranker: bool = True     # Cross-encoder reranking
    rrf_k: int = 60               # RRF constant (standard is 60)
    sparse_weight: float = 0.4    # Weight for BM25 in weighted fusion
    dense_weight: float = 0.6     # Weight for embeddings in weighted fusion
    fusion_method: str = "rrf"    # "rrf" or "weighted"


# Default config
DEFAULT_CONFIG = RetrievalConfig()


def reciprocal_rank_fusion(
    ranked_lists: list[list[dict]],
    k: int = 60,
    top_k: int = 10,
) -> list[dict]:
    """
    Reciprocal Rank Fusion (RRF) — merges multiple ranked lists.

    RRF score for document d = Σ  1 / (k + rank_i(d))
    where rank_i(d) is the rank of d in list i.

    This is proven to outperform most individual rankers.
    Paper: "Reciprocal Rank Fusion outperforms Condorcet and Individual Rank Learning Methods"
    """
    # Collect all unique chunks by ID
    chunk_map: dict[str, dict] = {}   # id -> chunk data
    rrf_scores: dict[str, float] = {} # id -> cumulative RRF score

    for ranked_list in ranked_lists:
        for rank, chunk in enumerate(ranked_list):
            cid = chunk["id"]
            rrf_scores[cid] = rrf_scores.get(cid, 0.0) + 1.0 / (k + rank + 1)

            # Keep the chunk data (first seen wins, or update with richer data)
            if cid not in chunk_map:
                chunk_map[cid] = chunk.copy()

    # Sort by RRF score descending
    sorted_ids = sorted(rrf_scores.keys(), key=lambda x: rrf_scores[x], reverse=True)

    results = []
    for cid in sorted_ids[:top_k]:
        chunk = chunk_map[cid]
        chunk["rrf_score"] = rrf_scores[cid]
        chunk["fusion_method"] = "rrf"
        results.append(chunk)

    return results


def weighted_fusion(
    sparse_results: list[dict],
    dense_results: list[dict],
    sparse_weight: float = 0.4,
    dense_weight: float = 0.6,
    top_k: int = 10,
) -> list[dict]:
    """
    Weighted score fusion — normalizes scores from each retriever
    and combines them with configurable weights.
    """
    chunk_map: dict[str, dict] = {}
    scores: dict[str, float] = {}

    # Normalize and weight BM25 scores
    if sparse_results:
        max_bm25 = max(r.get("bm25_score", 0) for r in sparse_results) or 1.0
        for chunk in sparse_results:
            cid = chunk["id"]
            norm_score = (chunk.get("bm25_score", 0) / max_bm25) * sparse_weight
            scores[cid] = scores.get(cid, 0.0) + norm_score
            if cid not in chunk_map:
                chunk_map[cid] = chunk.copy()

    # Normalize and weight dense scores (distance → similarity)
    if dense_results:
        # ChromaDB returns distances (lower = better), convert to similarity
        max_dist = max(r.get("distance", 1) for r in dense_results) or 1.0
        for chunk in dense_results:
            cid = chunk["id"]
            similarity = 1.0 - (chunk.get("distance", 0) / max_dist) if max_dist > 0 else 0.5
            norm_score = similarity * dense_weight
            scores[cid] = scores.get(cid, 0.0) + norm_score
            if cid not in chunk_map:
                chunk_map[cid] = chunk.copy()

    # Sort by combined score
    sorted_ids = sorted(scores.keys(), key=lambda x: scores[x], reverse=True)

    results = []
    for cid in sorted_ids[:top_k]:
        chunk = chunk_map[cid]
        chunk["fusion_score"] = scores[cid]
        chunk["fusion_method"] = "weighted"
        results.append(chunk)

    return results


def hybrid_retrieve(
    user_id: int,
    query: str,
    config: RetrievalConfig = None,
) -> list[dict]:
    """
    Main hybrid retrieval function.

    Flow:
    1. Run sparse (BM25) retrieval
    2. Run dense (embedding) retrieval
    3. Fuse results using RRF or weighted fusion
    4. Optionally rerank with cross-encoder
    5. Return final top-k chunks
    """
    config = config or DEFAULT_CONFIG

    sparse_results = []
    dense_results = []

    # ── Step 1: Sparse Retrieval (BM25) ──
    if config.mode in (RetrievalMode.SPARSE, RetrievalMode.HYBRID):
        sparse_results = search_bm25(user_id, query, top_k=config.sparse_top_k)

    # ── Step 2: Dense Retrieval (Embeddings) ──
    if config.mode in (RetrievalMode.DENSE, RetrievalMode.HYBRID):
        query_embedding = generate_single_embedding(query)
        raw = dense_search(user_id, query_embedding, top_k=config.dense_top_k)

        ids = raw["ids"][0] if raw["ids"] else []
        docs = raw["documents"][0] if raw["documents"] else []
        metas = raw["metadatas"][0] if raw["metadatas"] else []
        dists = raw["distances"][0] if raw["distances"] else []

        for i in range(len(ids)):
            dense_results.append({
                "id": ids[i],
                "text": docs[i],
                "metadata": metas[i],
                "distance": dists[i],
            })

    # ── Step 3: Fusion ──
    if config.mode == RetrievalMode.SPARSE:
        fused = sparse_results[:config.fusion_top_k]
    elif config.mode == RetrievalMode.DENSE:
        fused = dense_results[:config.fusion_top_k]
    else:
        # Hybrid fusion
        if config.fusion_method == "rrf":
            fused = reciprocal_rank_fusion(
                [sparse_results, dense_results],
                k=config.rrf_k,
                top_k=config.fusion_top_k,
            )
        else:
            fused = weighted_fusion(
                sparse_results, dense_results,
                sparse_weight=config.sparse_weight,
                dense_weight=config.dense_weight,
                top_k=config.fusion_top_k,
            )

    if not fused:
        return []

    # ── Step 4: Optional Cross-Encoder Reranking ──
    if config.use_reranker and len(fused) > 1:
        final = rerank_chunks(query, fused, top_k=config.final_top_k)
    else:
        final = fused[:config.final_top_k]

    return final