"""StudyBuddy AI — FastAPI Application Entry Point (Hybrid RAG)."""

from contextlib import asynccontextmanager
import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from db.database import init_db, async_session
from sqlalchemy import select


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup: create DB tables + rebuild BM25 indices."""
    print("Starting StudyBuddy AI...")
    await init_db()
    print("Database initialized.")

    # Rebuild BM25 indices for all users who have documents
    await _rebuild_all_bm25_indices()

    yield
    print("Shutting down StudyBuddy AI.")


async def _rebuild_all_bm25_indices():
    """Rebuild BM25 in-memory indices from DB on startup."""
    from models import User, Document
    from core.sparse_retriever import rebuild_bm25_index
    async with async_session() as db:
        # Find all users who have at least one ready document
        result = await db.execute(
            select(User.id).where(
                User.id.in_(
                    select(Document.user_id).where(Document.processing_status == "ready")
                )
            )
        )
        user_ids = [row[0] for row in result.all()]

        for uid in user_ids:
            await rebuild_bm25_index(uid, db)

    if user_ids:
        print(f"BM25 indices rebuilt for {len(user_ids)} user(s).")
    else:
        print("No documents found — BM25 indices empty.")


app = FastAPI(
    title="StudyBuddy AI",
    description="Hybrid RAG Personal Tutor API (BM25 + Dense + RRF)",
    version="2.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)
# ── Register Routers ──
from api.auth import router as auth_router
from api.documents import router as documents_router
from api.chat import router as chat_router
from api.progress import router as progress_router

app.include_router(auth_router)
app.include_router(documents_router)
app.include_router(chat_router)
app.include_router(progress_router)


@app.get("/")
async def root():
    return {
        "message": "StudyBuddy AI API is running",
        "version": "2.0.0",
        "retrieval": "Hybrid (BM25 + Dense + RRF + Reranker)",
    }


@app.get("/health")
async def health():
    return {"status": "healthy"}
