import { useState, useEffect } from "react";
import { progressAPI } from "@/services/api";
import ReactMarkdown from "react-markdown";
import {
  Flame, Trophy, BookOpen, BarChart3, AlertTriangle,
  TrendingUp, Calendar, Brain, CheckCircle2, XCircle,
  ChevronRight, ChevronLeft, Eye, X, HelpCircle, ToggleLeft,
} from "lucide-react";

export default function ProgressPage() {
  const [stats, setStats] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [reviewQuiz, setReviewQuiz] = useState<any>(null);

  useEffect(() => {
    progressAPI.getStats()
      .then(({ data }) => setStats(data))
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <PageSkeleton />;
  if (!stats) return <div style={{ padding: 40, textAlign: "center", color: "var(--text-muted)" }}>Could not load progress data.</div>;

  return (
    <div style={{ padding: "32px 40px", maxWidth: 960, margin: "0 auto", overflowY: "auto", height: "calc(100vh - 56px)" }}>
      <h1 style={{ fontSize: 24, fontWeight: 800, marginBottom: 4 }}>Your Progress</h1>
      <p style={{ fontSize: 14, color: "var(--text-muted)", marginBottom: 28 }}>Track your study activity, quiz scores, and weak areas</p>

      {/* Top Stats */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 14, marginBottom: 24 }}>
        <BigStat icon={<Flame size={22} />} color="#fb923c" value={stats.streak} label="Day Streak" sub={stats.streak > 0 ? "Keep it going!" : "Start studying today"} />
        <BigStat icon={<BarChart3 size={22} />} color="#7c5cfc" value={stats.week_sessions} label="This Week" sub={`${stats.total_sessions} total sessions`} />
        <BigStat icon={<Trophy size={22} />} color="#60a5fa" value={`${stats.avg_score}%`} label="Avg Quiz Score" sub={`${stats.quiz_count} quizzes taken`} />
        <BigStat icon={<BookOpen size={22} />} color="#f472b6" value={stats.flashcard_count} label="Flashcards" sub="Cards generated" />
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 14, marginBottom: 24 }}>
        {/* Weekly Activity */}
        <Card title="Weekly Activity" icon={<Calendar size={16} color="var(--accent)" />}>
          <div style={{ display: "flex", gap: 8, alignItems: "end", height: 120 }}>
            {stats.daily_activity?.map((d: any, i: number) => {
              const max = Math.max(...stats.daily_activity.map((x: any) => x.count), 1);
              const h = Math.max((d.count / max) * 100, 6);
              return <div key={i} style={{ flex: 1, display: "flex", flexDirection: "column", alignItems: "center", gap: 6 }}>
                <span style={{ fontSize: 11, fontWeight: 600, color: d.count > 0 ? "var(--text-primary)" : "var(--text-muted)" }}>{d.count}</span>
                <div style={{ width: "100%", height: h, borderRadius: 6, background: d.count > 0 ? "var(--accent)" : "var(--border)", transition: "height 0.5s" }} />
                <span style={{ fontSize: 11, color: "var(--text-muted)" }}>{d.day}</span>
              </div>;
            })}
          </div>
        </Card>

        {/* Weak Topics */}
        <Card title="Weak Topics" icon={<AlertTriangle size={16} color="var(--warning)" />}>
          {stats.weak_topics?.length > 0 ? stats.weak_topics.map((w: any, i: number) => (
            <div key={i} style={{ marginBottom: 10 }}>
              <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 4 }}>
                <span style={{ fontSize: 13, fontWeight: 500 }}>{w.topic}</span>
                <span style={{ fontSize: 12, color: w.confidence < 50 ? "var(--danger)" : "var(--warning)", fontWeight: 600 }}>{w.confidence}%</span>
              </div>
              <div style={{ height: 6, borderRadius: 3, background: "var(--border)", overflow: "hidden" }}>
                <div style={{ height: "100%", borderRadius: 3, width: `${w.confidence}%`, background: w.confidence < 40 ? "var(--danger)" : w.confidence < 70 ? "var(--warning)" : "var(--success)", transition: "width 0.5s" }} />
              </div>
              <span style={{ fontSize: 10, color: "var(--text-muted)" }}>{w.mistakes} mistakes</span>
            </div>
          )) : <Empty text="Take quizzes to track weak areas" />}
        </Card>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 14, marginBottom: 24 }}>
        {/* Topics */}
        <Card title="Topics Studied" icon={<Brain size={16} color="#e879f9" />}>
          {stats.topics?.length > 0 ? (
            <div style={{ display: "flex", flexWrap: "wrap", gap: 6 }}>
              {stats.topics.map((t: any, i: number) => (
                <span key={i} style={{
                  padding: "4px 12px", borderRadius: 20, fontSize: i < 3 ? 13 : 11, fontWeight: 500,
                  background: i < 3 ? "var(--accent-light)" : "var(--bg-secondary)",
                  color: i < 3 ? "var(--accent)" : "var(--text-secondary)",
                  border: "1px solid var(--border)",
                }}>
                  {t.topic} <span style={{ fontSize: 10, opacity: 0.5 }}>×{t.count} · {t.mode}</span>
                </span>
              ))}
            </div>
          ) : <Empty text="Start studying to see topics" />}
        </Card>

        {/* Documents reference */}
        <Card title="Your Documents" icon={<BookOpen size={16} color="#34d399" />}>
          {stats.documents?.length > 0 ? (
            <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
              {stats.documents.map((d: any) => (
                <div key={d.id} style={{ display: "flex", alignItems: "center", gap: 8, padding: "6px 10px", background: "var(--bg-secondary)", borderRadius: 6, border: "1px solid var(--border)" }}>
                  <BookOpen size={14} color="#34d399" />
                  <span style={{ fontSize: 12, color: "var(--text-primary)" }}>{d.title}</span>
                </div>
              ))}
            </div>
          ) : <Empty text="Upload documents to get started" />}
        </Card>
      </div>

      {/* Quiz History — Full review */}
      <Card title="Quiz History" icon={<TrendingUp size={16} color="#60a5fa" />} full>
        {stats.recent_quizzes?.length > 0 ? (
          <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
            {stats.recent_quizzes.map((q: any) => (
              <div key={q.id} style={{
                display: "flex", alignItems: "center", gap: 12, padding: "12px 14px",
                background: "var(--bg-secondary)", borderRadius: 10, border: "1px solid var(--border)",
              }}>
                <div style={{
                  width: 40, height: 40, borderRadius: 10, display: "flex", alignItems: "center", justifyContent: "center",
                  background: q.score >= 70 ? "rgba(52,211,153,0.15)" : "rgba(248,113,113,0.15)",
                }}>
                  {q.score >= 70 ? <CheckCircle2 size={20} color="var(--success)" /> : <AlertTriangle size={20} color="var(--danger)" />}
                </div>
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div style={{ fontSize: 14, fontWeight: 600, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{q.topic}</div>
                  <div style={{ fontSize: 11, color: "var(--text-muted)", display: "flex", gap: 8, marginTop: 2 }}>
                    <span>{q.mode === "mcq" ? "MCQ" : "T/F"}</span>
                    <span>·</span>
                    <span>{q.correct}/{q.total} correct</span>
                    <span>·</span>
                    <span>{new Date(q.date).toLocaleDateString()}</span>
                    {q.questions_json?.document && <>
                      <span>·</span>
                      <span style={{ color: "#34d399" }}>{q.questions_json.document}</span>
                    </>}
                  </div>
                </div>
                <div style={{ fontSize: 20, fontWeight: 800, color: q.score >= 70 ? "var(--success)" : "var(--danger)", marginRight: 8 }}>{q.score}%</div>
                <button onClick={() => setReviewQuiz(q)} style={{
                  padding: "6px 12px", borderRadius: 6, border: "1px solid var(--border)",
                  background: "var(--bg-card)", color: "var(--accent)", cursor: "pointer", fontSize: 11,
                  display: "flex", alignItems: "center", gap: 4, fontWeight: 600,
                }}>
                  <Eye size={12} /> Review
                </button>
              </div>
            ))}
          </div>
        ) : <Empty text="Take a quiz to see your history" />}
      </Card>

      {/* Quiz Review Modal */}
      {reviewQuiz && <QuizReviewModal quiz={reviewQuiz} onClose={() => setReviewQuiz(null)} />}
    </div>
  );
}

// ── Quiz Review Modal ──
function QuizReviewModal({ quiz, onClose }: { quiz: any; onClose: () => void }) {
  const questions = quiz.questions_json?.questions || quiz.questions_json || [];
  const isTF = quiz.mode === "tf";

  return (
    <div style={{
      position: "fixed", inset: 0, zIndex: 100, background: "rgba(0,0,0,0.6)",
      display: "flex", alignItems: "center", justifyContent: "center", padding: 20,
    }} onClick={onClose}>
      <div onClick={e => e.stopPropagation()} style={{
        width: "100%", maxWidth: 640, maxHeight: "80vh", overflowY: "auto",
        background: "var(--bg-card)", border: "1px solid var(--border)", borderRadius: 16, padding: 24,
      }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 20 }}>
          <div>
            <h2 style={{ fontSize: 18, fontWeight: 700, margin: 0 }}>Quiz Review: {quiz.topic}</h2>
            <p style={{ fontSize: 12, color: "var(--text-muted)", marginTop: 2 }}>
              {quiz.mode === "mcq" ? "Multiple Choice" : "True/False"} · {quiz.correct}/{quiz.total} correct · {quiz.score}%
              {quiz.questions_json?.document && <> · <span style={{ color: "#34d399" }}>{quiz.questions_json.document}</span></>}
            </p>
          </div>
          <button onClick={onClose} style={{ background: "none", border: "none", cursor: "pointer", color: "var(--text-muted)", padding: 4 }}><X size={20} /></button>
        </div>

        {questions.length > 0 ? questions.map((q: any, i: number) => (
          <div key={i} style={{ background: "var(--bg-secondary)", border: "1px solid var(--border)", borderRadius: 10, padding: 16, marginBottom: 10 }}>
            <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 8 }}>
              {isTF ? <ToggleLeft size={14} color="#a78bfa" /> : <HelpCircle size={14} color="#60a5fa" />}
              <span style={{ fontSize: 13, fontWeight: 600 }}>{i + 1}. {isTF ? q.statement : q.question}</span>
            </div>
            {!isTF && q.options?.map((opt: string, j: number) => {
              const letter = opt.charAt(0);
              const isCorrect = letter === q.correct_answer;
              return <div key={j} style={{
                padding: "6px 12px", borderRadius: 6, marginBottom: 3, fontSize: 12,
                background: isCorrect ? "rgba(52,211,153,0.1)" : "transparent",
                border: `1px solid ${isCorrect ? "var(--success)" : "var(--border)"}`,
                display: "flex", alignItems: "center", gap: 6,
              }}>
                {isCorrect && <CheckCircle2 size={12} color="var(--success)" />}
                {opt}
              </div>;
            })}
            {isTF && (
              <div style={{ fontSize: 12, color: "var(--text-secondary)", marginBottom: 4 }}>
                Answer: <span style={{ fontWeight: 600, color: "var(--success)" }}>{String(q.correct_answer)}</span>
              </div>
            )}
            {q.explanation && (
              <div style={{ marginTop: 8, padding: "8px 12px", background: "var(--bg-card)", borderRadius: 6, borderLeft: "3px solid var(--accent)" }}>
                <p style={{ fontSize: 11, color: "var(--text-secondary)", lineHeight: 1.5, margin: 0 }}>{q.explanation}</p>
              </div>
            )}
          </div>
        )) : <p style={{ fontSize: 13, color: "var(--text-muted)", textAlign: "center", padding: 20 }}>No question details saved for this quiz.</p>}
      </div>
    </div>
  );
}

// ── Sub-components ──
function BigStat({ icon, color, value, label, sub }: { icon: React.ReactNode; color: string; value: string | number; label: string; sub: string }) {
  return <div style={{ background: "var(--bg-card)", border: "1px solid var(--border)", borderRadius: 14, padding: "18px 16px" }}>
    <div style={{ width: 40, height: 40, borderRadius: 10, marginBottom: 12, background: `${color}18`, display: "flex", alignItems: "center", justifyContent: "center", color }}>{icon}</div>
    <div style={{ fontSize: 26, fontWeight: 800, lineHeight: 1 }}>{value}</div>
    <div style={{ fontSize: 13, fontWeight: 600, color: "var(--text-secondary)", marginTop: 4 }}>{label}</div>
    <div style={{ fontSize: 11, color: "var(--text-muted)", marginTop: 2 }}>{sub}</div>
  </div>;
}

function Card({ title, icon, children, full }: { title: string; icon: React.ReactNode; children: React.ReactNode; full?: boolean }) {
  return <div style={{ background: "var(--bg-card)", border: "1px solid var(--border)", borderRadius: 14, padding: 20, gridColumn: full ? "1 / -1" : undefined, marginBottom: full ? 24 : 0 }}>
    <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 16 }}>{icon}<h3 style={{ fontSize: 14, fontWeight: 700, margin: 0 }}>{title}</h3></div>
    {children}
  </div>;
}

function Empty({ text }: { text: string }) {
  return <p style={{ fontSize: 13, color: "var(--text-muted)", textAlign: "center", padding: 20 }}>{text}</p>;
}

function PageSkeleton() {
  return <div style={{ padding: 40, maxWidth: 900, margin: "0 auto" }}>
    <div className="skeleton" style={{ height: 32, width: "30%", marginBottom: 24 }} />
    <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 16 }}>
      {[1, 2, 3, 4].map(i => <div key={i} className="skeleton" style={{ height: 100, borderRadius: 12 }} />)}
    </div>
    <div className="skeleton" style={{ height: 200, marginTop: 24, borderRadius: 12 }} />
  </div>;
}