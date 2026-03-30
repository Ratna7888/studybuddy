
# 🎓 StudyBuddy AI

A RAG-based personal tutor that answers **only** from your uploaded documents. Upload PDFs, DOCX, TXT, or Markdown files and study with AI-powered tools.

---

## 🚀 Features

* **Q&A Chat** — Conversational AI grounded in your documents
* **Concept Breakdown** — Topic decomposition with key terms
* **Progress Tracking** — Study activity and learning insights
* **Source Transparency** — Answers are generated from retrieved document chunks
* **Anti-Hallucination** — Refuses to answer outside your uploaded material
* **User Authentication** — Secure JWT-based signup and login
* **Production Lightweight Mode** — BM25-only retrieval for low-memory deployment
* **Document Upload Support** — PDF, DOCX, TXT, and Markdown files

---

## 🛠 Tech Stack

| Layer | Technology |
| :--- | :--- |
| **Frontend** | React + Vite + TypeScript |
| **Backend** | FastAPI + Python |
| **LLM** | Google Gemini API |
| **Retrieval (Local Dev)** | Hybrid RAG |
| **Retrieval (Production)** | BM25-only lightweight retrieval |
| **Sparse Search** | BM25 (`rank-bm25`) |
| **Database** | PostgreSQL |
| **ORM** | SQLAlchemy Async |
| **Auth** | JWT |
| **Deployment** | Vercel (Frontend), Render (Backend) |

---

## 🏗 Architecture

**Local Development (Full Pipeline):**

```text
Query --> BM25 Sparse Search -----┐
                                  |
                                  ├--> Reciprocal Rank Fusion --> Gemini LLM --> Grounded Answer
                                  |
Query --> Dense Retrieval --------┘
```

**Production (Lightweight Mode):**

```text
Query --> BM25 Search --> Retrieved Chunks --> Gemini LLM --> Grounded Answer
```

---

## ⚙️ Setup

### Prerequisites

* Python 3.11+
* Node.js 18+
* Gemini API key from [AI Studio](https://aistudio.google.com/apikey)
* PostgreSQL database URL

### Backend
```bash
cd backend
python -m venv venv
# Windows: venv\Scripts\activate
# Mac/Linux: source venv/bin/activate

pip install -r requirements.txt
uvicorn main:app --reload
```

### Frontend
```bash
cd frontend
npm install
npm run dev
```
Open `http://localhost:5173` — backend runs on `http://localhost:8000`.

---

## Environment Variables

### Create `backend/.env`:
```env
GEMINI_API_KEY=your_key_here
JWT_SECRET=your_random_secret
JWT_ALGORITHM=HS256
JWT_EXPIRE_MINUTES=60

DATABASE_URL=postgresql+asyncpg://user:password@host:port/dbname

FRONTEND_URL=http://localhost:5173

# Optional: set true in production on Render
LIGHTWEIGHT_MODE=false
```

### Create `frontend/.env`:
```env
VITE_API_URL=http://localhost:8000
```

---

## 🌍 Deployment

### Frontend (Vercel)
* **Root Directory:** `frontend`
* **Build Command:** `npm run build`
* **Output Directory:** `dist`

**Set:**
```env
VITE_API_URL=https://your-backend-url.onrender.com
```

### Backend (Render)
* **Root Directory:** `backend`
* **Build Command:** `pip install -r requirements-prod.txt`
* **Start Command:** `uvicorn main:app --host 0.0.0.0 --port $PORT`

**Set these environment variables on Render:**
```env
GEMINI_API_KEY=your_key_here
JWT_SECRET=your_random_secret
JWT_ALGORITHM=HS256
JWT_EXPIRE_MINUTES=60
DATABASE_URL=postgresql+asyncpg://user:password@host:port/dbname
FRONTEND_URL=https://your-frontend-url.vercel.app
LIGHTWEIGHT_MODE=true
```

---

## Lightweight Production Mode

The deployed version is optimized for low-memory environments such as Render free instances.

**What changes in production:**

| | Local Dev | Production (Render) |
| :--- | :--- | :--- |
| **Retrieval** | Hybrid pipeline | BM25 only |
| **Memory Usage** | Higher | Lower |
| **Dependencies** | `requirements.txt` | `requirements-prod.txt` |
| **LIGHTWEIGHT_MODE** | `false` / unset | `true` |

**In lightweight mode:**
* Local embedding models are skipped
* ChromaDB is skipped
* Reranking is skipped
* Retrieval uses only BM25
* Gemini is still used for answer generation

This makes deployment much more stable on small instances while still keeping document-grounded Q&A effective.

---

## Notes
* First request may be slow due to Render cold start
* Production uses **BM25-only retrieval** for memory efficiency
* PostgreSQL is used in production with async SQLAlchemy
* Make sure CORS is configured for your frontend domain
* Use `requirements-prod.txt` on Render, not local dev requirements

## Future Improvements
* Re-enable hybrid retrieval on larger production instances
* Flashcards and quiz generation
* Streaming AI responses
* Better UI/UX
* Multi-document reasoning improvements

## 📝 License
MIT

---

