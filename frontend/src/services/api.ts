import axios from "axios";

// In production, call Render backend directly
// In dev, Vite proxy handles /api -> localhost:8000
const isProd = window.location.hostname !== "localhost";
const BASE_URL = isProd
  ? "https://studybuddy-api-uy9l.onrender.com/api"  // ← Replace with YOUR Render URL
  : "/api";

const api = axios.create({
  baseURL: BASE_URL,
  headers: { "Content-Type": "application/json" },
});

// Attach JWT token to every request
api.interceptors.request.use((config) => {
  const token = localStorage.getItem("token");
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Handle 401 globally
api.interceptors.response.use(
  (res) => res,
  (err) => {
    if (err.response?.status === 401) {
      localStorage.removeItem("token");
      localStorage.removeItem("user");
      window.location.href = "/login";
    }
    return Promise.reject(err);
  }
);

// ── Auth ──
export const authAPI = {
  register: (email: string, name: string, password: string) =>
    api.post("/auth/register", { email, name, password }),
  login: (email: string, password: string) =>
    api.post("/auth/login", { email, password }),
  me: () => api.get("/auth/me"),
};

// ── Documents ──
export const documentsAPI = {
  upload: (file: File) => {
    const form = new FormData();
    form.append("file", file);
    return api.post("/documents/upload", form, {
      headers: { "Content-Type": "multipart/form-data" },
    });
  },
  list: () => api.get("/documents"),
  get: (id: number) => api.get(`/documents/${id}`),
  delete: (id: number) => api.delete(`/documents/${id}`),
};

// ── Chat / Tutor ──
export const chatAPI = {
  converse: (question: string, history: { role: string; content: string }[], mode: string, doc_ids: number[] = []) =>
    api.post("/chat/converse", { question, history, mode, doc_ids }),
  ask: (question: string, doc_ids: number[] = []) =>
    api.post("/chat/ask", { question, doc_ids }),
  summarize: (question: string, doc_ids: number[] = []) =>
    api.post("/chat/summarize", { question, doc_ids }),
  flashcards: (topic: string, count = 5, doc_ids: number[] = []) =>
    api.post("/chat/flashcards", { topic, count, doc_ids }),
  quizMCQ: (topic: string, count = 5, doc_ids: number[] = []) =>
    api.post("/chat/quiz/mcq", { topic, count, doc_ids }),
  quizTF: (topic: string, count = 5, doc_ids: number[] = []) =>
    api.post("/chat/quiz/tf", { topic, count, doc_ids }),
  conceptBreakdown: (question: string, doc_ids: number[] = []) =>
    api.post("/chat/concept-breakdown", { question, doc_ids }),
};

// ── Progress ──
export const progressAPI = {
  getStats: () => {
    const tzOffset = new Date().getTimezoneOffset(); // minutes from UTC
    return api.get(`/progress/stats?tz_offset=${tzOffset}`);
  },
  getQuizDetail: (id: number) => api.get(`/progress/quiz/${id}`),
  logSession: (topic: string, mode: string, duration_sec = 0) =>
    api.post("/progress/log-session", { topic, mode, duration_sec }),
  logQuiz: (topic: string, mode: string, total_questions: number, correct_count: number, score_percent: number, questions_json: any[] = [], document_name = "") =>
    api.post("/progress/log-quiz", { topic, mode, total_questions, correct_count, score_percent, questions_json, document_name }),
  logFlashcards: (topic: string, count: number) =>
    api.post("/progress/log-flashcards", { topic, count }),
};

export default api;