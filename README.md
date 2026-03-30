
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

---

## 🌍 Deployment

### Frontend (Vercel)

* **Root Directory:** `frontend`
* **Build Command:** `npm run build`
* **Output Directory:** `dist`

Set `VITE_API_URL=https://your-backend-url.onrender.com`

### Backend (Render)

* **Root Directory:** `backend`
* **Build Command:** `pip install -r requirements-prod.txt`
* **Start Command:** `uvicorn main:app --host 0.0.0.0 --port $PORT`

---

## 📝 License

MIT

---

