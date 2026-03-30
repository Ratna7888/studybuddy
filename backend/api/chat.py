"""Chat / Tutor interaction routes."""

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from db.database import get_db
from models import User
from api.auth import get_current_user
from core.rag_pipeline import (
    ask_question,
    ask_conversational,
    generate_summary,
    generate_flashcards,
    generate_quiz_mcq,
    generate_quiz_tf,
    concept_breakdown,
)

router = APIRouter(prefix="/api/chat", tags=["chat"])


class QuestionRequest(BaseModel):
    question: str

class ConversationRequest(BaseModel):
    question: str
    history: list[dict] = []
    mode: str = "qa"

class TopicRequest(BaseModel):
    topic: str
    count: int = 5


@router.post("/converse")
async def converse(req: ConversationRequest, user: User = Depends(get_current_user)):
    result = await ask_conversational(
        user_id=user.id, question=req.question, history=req.history, mode=req.mode,
    )
    return {"answer": result.answer, "sources": result.sources, "confidence": result.confidence, "mode": result.mode, "retrieval_info": result.retrieval_info}


@router.post("/ask")
async def ask(req: QuestionRequest, user: User = Depends(get_current_user)):
    result = await ask_question(user.id, req.question)
    return {"answer": result.answer, "sources": result.sources, "confidence": result.confidence, "mode": result.mode, "retrieval_info": result.retrieval_info}


@router.post("/summarize")
async def summarize(req: QuestionRequest, user: User = Depends(get_current_user)):
    result = await generate_summary(user.id, req.question)
    return {"answer": result.answer, "sources": result.sources, "confidence": result.confidence, "mode": result.mode, "retrieval_info": result.retrieval_info}


@router.post("/flashcards")
async def flashcards(req: TopicRequest, user: User = Depends(get_current_user)):
    return await generate_flashcards(user.id, req.topic, req.count)


@router.post("/quiz/mcq")
async def quiz_mcq(req: TopicRequest, user: User = Depends(get_current_user)):
    return await generate_quiz_mcq(user.id, req.topic, req.count)


@router.post("/quiz/tf")
async def quiz_tf(req: TopicRequest, user: User = Depends(get_current_user)):
    return await generate_quiz_tf(user.id, req.topic, req.count)


@router.post("/concept-breakdown")
async def concept_map(req: QuestionRequest, user: User = Depends(get_current_user)):
    return await concept_breakdown(user.id, req.question)