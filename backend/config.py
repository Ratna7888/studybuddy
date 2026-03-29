"""Application configuration loaded from environment variables."""

from pydantic_settings import BaseSettings
from pathlib import Path


class Settings(BaseSettings):
    # ── API Keys ──
    gemini_api_key: str = ""

    # ── Auth ──
    jwt_secret: str = "change-me"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60 * 24 * 7  # 7 days

    # ── Database ──
    database_url: str = "sqlite+aiosqlite:///./studybuddy.db"

    # ── ChromaDB ──
    chroma_persist_dir: str = "./chroma_data"

    # ── Models (local, free) ──
    embedding_model: str = "all-MiniLM-L6-v2"
    reranker_model: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"

    # ── File Upload ──
    upload_dir: str = "./uploads"
    max_file_size_mb: int = 50
    allowed_extensions: list[str] = ["pdf", "txt", "md", "docx"]

    # ── RAG Pipeline ──
    rag_top_k: int = 10
    rag_rerank_top_k: int = 5
    chunk_size: int = 512
    chunk_overlap: int = 50
    relevance_threshold: float = 0.3

    # ── Hybrid Retrieval ──
    retrieval_mode: str = "hybrid"       # hybrid, sparse, dense
    fusion_method: str = "rrf"           # rrf, weighted
    sparse_weight: float = 0.4
    dense_weight: float = 0.6
    sparse_top_k: int = 15
    dense_top_k: int = 15
    fusion_top_k: int = 10
    final_top_k: int = 5
    use_reranker: bool = True

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()

# Ensure directories exist
Path(settings.upload_dir).mkdir(parents=True, exist_ok=True)
Path(settings.chroma_persist_dir).mkdir(parents=True, exist_ok=True)