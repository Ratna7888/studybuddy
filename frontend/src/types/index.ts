// ── Auth ──
export interface User {
  id: number;
  email: string;
  name: string;
}

export interface AuthState {
  user: User | null;
  token: string | null;
  isAuthenticated: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, name: string, password: string) => Promise<void>;
  logout: () => void;
  loadFromStorage: () => void;
}

// ── Documents ──
export interface Document {
  id: number;
  title: string;
  file_type: string;
  processing_status: "pending" | "processing" | "ready" | "failed";
  chunk_count: number;
  created_at: string;
}

// ── Chat / RAG ──
export interface Source {
  index: number;
  document_title: string;
  section: string;
  chunk_index: number;
  relevance_score: number;
  text_preview: string;
  full_text: string;
}

export interface ChatResponse {
  answer: string;
  sources: Source[];
  confidence: "high" | "medium" | "low";
  mode: string;
}

// ── Flashcards ──
export interface Flashcard {
  front: string;
  back: string;
  topic: string;
}

export interface FlashcardResponse {
  flashcards: Flashcard[];
  sources: Source[];
  error?: string;
}

// ── Quizzes ──
export interface MCQQuestion {
  question: string;
  options: string[];
  correct_answer: string;
  explanation: string;
  topic: string;
}

export interface TFQuestion {
  statement: string;
  correct_answer: boolean;
  explanation: string;
  topic: string;
}

export interface QuizResponse {
  questions: MCQQuestion[] | TFQuestion[];
  sources: Source[];
  mode: string;
  error?: string;
}

// ── Study Modes ──
export type StudyMode =
  | "qa"
  | "explain"
  | "summary"
  | "flashcards"
  | "quiz_mcq"
  | "quiz_tf"
  | "teach_back"
  | "concept_breakdown";

export interface StudyModeInfo {
  id: StudyMode;
  label: string;
  description: string;
  icon: string;
  color: string;
}