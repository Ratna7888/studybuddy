"""Progress tracking — stats, streaks, quiz history, weak topics."""

from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc
from pydantic import BaseModel

from db.database import get_db
from models import User, StudySession, QuizAttempt, WeakTopic, Flashcard, Document
from api.auth import get_current_user

router = APIRouter(prefix="/api/progress", tags=["progress"])


# ── Request Schemas ──

class LogSessionRequest(BaseModel):
    topic: str = "General"
    mode: str = "qa"
    duration_sec: int = 0

class LogQuizRequest(BaseModel):
    topic: str
    mode: str
    total_questions: int
    correct_count: int
    score_percent: float
    questions_json: list = []
    document_name: str = ""

class LogFlashcardsRequest(BaseModel):
    topic: str
    count: int


# ── Log Endpoints ──

@router.post("/log-session")
async def log_session(
    req: LogSessionRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    session = StudySession(
        user_id=user.id, topic=req.topic, mode=req.mode, duration_sec=req.duration_sec,
    )
    db.add(session)
    return {"status": "logged"}


@router.post("/log-quiz")
async def log_quiz(
    req: LogQuizRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    attempt = QuizAttempt(
        user_id=user.id, topic=req.topic, mode=req.mode,
        total_questions=req.total_questions, correct_count=req.correct_count,
        score_percent=req.score_percent,
        questions_json={"questions": req.questions_json, "document": req.document_name},
    )
    db.add(attempt)

    # Update weak topics if score < 70%
    if req.score_percent < 70:
        result = await db.execute(
            select(WeakTopic).where(WeakTopic.user_id == user.id, WeakTopic.topic == req.topic)
        )
        weak = result.scalar_one_or_none()
        if weak:
            weak.mistake_count += req.total_questions - req.correct_count
            weak.confidence = req.score_percent / 100.0
            weak.last_seen_at = datetime.now(timezone.utc)
        else:
            db.add(WeakTopic(
                user_id=user.id, topic=req.topic,
                mistake_count=req.total_questions - req.correct_count,
                confidence=req.score_percent / 100.0,
            ))

    return {"status": "logged"}


@router.post("/log-flashcards")
async def log_flashcards(
    req: LogFlashcardsRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    session = StudySession(
        user_id=user.id, topic=req.topic, mode="flashcards", duration_sec=0,
    )
    db.add(session)
    return {"status": "logged", "topic": req.topic, "count": req.count}


# ── Stats Endpoint ──

@router.get("/stats")
async def get_stats(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
    tz_offset: int = 0,
):
    """
    Get user stats. tz_offset is minutes from UTC (e.g. -330 for IST).
    Frontend sends: /progress/stats?tz_offset=-330
    """
    offset_delta = timedelta(minutes=-tz_offset)  # Convert JS offset to Python delta
    now = datetime.now(timezone.utc) + offset_delta  # User's local "now"
    week_ago = now - timedelta(days=7)

    # Total sessions
    total_q = await db.execute(
        select(func.count()).select_from(StudySession).where(StudySession.user_id == user.id)
    )
    total_sessions = total_q.scalar() or 0

    # Sessions this week
    week_q = await db.execute(
        select(func.count()).select_from(StudySession).where(
            StudySession.user_id == user.id, StudySession.created_at >= week_ago
        )
    )
    week_sessions = week_q.scalar() or 0

    # Quiz count + avg score
    qcount_q = await db.execute(
        select(func.count()).select_from(QuizAttempt).where(QuizAttempt.user_id == user.id)
    )
    quiz_count = qcount_q.scalar() or 0

    avg_q = await db.execute(
        select(func.avg(QuizAttempt.score_percent)).where(QuizAttempt.user_id == user.id)
    )
    avg_score = round(avg_q.scalar() or 0, 1)

    # Recent quizzes (last 20)
    rq = await db.execute(
        select(QuizAttempt).where(QuizAttempt.user_id == user.id)
        .order_by(desc(QuizAttempt.created_at)).limit(20)
    )
    recent_quizzes = [
        {
            "id": q.id, "topic": q.topic, "mode": q.mode,
            "score": q.score_percent, "total": q.total_questions,
            "correct": q.correct_count, "date": q.created_at.isoformat(),
            "questions_json": q.questions_json,
        }
        for q in rq.scalars().all()
    ]

    # Topics studied
    tq = await db.execute(
        select(StudySession.topic, StudySession.mode, func.count().label("count"))
        .where(StudySession.user_id == user.id)
        .group_by(StudySession.topic, StudySession.mode)
        .order_by(desc("count")).limit(20)
    )
    topics = [{"topic": r[0], "mode": r[1], "count": r[2]} for r in tq.all()]

    # Weak topics
    wq = await db.execute(
        select(WeakTopic).where(WeakTopic.user_id == user.id)
        .order_by(desc(WeakTopic.mistake_count)).limit(10)
    )
    weak_topics = [
        {"topic": w.topic, "mistakes": w.mistake_count, "confidence": round(w.confidence * 100, 1)}
        for w in wq.scalars().all()
    ]

    # Flashcard sessions count (total flashcards generated from session logs)
    fc_q = await db.execute(
        select(func.count()).select_from(StudySession).where(
            StudySession.user_id == user.id, StudySession.mode == "flashcards"
        )
    )
    flashcard_count = fc_q.scalar() or 0

    # Streak
    streak = 0
    day = now.date()
    while True:
        ds = datetime.combine(day, datetime.min.time()).replace(tzinfo=timezone.utc)
        de = ds + timedelta(days=1)
        cnt = await db.execute(
            select(func.count()).select_from(StudySession).where(
                StudySession.user_id == user.id,
                StudySession.created_at >= ds,
                StudySession.created_at < de,
            )
        )
        if (cnt.scalar() or 0) > 0:
            streak += 1
            day -= timedelta(days=1)
        else:
            break

    # Daily activity (last 7 days)
    daily_activity = []
    for i in range(6, -1, -1):
        d = (now - timedelta(days=i)).date()
        ds = datetime.combine(d, datetime.min.time()).replace(tzinfo=timezone.utc)
        de = ds + timedelta(days=1)
        cnt = await db.execute(
            select(func.count()).select_from(StudySession).where(
                StudySession.user_id == user.id,
                StudySession.created_at >= ds,
                StudySession.created_at < de,
            )
        )
        daily_activity.append({"date": d.isoformat(), "day": d.strftime("%a"), "count": cnt.scalar() or 0})

    # Documents
    dq = await db.execute(
        select(Document.id, Document.title).where(Document.user_id == user.id)
    )
    documents = [{"id": r[0], "title": r[1]} for r in dq.all()]

    return {
        "total_sessions": total_sessions,
        "week_sessions": week_sessions,
        "streak": streak,
        "quiz_count": quiz_count,
        "avg_score": avg_score,
        "flashcard_count": flashcard_count,
        "recent_quizzes": recent_quizzes,
        "topics": topics,
        "weak_topics": weak_topics,
        "daily_activity": daily_activity,
        "documents": documents,
    }


# ── Quiz Detail ──

@router.get("/quiz/{quiz_id}")
async def get_quiz_detail(
    quiz_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(QuizAttempt).where(QuizAttempt.id == quiz_id, QuizAttempt.user_id == user.id)
    )
    q = result.scalar_one_or_none()
    if not q:
        return {"error": "Quiz not found"}
    return {
        "id": q.id, "topic": q.topic, "mode": q.mode,
        "score": q.score_percent, "total": q.total_questions,
        "correct": q.correct_count, "date": q.created_at.isoformat(),
        "questions_json": q.questions_json,
    }