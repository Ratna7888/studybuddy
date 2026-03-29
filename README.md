# 🎓 StudyBuddy AI

A RAG-based personal tutor that answers **only** from your uploaded documents. Upload PDFs, DOCX, TXT, or Markdown files and study with AI-powered tools.

## Features

- **Q&A Chat** — Conversational AI grounded in your documents
- **Flashcards** — Auto-generated question-answer cards
- **MCQ Quiz** — Multiple choice questions with scoring
- **True/False Quiz** — Quick knowledge checks
- **Concept Breakdown** — Topic decomposition with key terms
- **Progress Tracking** — Streaks, quiz scores, weak topics, study history
- **Source Transparency** — Every answer shows which document chunks were used
- **Anti-Hallucination** — Refuses to answer outside your uploaded material

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | React + Vite + TypeScript + Tailwind CSS |
| Backend | FastAPI + Python |
| LLM | Google Gemini (free tier) |
| Embeddings | sentence-transformers (local) |
| Vector DB | ChromaDB (local) |
| Sparse Search | BM25 (rank-bm25) |
| Reranker | Cross-encoder (local) |
| Database | SQLite via SQLAlchemy |
| Auth | JWT |

## Architecture

**Hybrid RAG Pipeline:**
```
Query → BM25 Sparse Search ─┐
                             ├→ Reciprocal Rank Fusion → Cross-Encoder Reranker → Gemini LLM → Grounded Answer
Query → Dense Embedding Search ┘
```

## Setup

### Prerequisites
- Python 3.11+
- Node.js 18+
- Free Gemini API key from https://aistudio.google.com/apikey

### Backend

```bash
cd backend
python -m venv venv
# Windows: venv\Scripts\activate
# Mac/Linux: source venv/bin/activate
pip install -r requirements.txt
# Add your Gemini API key to .env
uvicorn main:app --reload
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:5173 — backend runs on http://localhost:8000.

## Environment Variables

Create `backend/.env`:
```
GEMINI_API_KEY=your_key_here
JWT_SECRET=your_random_secret
DATABASE_URL=sqlite+aiosqlite:///./studybuddy.db
```

## License

MIT