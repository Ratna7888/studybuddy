"""Chat / Tutor interaction routes — conversational + structured modes."""

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from db.database import get_db
from models import User
from api.auth import get_current_user
from core.rag_pipeline import (
    ask_question,
    ask_conversational,
    generate_flashcards,
    generate_quiz_mcq,
    generate_quiz_tf,
    concept_breakdown,
)

router = APIRouter(prefix="/api/chat", tags=["chat"])


# ── Request Schemas ──

class QuestionRequest(BaseModel):
    question: str
    retrieval_mode: str = "hybrid"

class ConversationRequest(BaseModel):
    question: str
    history: list[dict] = []  # [{"role": "user"|"assistant", "content": "..."}]
    mode: str = "qa"          # qa, explain, teach_back
    retrieval_mode: str = "hybrid"

class TopicRequest(BaseModel):
    topic: str
    count: int = 5
    retrieval_mode: str = "hybrid"




# ── Conversational endpoint (Q&A, Explain, Teach Back) ──

@router.post("/converse")
async def converse(req: ConversationRequest, user: User = Depends(get_current_user)):
    """Multi-turn conversation with RAG grounding."""
    config = _get_config(req.retrieval_mode)
    result = await ask_conversational(
        user_id=user.id,
        question=req.question,
        history=req.history,
        mode=req.mode,
        config=config,
    )
    return {
        "answer": result.answer,
        "sources": result.sources,
        "confidence": result.confidence,
        "mode": result.mode,
        "retrieval_info": result.retrieval_info,
    }


# ── Legacy single-shot (still useful for structured modes) ──

@router.post("/ask")
async def ask(req: QuestionRequest, user: User = Depends(get_current_user)):
    config = _get_config(req.retrieval_mode)
    result = await ask_question(user.id, req.question, config)
    return {
        "answer": result.answer,
        "sources": result.sources,
        "confidence": result.confidence,
        "mode": result.mode,
        "retrieval_info": result.retrieval_info,
    }

@router.post("/flashcards")
async def flashcards(req: TopicRequest, user: User = Depends(get_current_user)):
    """Generate flashcards from a topic."""
    result = await generate_flashcards(user.id, req.topic, req.count)
    return result


@router.post("/quiz/mcq")
async def quiz_mcq(req: TopicRequest, user: User = Depends(get_current_user)):
    """Generate MCQ quiz."""
    result = await generate_quiz_mcq(user.id, req.topic, req.count)
    return result


@router.post("/quiz/tf")
async def quiz_tf(req: TopicRequest, user: User = Depends(get_current_user)):
    """Generate True/False quiz."""
    result = await generate_quiz_tf(user.id, req.topic, req.count)
    return result

@router.post("/concept-breakdown")
async def concept_map(req: QuestionRequest, user: User = Depends(get_current_user)):
    """Break down a topic into concepts."""
    result = await concept_breakdown(user.id, req.question)
    return result