"""
Full RAG Pipeline with Hybrid Retrieval.

Architecture:
    Query
      ├──► BM25 Sparse Search ──► ranked list A
      ├──► Dense Embedding Search ──► ranked list B
      └──► Reciprocal Rank Fusion (RRF)
              │
              ▼
          Cross-Encoder Reranker
              │
              ▼
          Context Assembly ──► Gemini LLM ──► Grounded Answer
"""

import json
import os
from dataclasses import dataclass

LIGHTWEIGHT = os.environ.get("LIGHTWEIGHT_MODE", "false").lower() == "true"

if LIGHTWEIGHT:
    from core.sparse_retriever import search_bm25
else:
    from core.hybrid_retriever import (
        hybrid_retrieve,
        RetrievalConfig,
        RetrievalMode,
    )

from core.llm import (
    generate_answer,
    TUTOR_SYSTEM_PROMPT,
    EXPLAIN_SIMPLY_PROMPT,
    FLASHCARD_GENERATION_PROMPT,
    QUIZ_MCQ_PROMPT,
    QUIZ_TRUE_FALSE_PROMPT,
    SUMMARY_PROMPT,
    TEACH_BACK_PROMPT,
    CONCEPT_BREAKDOWN_PROMPT,
)
from config import settings


@dataclass
class RAGResult:
    answer: str
    sources: list[dict]
    confidence: str
    mode: str
    retrieval_info: dict  # metadata about retrieval strategy used


# Default hybrid config (only used when not lightweight)
if not LIGHTWEIGHT:
    HYBRID_CONFIG = RetrievalConfig(
        mode=RetrievalMode.HYBRID,
        sparse_top_k=15, dense_top_k=15,
        fusion_top_k=10, final_top_k=5,
        use_reranker=True, rrf_k=60, fusion_method="rrf",
    )
else:
    # Dummy so code doesn't crash on references
    HYBRID_CONFIG = None
    RetrievalConfig = None


# ────────────────────────────────────────────
# Main Retrieval Function
# ────────────────────────────────────────────

def retrieve_context(user_id: int, query: str, config=None) -> list[dict]:
    """Retrieve chunks — BM25-only in production, hybrid locally."""
    if LIGHTWEIGHT:
        return search_bm25(user_id, query, top_k=5)
    else:
        config = config or HYBRID_CONFIG
        return hybrid_retrieve(user_id, query, config)


def build_context_prompt(chunks: list[dict]) -> str:
    """Build the context section of the prompt from retrieved chunks."""
    if not chunks:
        return "NO CONTEXT AVAILABLE."

    context_parts = []
    for i, chunk in enumerate(chunks):
        meta = chunk.get("metadata", {})
        doc_title = meta.get("document_title", "Unknown")
        section = meta.get("section", "")
        source_label = f"[Source {i+1}: {doc_title}"
        if section:
            source_label += f" — {section}"
        source_label += "]"

        context_parts.append(f"{source_label}\n{chunk['text']}")

    return "\n\n---\n\n".join(context_parts)


def format_sources(chunks: list[dict]) -> list[dict]:
    """Format chunk metadata into clean source references."""
    sources = []
    for i, chunk in enumerate(chunks):
        meta = chunk.get("metadata", {})

        # Pick best available score
        score = (
            chunk.get("rerank_score")
            or chunk.get("rrf_score")
            or chunk.get("fusion_score")
            or chunk.get("bm25_score")
            or 0
        )

        sources.append({
            "index": i + 1,
            "document_title": meta.get("document_title", "Unknown"),
            "section": meta.get("section", ""),
            "chunk_index": meta.get("chunk_index", 0),
            "relevance_score": round(float(score), 3),
            "text_preview": chunk["text"][:200] + "..." if len(chunk["text"]) > 200 else chunk["text"],
            "full_text": chunk["text"],
            "retrieval_method": chunk.get("fusion_method", "unknown"),
        })
    return sources


def _build_retrieval_info(chunks: list[dict], config=None) -> dict:
    """Metadata about what retrieval strategy was used."""
    if LIGHTWEIGHT:
        return {"mode": "bm25_only", "chunks_retrieved": len(chunks)}
    return {
        "mode": config.mode.value if config else "hybrid",
        "fusion_method": config.fusion_method if config else "rrf",
        "reranker_used": config.use_reranker if config else False,
        "chunks_retrieved": len(chunks),
    }


# ────────────────────────────────────────────
# Conversational Mode (Q&A, Explain, Teach Back)
# ────────────────────────────────────────────

CONVERSATION_SYSTEM_PROMPTS = {
    "qa": """You are a personal AI tutor having a conversation with a student.
Answer ONLY from the provided study context. Do NOT use outside knowledge.
If the answer is NOT in the material, say: "I cannot answer this from the provided study material."
Always cite sources. Keep a natural conversational tone — refer to previous messages when relevant.
Use markdown formatting: **bold** for key terms, bullet points for lists, headings for structure.""",

    "explain": """You are a personal AI tutor explaining topics in a simple, beginner-friendly way.
ONLY use information from the provided context. Use analogies and simple language.
If the topic is not in the context, say: "I cannot answer this from the provided study material."
This is a conversation — build on previous messages, ask if the student understood, go deeper when asked.
Use markdown formatting for clarity.""",

    "teach_back": """You are evaluating a student's understanding through conversation.
The study context is provided below — use it as the source of truth.
When the student explains something:
1. Acknowledge what they got RIGHT
2. Gently correct what they got WRONG
3. Ask follow-up questions to probe deeper understanding
4. Give a rating: Excellent / Good / Needs Work
Keep it encouraging and conversational. Build on previous exchanges.""",
}


async def ask_conversational(
    user_id: int,
    question: str,
    history: list[dict],
    mode: str = "qa",
    config: RetrievalConfig = None,
) -> RAGResult:
    """
    Multi-turn conversational RAG.
    Retrieves context based on the latest question,
    then includes conversation history in the prompt.
    """
    config = config or HYBRID_CONFIG
    chunks = retrieve_context(user_id, question, config)

    if not chunks or not _chunks_are_relevant(chunks, question):
        return _no_context_result(mode)

    context = build_context_prompt(chunks)
    system = CONVERSATION_SYSTEM_PROMPTS.get(mode, CONVERSATION_SYSTEM_PROMPTS["qa"])

    # Build conversation history string
    history_text = ""
    if history:
        history_text = "\n\nCONVERSATION SO FAR:\n"
        for msg in history[-10:]:  # Last 10 messages to stay within token limits
            role = "Student" if msg["role"] == "user" else "Tutor"
            history_text += f"{role}: {msg['content']}\n"

    prompt = f"CONTEXT:\n{context}{history_text}\n\nStudent: {question}\n\nTutor:"

    answer = await generate_answer(system, prompt)

    scores = [c.get("rerank_score") or c.get("rrf_score") or c.get("fusion_score") or 0 for c in chunks]
    avg = sum(scores) / len(scores) if scores else 0
    confidence = "high" if avg > 2.0 else "medium" if avg > 0.5 else "low"

    return RAGResult(
        answer=answer,
        sources=format_sources(chunks),
        confidence=confidence,
        mode=mode,
        retrieval_info=_build_retrieval_info(chunks, config),
    )


# ────────────────────────────────────────────
# Q&A Mode (single-shot, kept for backward compat)
# ────────────────────────────────────────────

async def ask_question(
    user_id: int,
    question: str,
    config=None,
) -> RAGResult:
    """Direct Q&A with RAG grounding."""
    chunks = retrieve_context(user_id, question, config)

    if not chunks or not _chunks_are_relevant(chunks, question):
        return RAGResult(
            answer="I cannot answer this from the provided study material. No relevant content was found in your uploaded documents.",
            sources=[],
            confidence="low",
            mode="qa",
            retrieval_info=_build_retrieval_info([]),
        )

    context = build_context_prompt(chunks)
    prompt = f"CONTEXT:\n{context}\n\nQUESTION:\n{question}"

    answer = await generate_answer(TUTOR_SYSTEM_PROMPT, prompt)

    # Determine confidence based on best available score
    scores = [
        c.get("rerank_score") or c.get("rrf_score") or c.get("fusion_score") or 0
        for c in chunks
    ]
    avg_score = sum(scores) / len(scores) if scores else 0
    confidence = "high" if avg_score > 2.0 else "medium" if avg_score > 0.5 else "low"

    return RAGResult(
        answer=answer,
        sources=format_sources(chunks),
        confidence=confidence,
        mode="qa",
        retrieval_info=_build_retrieval_info(chunks, config),
    )


# ────────────────────────────────────────────
# Explain Simply Mode
# ────────────────────────────────────────────

async def explain_simply(user_id: int, topic: str) -> RAGResult:
    chunks = retrieve_context(user_id, topic)
    if not chunks or not _chunks_are_relevant(chunks, topic):
        return _no_context_result("explain")

    context = build_context_prompt(chunks)
    prompt = f"CONTEXT:\n{context}\n\nTOPIC TO EXPLAIN SIMPLY:\n{topic}"
    answer = await generate_answer(EXPLAIN_SIMPLY_PROMPT, prompt)

    return RAGResult(
        answer=answer,
        sources=format_sources(chunks),
        confidence=_calc_confidence(chunks),
        mode="explain",
        retrieval_info=_build_retrieval_info(chunks, HYBRID_CONFIG),
    )


# ────────────────────────────────────────────
# Summary Mode
# ────────────────────────────────────────────

async def generate_summary(user_id: int, topic: str) -> RAGResult:
    chunks = retrieve_context(user_id, topic)
    if not chunks or not _chunks_are_relevant(chunks):
        return _no_context_result("summary")

    context = build_context_prompt(chunks)
    prompt = f"CONTEXT:\n{context}\n\nTOPIC TO SUMMARIZE:\n{topic}"
    answer = await generate_answer(SUMMARY_PROMPT, prompt)

    return RAGResult(
        answer=answer,
        sources=format_sources(chunks),
        confidence=_calc_confidence(chunks),
        mode="summary",
        retrieval_info=_build_retrieval_info(chunks, HYBRID_CONFIG),
    )


# ────────────────────────────────────────────
# Flashcard Generation
# ────────────────────────────────────────────

async def generate_flashcards(user_id: int, topic: str, count: int = 5, doc_ids: list[int] = None) -> dict:
    chunks = _retrieve_with_fallback(user_id, topic, doc_ids=doc_ids)
    if not chunks:
        return {"flashcards": [], "sources": [], "error": NO_RELEVANCE_MSG}

    context = build_context_prompt(chunks)
    system = FLASHCARD_GENERATION_PROMPT.format(count=count)
    prompt = f"CONTEXT:\n{context}\n\nTOPIC:\n{topic}"

    raw = await generate_answer(system, prompt)

    try:
        flashcards = json.loads(_extract_json(raw))
    except json.JSONDecodeError:
        flashcards = []

    return {
        "flashcards": flashcards,
        "sources": format_sources(chunks),
        "retrieval_info": _build_retrieval_info(chunks, HYBRID_CONFIG),
    }


# ────────────────────────────────────────────
# Quiz Generation (MCQ)
# ────────────────────────────────────────────

async def generate_quiz_mcq(user_id: int, topic: str, count: int = 5, doc_ids: list[int] = None) -> dict:
    chunks = _retrieve_with_fallback(user_id, topic, doc_ids=doc_ids)
    if not chunks:
        return {"questions": [], "sources": [], "error": NO_RELEVANCE_MSG}

    context = build_context_prompt(chunks)
    system = QUIZ_MCQ_PROMPT.format(count=count)
    prompt = f"CONTEXT:\n{context}\n\nTOPIC:\n{topic}"

    raw = await generate_answer(system, prompt)

    try:
        questions = json.loads(_extract_json(raw))
    except json.JSONDecodeError:
        questions = []

    return {
        "questions": questions,
        "sources": format_sources(chunks),
        "mode": "mcq",
        "retrieval_info": _build_retrieval_info(chunks, HYBRID_CONFIG),
    }


# ────────────────────────────────────────────
# Quiz Generation (True/False)
# ────────────────────────────────────────────

async def generate_quiz_tf(user_id: int, topic: str, count: int = 5, doc_ids: list[int] = None) -> dict:
    chunks = _retrieve_with_fallback(user_id, topic, doc_ids=doc_ids)
    if not chunks:
        return {"questions": [], "sources": [], "error": NO_RELEVANCE_MSG}

    context = build_context_prompt(chunks)
    system = QUIZ_TRUE_FALSE_PROMPT.format(count=count)
    prompt = f"CONTEXT:\n{context}\n\nTOPIC:\n{topic}"

    raw = await generate_answer(system, prompt)

    try:
        questions = json.loads(_extract_json(raw))
    except json.JSONDecodeError:
        questions = []

    return {
        "questions": questions,
        "sources": format_sources(chunks),
        "mode": "tf",
        "retrieval_info": _build_retrieval_info(chunks, HYBRID_CONFIG),
    }


# ────────────────────────────────────────────
# Socratic Mode
# ────────────────────────────────────────────

async def socratic_question(user_id: int, topic: str) -> RAGResult:
    chunks = retrieve_context(user_id, topic)
    if not chunks or not _chunks_are_relevant(chunks):
        return _no_context_result("socratic")

    context = build_context_prompt(chunks)
    prompt = f"CONTEXT:\n{context}\n\nTOPIC:\n{topic}"
    answer = await generate_answer(SOCRATIC_PROMPT, prompt)

    return RAGResult(
        answer=answer,
        sources=format_sources(chunks),
        confidence=_calc_confidence(chunks),
        mode="socratic",
        retrieval_info=_build_retrieval_info(chunks, HYBRID_CONFIG),
    )


# ────────────────────────────────────────────
# Teach-Back Evaluation
# ────────────────────────────────────────────

async def evaluate_teach_back(
    user_id: int, topic: str, student_explanation: str
) -> RAGResult:
    chunks = retrieve_context(user_id, topic)
    if not chunks:
        return _no_context_result("teach_back")

    context = build_context_prompt(chunks)
    prompt = (
        f"CONTEXT:\n{context}\n\n"
        f"TOPIC: {topic}\n\n"
        f"STUDENT'S EXPLANATION:\n{student_explanation}"
    )
    answer = await generate_answer(TEACH_BACK_PROMPT, prompt)

    return RAGResult(
        answer=answer,
        sources=format_sources(chunks),
        confidence=_calc_confidence(chunks),
        mode="teach_back",
        retrieval_info=_build_retrieval_info(chunks, HYBRID_CONFIG),
    )


# ────────────────────────────────────────────
# Concept Breakdown
# ────────────────────────────────────────────

async def concept_breakdown(user_id: int, topic: str) -> dict:
    chunks = retrieve_context(user_id, topic)
    if not chunks or not _chunks_are_relevant(chunks):
        return {"error": NO_RELEVANCE_MSG}

    context = build_context_prompt(chunks)
    prompt = f"CONTEXT:\n{context}\n\nTOPIC:\n{topic}"

    raw = await generate_answer(CONCEPT_BREAKDOWN_PROMPT, prompt)

    try:
        breakdown = json.loads(_extract_json(raw))
    except json.JSONDecodeError:
        breakdown = {"raw": raw}

    breakdown["sources"] = format_sources(chunks)
    breakdown["retrieval_info"] = _build_retrieval_info(chunks, HYBRID_CONFIG)
    return breakdown


# ────────────────────────────────────────────
# Helpers
# ────────────────────────────────────────────

def _no_context_result(mode: str) -> RAGResult:
    return RAGResult(
        answer="I cannot answer this from the provided study material. No relevant content was found.",
        sources=[],
        confidence="low",
        mode=mode,
        retrieval_info={"mode": "hybrid", "chunks_retrieved": 0},
    )


def _retrieve_with_fallback(user_id: int, query: str) -> list[dict]:
    """
    Retrieve chunks with fallback for broad/generic queries.
    If BM25 keyword search returns nothing, fall back to returning
    the first few chunks from the user's documents.
    """
    chunks = retrieve_context(user_id, query)

    # Try broader search
    if not chunks and len(query.split()) > 2:
        broader = " ".join(query.split()[:3])
        chunks = retrieve_context(user_id, broader)

    # Final fallback: return any chunks for this user
    if not chunks:
        if LIGHTWEIGHT:
            from core.sparse_retriever import get_user_index
            idx = get_user_index(user_id)
            if idx.chunk_texts:
                chunks = [
                    {"id": idx.chunk_ids[i], "text": idx.chunk_texts[i], "metadata": idx.chunk_metadatas[i], "bm25_score": 1.0}
                    for i in range(min(5, len(idx.chunk_texts)))
                ]

    return chunks


NO_RELEVANCE_MSG = "I cannot answer this from the provided study material. The uploaded documents do not contain relevant information on this topic."


def _calc_confidence(chunks: list[dict]) -> str:
    if not chunks:
        return "low"
    scores = [
        c.get("rerank_score") or c.get("rrf_score") or c.get("fusion_score") or 0
        for c in chunks
    ]
    avg = sum(scores) / len(scores) if scores else 0
    return "high" if avg > 2.0 else "medium" if avg > 0.5 else "low"


def _extract_json(text: str) -> str:
    """Extract JSON from LLM response that might have markdown wrapping."""
    text = text.strip()
    if text.startswith("```json"):
        text = text[7:]
    elif text.startswith("```"):
        text = text[3:]
    if text.endswith("```"):
        text = text[:-3]
    return text.strip()