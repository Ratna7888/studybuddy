import { useState, useEffect, useRef, useCallback } from "react";
import { chatAPI, documentsAPI, progressAPI } from "@/services/api";
import type { StudyMode, Source, Flashcard, MCQQuestion, Document } from "@/types";
import toast from "react-hot-toast";
import ReactMarkdown from "react-markdown";
import {
  MessageSquare, BookOpen, HelpCircle, Send, Loader2, ChevronRight,
  Layers, ToggleLeft, CheckCircle2, XCircle, FileCheck, ChevronDown,
  Zap, Target, Network, User, Bot, Plus, Trash2, Clock,
} from "lucide-react";

interface ChatMessage { role: "user" | "assistant"; content: string; sources?: Source[]; confidence?: string }
interface ChatSession { id: string; title: string; messages: ChatMessage[]; sources: Source[]; createdAt: number }
interface ToolSession { id: string; type: ActiveView; title: string; data: any; sources: Source[]; createdAt: number }

type ActiveView = "chat" | "flashcards" | "quiz_mcq" | "quiz_tf" | "concept_breakdown";

const TOOLS: { id: ActiveView; label: string; icon: React.ReactNode; color: string; desc: string; tagline: string; tips: string[] }[] = [
  { id: "flashcards", label: "Flashcards", icon: <BookOpen size={18} />, color: "#f472b6", desc: "Generate cards", tagline: "Generate flashcards to test yourself", tips: ["Creates question-answer pairs", "Click cards to flip", "Great for memorization"] },
  { id: "quiz_mcq", label: "MCQ Quiz", icon: <HelpCircle size={18} />, color: "#60a5fa", desc: "Multiple choice", tagline: "Test with multiple choice questions", tips: ["5 questions per topic", "Submit to see score", "Explanations included"] },
  { id: "quiz_tf", label: "True / False", icon: <ToggleLeft size={18} />, color: "#a78bfa", desc: "True or false", tagline: "Quick true or false challenge", tips: ["Fast knowledge check", "Great for review", "Explanations included"] },
  { id: "concept_breakdown", label: "Concepts", icon: <Layers size={18} />, color: "#e879f9", desc: "Break it down", tagline: "Break any topic into subtopics", tips: ["Decomposes complex topics", "Key terms & connections", "Great for mental models"] },
];

const genId = () => Date.now().toString(36) + Math.random().toString(36).slice(2, 6);

export default function StudyWorkspace() {
  const [view, setView] = useState<ActiveView>("chat");
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);

  // Chat
  const [sessions, setSessions] = useState<ChatSession[]>([]);
  const [activeSessionId, setActiveSessionId] = useState<string | null>(null);
  const chatEndRef = useRef<HTMLDivElement>(null);

  // Tool sessions history
  const [toolSessions, setToolSessions] = useState<ToolSession[]>([]);
  const [activeToolSessionId, setActiveToolSessionId] = useState<string | null>(null);

  // Study tools
  const [flashcards, setFlashcards] = useState<Flashcard[]>([]);
  const [quizQuestions, setQuizQuestions] = useState<MCQQuestion[]>([]);
  const [conceptData, setConceptData] = useState<any>(null);
  const [toolError, setToolError] = useState<string | null>(null);
  const [sources, setSources] = useState<Source[]>([]);
  const [expandedSource, setExpandedSource] = useState<number | null>(null);
  const [cardIndex, setCardIndex] = useState(0);
  const [flipped, setFlipped] = useState(false);
  const [quizAnswers, setQuizAnswers] = useState<Record<number, string>>({});
  const [quizSubmitted, setQuizSubmitted] = useState(false);

  // Docs
  const [docs, setDocs] = useState<Document[]>([]);
  const [selectedDocIds, setSelectedDocIds] = useState<Set<number>>(new Set());
  const [showDocPicker, setShowDocPicker] = useState(false);

  useEffect(() => {
    documentsAPI.list().then(({ data }) => {
      const ready = data.filter((d: Document) => d.processing_status === "ready");
      setDocs(ready);
      setSelectedDocIds(new Set(ready.map((d: Document) => d.id)));
    }).catch(() => {});
  }, []);

  const activeSession = sessions.find(s => s.id === activeSessionId);
  const messages = activeSession?.messages || [];

  useEffect(() => { chatEndRef.current?.scrollIntoView({ behavior: "smooth" }); }, [messages, loading]);

  // When switching to a tool, clear tool state but NOT chat sessions
  useEffect(() => {
    if (view !== "chat") {
      setFlashcards([]); setQuizQuestions([]); setConceptData(null); setToolError(null);
      setQuizAnswers({}); setQuizSubmitted(false); setCardIndex(0); setFlipped(false);
      setSources([]);
    } else {
      // Restore sources from active session
      const s = sessions.find(s => s.id === activeSessionId);
      setSources(s?.sources || []);
    }
  }, [view]);

  const selectSession = (id: string) => {
    setActiveSessionId(id);
    setView("chat");
    setSources(sessions.find(s => s.id === id)?.sources || []);
  };

  const createNewSession = useCallback(() => {
    const s: ChatSession = { id: genId(), title: "New chat", messages: [], sources: [], createdAt: Date.now() };
    setSessions(prev => [s, ...prev]);
    setActiveSessionId(s.id);
    setView("chat");
    setSources([]);
  }, []);

  const deleteSession = (id: string) => {
    setSessions(prev => prev.filter(s => s.id !== id));
    if (activeSessionId === id) {
      const rest = sessions.filter(s => s.id !== id);
      setActiveSessionId(rest[0]?.id || null);
    }
  };

  const updateSession = (id: string, upd: Partial<ChatSession>) => {
    setSessions(prev => prev.map(s => s.id === id ? { ...s, ...upd } : s));
  };

  const toggleDoc = (id: number) => setSelectedDocIds(p => { const n = new Set(p); n.has(id) ? n.delete(id) : n.add(id); return n; });
  const hasToolContent = flashcards.length > 0 || quizQuestions.length > 0 || conceptData || toolError;

  const loadToolSession = (ts: ToolSession) => {
    setView(ts.type);
    setActiveToolSessionId(ts.id);
    setSources(ts.sources);
    setToolError(null);
    setFlashcards([]); setQuizQuestions([]); setConceptData(null);
    setQuizAnswers({}); setQuizSubmitted(false); setCardIndex(0); setFlipped(false);
    if (ts.type === "flashcards") setFlashcards(ts.data.flashcards || []);
    else if (ts.type === "quiz_mcq" || ts.type === "quiz_tf") setQuizQuestions(ts.data.questions || []);
    else if (ts.type === "concept_breakdown") setConceptData(ts.data);
  };

  const deleteToolSession = (id: string) => {
    setToolSessions(prev => prev.filter(s => s.id !== id));
    if (activeToolSessionId === id) setActiveToolSessionId(null);
  };

  const handleSubmit = async () => {
    if (!input.trim() || loading) return;
    if (selectedDocIds.size === 0) { toast.error("Select at least one document"); return; }
    const query = input.trim();
    setInput("");
    setLoading(true);

    if (view === "chat") {
      let sid = activeSessionId;
      if (!sid) {
        const s: ChatSession = { id: genId(), title: query.slice(0, 40), messages: [], sources: [], createdAt: Date.now() };
        setSessions(prev => [s, ...prev]);
        sid = s.id;
        setActiveSessionId(sid);
      }
      const userMsg: ChatMessage = { role: "user", content: query };
      const prev = sessions.find(s => s.id === sid)?.messages || [];
      const updated = [...prev, userMsg];
      updateSession(sid, { messages: updated, title: prev.length === 0 ? query.slice(0, 40) : undefined });

      try {
        const history = updated.map(m => ({ role: m.role, content: m.content }));
        const { data } = await chatAPI.converse(query, history, "qa");
        const aMsg: ChatMessage = { role: "assistant", content: data.answer, sources: data.sources, confidence: data.confidence };
        updateSession(sid, { messages: [...updated, aMsg], sources: data.sources || [] });
        setSources(data.sources || []);
        const docName = data.sources?.[0]?.document_title || "";
        progressAPI.logSession(query.slice(0, 60) + (docName ? ` [${docName}]` : ""), "qa").catch(() => {});
      } catch (err: any) {
        updateSession(sid, { messages: [...updated, { role: "assistant", content: "Something went wrong. Please try again." }] });
        toast.error(err.response?.data?.detail || "Request failed");
      }
    } else {
      setFlashcards([]); setQuizQuestions([]); setConceptData(null); setToolError(null);
      setSources([]); setQuizAnswers({}); setQuizSubmitted(false); setCardIndex(0); setFlipped(false);
      try {
        let data: any;
        switch (view) {
          case "flashcards":
            data = (await chatAPI.flashcards(query, 5)).data;
            data.error ? setToolError(data.error) : setFlashcards(data.flashcards || []);
            setSources(data.sources || []);
            if (!data.error && data.flashcards?.length) {
              const docName = data.sources?.[0]?.document_title || "";
              const ts: ToolSession = { id: genId(), type: "flashcards", title: query.slice(0, 40), data: { flashcards: data.flashcards }, sources: data.sources || [], createdAt: Date.now() };
              setToolSessions(prev => [ts, ...prev]);
              setActiveToolSessionId(ts.id);
              progressAPI.logFlashcards(query, data.flashcards.length).catch(() => {});
              progressAPI.logSession(query + (docName ? ` [${docName}]` : ""), "flashcards").catch(() => {});
            }
            break;
          case "quiz_mcq":
            data = (await chatAPI.quizMCQ(query, 5)).data;
            data.error ? setToolError(data.error) : setQuizQuestions(data.questions || []);
            setSources(data.sources || []);
            if (!data.error && data.questions?.length) {
              const docName = data.sources?.[0]?.document_title || "";
              const ts: ToolSession = { id: genId(), type: "quiz_mcq", title: query.slice(0, 40), data: { questions: data.questions }, sources: data.sources || [], createdAt: Date.now() };
              setToolSessions(prev => [ts, ...prev]);
              setActiveToolSessionId(ts.id);
              progressAPI.logSession(query + (docName ? ` [${docName}]` : ""), "quiz_mcq").catch(() => {});
            }
            break;
          case "quiz_tf":
            data = (await chatAPI.quizTF(query, 5)).data;
            data.error ? setToolError(data.error) : setQuizQuestions(data.questions || []);
            setSources(data.sources || []);
            if (!data.error && data.questions?.length) {
              const docName = data.sources?.[0]?.document_title || "";
              const ts: ToolSession = { id: genId(), type: "quiz_tf", title: query.slice(0, 40), data: { questions: data.questions }, sources: data.sources || [], createdAt: Date.now() };
              setToolSessions(prev => [ts, ...prev]);
              setActiveToolSessionId(ts.id);
              progressAPI.logSession(query + (docName ? ` [${docName}]` : ""), "quiz_tf").catch(() => {});
            }
            break;
          case "concept_breakdown":
            data = (await chatAPI.conceptBreakdown(query)).data;
            data.error ? setToolError(data.error) : setConceptData(data);
            setSources(data.sources || []);
            if (!data.error && !data.error) {
              const docName = data.sources?.[0]?.document_title || "";
              const ts: ToolSession = { id: genId(), type: "concept_breakdown", title: query.slice(0, 40), data: data, sources: data.sources || [], createdAt: Date.now() };
              setToolSessions(prev => [ts, ...prev]);
              setActiveToolSessionId(ts.id);
              progressAPI.logSession(query + (docName ? ` [${docName}]` : ""), "concepts").catch(() => {});
            }
            break;
        }
      } catch (err: any) { toast.error(err.response?.data?.detail || "Request failed"); }
    }
    setLoading(false);
  };

  const activeTool = TOOLS.find(t => t.id === view);
  const placeholder = view === "chat" ? "Ask a question..." : activeTool ? `${activeTool.label} for which topic?` : "Type here...";

  return (
    <div style={{ display: "flex", height: "calc(100vh - 56px)", overflow: "hidden" }}>
      {/* LEFT SIDEBAR */}
      <div style={{ width: 230, minWidth: 230, background: "var(--bg-secondary)", borderRight: "1px solid var(--border)", display: "flex", flexDirection: "column" }}>
        {/* Chat sessions */}
        <div style={{ padding: "12px 10px 0" }}>
          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 6 }}>
            <p style={{ fontSize: 10, color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: 1.2, fontWeight: 700 }}>Chats</p>
            <button onClick={createNewSession} title="New chat" style={{
              width: 24, height: 24, borderRadius: 6, border: "1px solid var(--border)", background: "var(--bg-card)",
              color: "var(--accent)", cursor: "pointer", display: "flex", alignItems: "center", justifyContent: "center",
            }}><Plus size={12} /></button>
          </div>
          <div style={{ maxHeight: 200, overflowY: "auto" }}>
            {sessions.length === 0 ? (
              <p style={{ fontSize: 11, color: "var(--text-muted)", padding: "4px 4px 8px" }}>No chats yet</p>
            ) : sessions.sort((a, b) => b.createdAt - a.createdAt).map(s => (
              <div key={s.id} onClick={() => selectSession(s.id)} style={{
                display: "flex", alignItems: "center", gap: 8, padding: "7px 8px", borderRadius: 8,
                cursor: "pointer", marginBottom: 1, transition: "all 0.15s",
                background: view === "chat" && activeSessionId === s.id ? "var(--accent-light)" : "transparent",
                color: view === "chat" && activeSessionId === s.id ? "var(--accent)" : "var(--text-secondary)",
              }}>
                <MessageSquare size={12} style={{ flexShrink: 0, opacity: 0.5 }} />
                <span style={{ flex: 1, fontSize: 12, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{s.title}</span>
                <span style={{ fontSize: 10, color: "var(--text-muted)", flexShrink: 0 }}>{s.messages.length}</span>
                <button onClick={e => { e.stopPropagation(); deleteSession(s.id); }} style={{ background: "none", border: "none", cursor: "pointer", color: "var(--text-muted)", padding: 1, opacity: 0.4 }}><Trash2 size={10} /></button>
              </div>
            ))}
          </div>
        </div>

        {/* Study Tools */}
        <div style={{ borderTop: "1px solid var(--border)", padding: "10px 8px 0", marginTop: 4 }}>
          <p style={{ fontSize: 10, color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: 1.2, fontWeight: 700, padding: "0 4px 6px" }}>Study Tools</p>
          {TOOLS.map(t => (
            <button key={t.id} onClick={() => setView(t.id)} style={{
              display: "flex", alignItems: "center", gap: 10, padding: "8px 8px", borderRadius: 8,
              border: "none", cursor: "pointer", width: "100%", textAlign: "left", marginBottom: 1,
              background: view === t.id ? `${t.color}18` : "transparent",
              color: view === t.id ? t.color : "var(--text-secondary)", transition: "all 0.15s",
            }}>
              <span style={{ flexShrink: 0 }}>{t.icon}</span>
              <div><div style={{ fontSize: 12, fontWeight: 600 }}>{t.label}</div><div style={{ fontSize: 10, color: "var(--text-muted)" }}>{t.desc}</div></div>
            </button>
          ))}
        </div>

        {/* Tool Session History */}
        {toolSessions.length > 0 && (
          <div style={{ borderTop: "1px solid var(--border)", padding: "10px 8px 0", marginTop: 4 }}>
            <p style={{ fontSize: 10, color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: 1.2, fontWeight: 700, padding: "0 4px 6px" }}>History</p>
            <div style={{ maxHeight: 160, overflowY: "auto" }}>
              {toolSessions.slice(0, 10).map(ts => {
                const tool = TOOLS.find(t => t.id === ts.type);
                return (
                  <div key={ts.id} onClick={() => loadToolSession(ts)} style={{
                    display: "flex", alignItems: "center", gap: 8, padding: "6px 8px", borderRadius: 6,
                    cursor: "pointer", marginBottom: 1, fontSize: 11,
                    background: activeToolSessionId === ts.id ? `${tool?.color || "var(--accent)"}18` : "transparent",
                    color: activeToolSessionId === ts.id ? tool?.color || "var(--accent)" : "var(--text-muted)",
                  }}>
                    <span style={{ flexShrink: 0 }}>{tool?.icon}</span>
                    <span style={{ flex: 1, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{ts.title}</span>
                    <button onClick={e => { e.stopPropagation(); deleteToolSession(ts.id); }} style={{ background: "none", border: "none", cursor: "pointer", color: "var(--text-muted)", padding: 1, opacity: 0.4 }}><Trash2 size={10} /></button>
                  </div>
                );
              })}
            </div>
          </div>
        )}

        <div style={{ flex: 1 }} />

        {/* Doc Selector */}
        <div style={{ borderTop: "1px solid var(--border)", padding: "10px 12px", position: "relative", flexShrink: 0 }}>
          <button onClick={() => setShowDocPicker(!showDocPicker)} style={{
            display: "flex", alignItems: "center", justifyContent: "space-between", width: "100%",
            padding: "8px 10px", borderRadius: 8, border: "1px solid var(--border)",
            background: "var(--bg-card)", color: "var(--text-primary)", cursor: "pointer", fontSize: 12,
          }}>
            <span style={{ display: "flex", alignItems: "center", gap: 6 }}><FileCheck size={14} color="var(--accent)" />{selectedDocIds.size}/{docs.length} docs</span>
            <ChevronDown size={14} style={{ transform: showDocPicker ? "rotate(180deg)" : "none", transition: "transform 0.2s" }} />
          </button>
          {showDocPicker && (
            <div style={{ position: "absolute", bottom: 48, left: 12, width: 206, zIndex: 50, background: "var(--bg-card)", border: "1px solid var(--border)", borderRadius: 10, padding: 8, maxHeight: 250, overflowY: "auto", boxShadow: "0 8px 24px rgba(0,0,0,0.4)" }}>
              <div style={{ display: "flex", gap: 6, marginBottom: 6, padding: "0 4px" }}>
                <button onClick={() => setSelectedDocIds(new Set(docs.map(d => d.id)))} style={{ fontSize: 11, color: "var(--accent)", background: "none", border: "none", cursor: "pointer" }}>All</button>
                <span style={{ color: "var(--text-muted)", fontSize: 11 }}>·</span>
                <button onClick={() => setSelectedDocIds(new Set())} style={{ fontSize: 11, color: "var(--text-muted)", background: "none", border: "none", cursor: "pointer" }}>Clear</button>
              </div>
              {docs.map(doc => (
                <label key={doc.id} style={{ display: "flex", alignItems: "center", gap: 8, padding: "6px 4px", cursor: "pointer", fontSize: 12, color: selectedDocIds.has(doc.id) ? "var(--text-primary)" : "var(--text-muted)" }}>
                  <input type="checkbox" checked={selectedDocIds.has(doc.id)} onChange={() => toggleDoc(doc.id)} style={{ accentColor: "var(--accent)" }} />
                  <span style={{ overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{doc.title}</span>
                </label>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* CENTER */}
      <div style={{ flex: 1, display: "flex", flexDirection: "column", minWidth: 0, overflow: "hidden" }}>
        {/* Header */}
        <div style={{ padding: "12px 20px", borderBottom: "1px solid var(--border)", display: "flex", alignItems: "center", gap: 10, flexShrink: 0 }}>
          {view === "chat" ? <>
            <MessageSquare size={18} color="#7c5cfc" />
            <div><h2 style={{ fontSize: 15, fontWeight: 700, margin: 0 }}>Q&A Chat</h2><p style={{ fontSize: 11, color: "var(--text-muted)", margin: 0 }}>Ask anything from your documents</p></div>
            {activeSession && <button onClick={createNewSession} style={{ marginLeft: "auto", padding: "4px 10px", borderRadius: 6, border: "1px solid var(--border)", background: "var(--bg-card)", color: "var(--text-secondary)", cursor: "pointer", fontSize: 11, display: "flex", alignItems: "center", gap: 4 }}><Plus size={12} /> New</button>}
          </> : <>
            <span style={{ color: activeTool?.color }}>{activeTool?.icon}</span>
            <div><h2 style={{ fontSize: 15, fontWeight: 700, margin: 0 }}>{activeTool?.label}</h2><p style={{ fontSize: 11, color: "var(--text-muted)", margin: 0 }}>{activeTool?.desc}</p></div>
          </>}
        </div>

        {/* Content */}
        <div style={{ flex: 1, overflowY: "auto", padding: 20 }}>
          {/* Chat */}
          {view === "chat" && messages.length > 0 && (
            <div style={{ display: "flex", flexDirection: "column", gap: 16, maxWidth: 720, margin: "0 auto" }}>
              {messages.map((msg, i) => (
                <div key={i} className="animate-fade-in" style={{ display: "flex", gap: 12, alignItems: "flex-start" }}>
                  <div style={{ width: 32, height: 32, borderRadius: 10, flexShrink: 0, display: "flex", alignItems: "center", justifyContent: "center", background: msg.role === "user" ? "var(--accent-light)" : "rgba(124,92,252,0.1)" }}>
                    {msg.role === "user" ? <User size={16} color="var(--accent)" /> : <Bot size={16} color="#7c5cfc" />}
                  </div>
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <div style={{ fontSize: 11, fontWeight: 600, color: "var(--text-muted)", marginBottom: 4 }}>
                      {msg.role === "user" ? "You" : "Tutor"}{msg.confidence && <ConfBadge c={msg.confidence} />}
                    </div>
                    {msg.role === "user" ? (
                      <div style={{ fontSize: 14, color: "var(--text-primary)", lineHeight: 1.6 }}>{msg.content}</div>
                    ) : (
                      <div className="markdown-body" style={{ background: "var(--bg-card)", border: "1px solid var(--border)", borderRadius: 12, padding: 16, fontSize: 14, lineHeight: 1.7 }}>
                        <ReactMarkdown>{msg.content}</ReactMarkdown>
                      </div>
                    )}
                  </div>
                </div>
              ))}
              {loading && <Typing />}
              <div ref={chatEndRef} />
            </div>
          )}

          {/* Tool outputs */}
          {view !== "chat" && loading && <LoadingSkeleton />}
          {view !== "chat" && toolError && !loading && (
            <div className="animate-fade-in markdown-body" style={{ background: "var(--bg-card)", border: "1px solid var(--border)", borderRadius: 12, padding: 24, fontSize: 14 }}>
              <ReactMarkdown>{toolError}</ReactMarkdown>
            </div>
          )}
          {conceptData && !loading && <ConceptView data={conceptData} />}
          {flashcards.length > 0 && !loading && <FlashcardViewer cards={flashcards} index={cardIndex} flipped={flipped} onFlip={() => setFlipped(!flipped)} onNext={() => { setCardIndex(i => Math.min(i + 1, flashcards.length - 1)); setFlipped(false); }} onPrev={() => { setCardIndex(i => Math.max(i - 1, 0)); setFlipped(false); }} />}
          {quizQuestions.length > 0 && !loading && <QuizViewer questions={quizQuestions} mode={view as any} answers={quizAnswers} submitted={quizSubmitted} onAnswer={(i, a) => setQuizAnswers({ ...quizAnswers, [i]: a })} onSubmit={() => {
            setQuizSubmitted(true);
            // Log quiz score with document name from sources
            const isTF = view === "quiz_tf";
            const correct = quizQuestions.filter((q, i) => isTF ? String(q.correct_answer) === quizAnswers[i] : q.correct_answer === quizAnswers[i]).length;
            const pct = Math.round((correct / quizQuestions.length) * 100);
            const topic = quizQuestions[0]?.topic || "General";
            const docName = sources.length > 0 ? sources[0].document_title : "";
            progressAPI.logQuiz(topic, isTF ? "tf" : "mcq", quizQuestions.length, correct, pct, quizQuestions, docName).catch(() => {});
          }} />

          {/* Empty states */}
          {!loading && view === "chat" && messages.length === 0 && (
            <EmptyState icon={<MessageSquare size={36} />} color="#7c5cfc" title="Ask anything from your documents" tips={["Ask specific or broad questions", "Follow up naturally in conversation", "Answers cite your uploaded docs"]} />
          )}
          {!loading && view !== "chat" && !hasToolContent && activeTool && (
            <EmptyState icon={activeTool.icon} color={activeTool.color} title={activeTool.tagline} tips={activeTool.tips} />
          )}
        </div>

        {/* Input */}
        <div style={{ padding: "12px 20px", borderTop: "1px solid var(--border)", background: "var(--bg-primary)", flexShrink: 0 }}>
          <div style={{ display: "flex", alignItems: "center", gap: 10, background: "var(--bg-card)", border: "1px solid var(--border)", borderRadius: 12, padding: "10px 14px" }}>
            <input value={input} onChange={e => setInput(e.target.value)}
              onKeyDown={e => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); handleSubmit(); } }}
              placeholder={placeholder} disabled={loading}
              style={{ flex: 1, background: "transparent", border: "none", outline: "none", color: "var(--text-primary)", fontSize: 14 }}
            />
            <button onClick={handleSubmit} disabled={loading || !input.trim()} style={{
              width: 36, height: 36, borderRadius: 8, border: "none", flexShrink: 0,
              background: input.trim() ? "var(--accent)" : "var(--bg-hover)",
              cursor: input.trim() && !loading ? "pointer" : "not-allowed",
              display: "flex", alignItems: "center", justifyContent: "center",
            }}>
              {loading ? <Loader2 size={16} color="white" className="animate-spin" /> : <Send size={16} color="white" />}
            </button>
          </div>
        </div>
      </div>

      {/* RIGHT: Sources */}
      <div style={{ width: 280, minWidth: 280, background: "var(--bg-secondary)", borderLeft: "1px solid var(--border)", display: "flex", flexDirection: "column" }}>
        <div style={{ padding: "12px 16px", borderBottom: "1px solid var(--border)" }}>
          <h3 style={{ fontSize: 13, fontWeight: 700, color: "var(--text-secondary)", margin: 0 }}>Sources & Context</h3>
        </div>
        <div style={{ flex: 1, overflowY: "auto", padding: 12 }}>
          {sources.length === 0 ? <p style={{ fontSize: 12, color: "var(--text-muted)", padding: 8 }}>Sources appear here after asking.</p> :
            sources.map((s, i) => (
              <div key={i} onClick={() => setExpandedSource(expandedSource === i ? null : i)} style={{ background: "var(--bg-card)", border: "1px solid var(--border)", borderRadius: 8, padding: 10, cursor: "pointer", marginBottom: 6 }}>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "start" }}>
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <div style={{ fontSize: 11, fontWeight: 600, color: "var(--accent)" }}>{s.document_title}</div>
                    <div style={{ fontSize: 10, color: "var(--text-muted)", marginTop: 2 }}>{s.section} · Score: {s.relevance_score}</div>
                  </div>
                  <ChevronRight size={12} style={{ color: "var(--text-muted)", transform: expandedSource === i ? "rotate(90deg)" : "none", transition: "transform 0.2s", flexShrink: 0 }} />
                </div>
                {expandedSource === i && <div style={{ marginTop: 8, padding: 8, background: "var(--bg-secondary)", borderRadius: 6, fontSize: 11, lineHeight: 1.6, color: "var(--text-secondary)", maxHeight: 180, overflowY: "auto" }}>{s.full_text}</div>}
              </div>
            ))
          }
        </div>
      </div>
    </div>
  );
}

// ── Small Components ──

function EmptyState({ icon, color, title, tips }: { icon: React.ReactNode; color: string; title: string; tips: string[] }) {
  return <div className="animate-fade-in" style={{ display: "flex", alignItems: "center", justifyContent: "center", height: "100%", padding: 40 }}>
    <div style={{ textAlign: "center", maxWidth: 340 }}>
      <div style={{ width: 68, height: 68, borderRadius: 18, margin: "0 auto 18px", background: `${color}15`, display: "flex", alignItems: "center", justifyContent: "center", color }}>{icon}</div>
      <h3 style={{ fontSize: 17, fontWeight: 700, margin: "0 0 14px" }}>{title}</h3>
      {tips.map((t, i) => <div key={i} style={{ display: "flex", alignItems: "center", gap: 8, padding: "7px 12px", background: "var(--bg-card)", borderRadius: 8, border: "1px solid var(--border)", fontSize: 12, color: "var(--text-secondary)", textAlign: "left", marginBottom: 6 }}><Zap size={11} color={color} style={{ flexShrink: 0 }} />{t}</div>)}
    </div>
  </div>;
}

function ConfBadge({ c }: { c: string }) {
  const m: Record<string, string> = { high: "var(--success)", medium: "var(--warning)", low: "var(--danger)" };
  return <span style={{ padding: "2px 6px", borderRadius: 20, fontSize: 9, fontWeight: 600, textTransform: "uppercase", marginLeft: 8, background: `${m[c]}22`, color: m[c] }}>{c}</span>;
}

function Typing() {
  return <div style={{ display: "flex", gap: 12, alignItems: "flex-start" }}>
    <div style={{ width: 32, height: 32, borderRadius: 10, background: "rgba(124,92,252,0.1)", display: "flex", alignItems: "center", justifyContent: "center" }}><Bot size={16} color="#7c5cfc" /></div>
    <div style={{ padding: "16px 0" }}><div style={{ display: "flex", gap: 4 }}>{[0, .2, .4].map((d, i) => <span key={i} style={{ width: 6, height: 6, borderRadius: 3, background: "var(--text-muted)", animation: `pulse 1s infinite ${d}s` }} />)}</div></div>
  </div>;
}

function LoadingSkeleton() { return <div style={{ display: "flex", flexDirection: "column", gap: 10 }}><div className="skeleton" style={{ height: 18, width: "35%" }} /><div className="skeleton" style={{ height: 100 }} /><div className="skeleton" style={{ height: 14, width: "55%" }} /></div>; }

function ConceptView({ data }: { data: any }) {
  return <div className="animate-fade-in" style={{ maxWidth: 600, margin: "0 auto" }}>
    <div style={{ background: "var(--bg-card)", border: "1px solid var(--border)", borderRadius: 12, padding: 20, marginBottom: 12 }}>
      <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 8 }}><Target size={18} color="#e879f9" /><h3 style={{ fontSize: 16, fontWeight: 700, margin: 0 }}>{data.main_topic || "Concept"}</h3></div>
      {data.definition && <p style={{ fontSize: 13, color: "var(--text-secondary)", lineHeight: 1.6 }}>{data.definition}</p>}
    </div>
    {data.subtopics?.map((s: any, i: number) => <div key={i} style={{ background: "var(--bg-card)", border: "1px solid var(--border)", borderRadius: 10, padding: 16, marginBottom: 8, borderLeft: "3px solid #e879f9" }}>
      <h4 style={{ fontSize: 14, fontWeight: 600, margin: "0 0 6px" }}>{s.name}</h4>
      <p style={{ fontSize: 12, color: "var(--text-secondary)", lineHeight: 1.5, margin: "0 0 8px" }}>{s.description}</p>
      {s.key_points?.length > 0 && <div style={{ display: "flex", flexWrap: "wrap", gap: 4 }}>{s.key_points.map((p: string, j: number) => <span key={j} style={{ padding: "3px 10px", borderRadius: 20, fontSize: 11, background: "rgba(232,121,249,0.1)", color: "#e879f9" }}>{p}</span>)}</div>}
    </div>)}
    {data.key_terms?.length > 0 && <div style={{ background: "var(--bg-card)", border: "1px solid var(--border)", borderRadius: 10, padding: 16, marginBottom: 8 }}>
      <h4 style={{ fontSize: 13, fontWeight: 600, margin: "0 0 10px" }}><BookOpen size={14} color="#e879f9" style={{ verticalAlign: "middle", marginRight: 6 }} />Key Terms</h4>
      {data.key_terms.map((t: any, i: number) => <div key={i} style={{ marginBottom: 6 }}><span style={{ fontWeight: 600, fontSize: 13, color: "#e879f9" }}>{t.term}</span><span style={{ fontSize: 12, color: "var(--text-secondary)" }}> — {t.definition}</span></div>)}
    </div>}
    {data.connections?.length > 0 && <div style={{ background: "var(--bg-card)", border: "1px solid var(--border)", borderRadius: 10, padding: 16 }}>
      <h4 style={{ fontSize: 13, fontWeight: 600, margin: "0 0 10px" }}><Network size={14} color="#e879f9" style={{ verticalAlign: "middle", marginRight: 6 }} />Connections</h4>
      {data.connections.map((c: string, i: number) => <div key={i} style={{ fontSize: 12, color: "var(--text-secondary)", lineHeight: 1.5, marginBottom: 4, paddingLeft: 8, borderLeft: "2px solid rgba(232,121,249,0.3)" }}>{c}</div>)}
    </div>}
  </div>;
}

function FlashcardViewer({ cards, index, flipped, onFlip, onNext, onPrev }: { cards: Flashcard[]; index: number; flipped: boolean; onFlip: () => void; onNext: () => void; onPrev: () => void }) {
  return <div className="animate-fade-in" style={{ maxWidth: 480, margin: "0 auto" }}>
    <p style={{ textAlign: "center", fontSize: 12, color: "var(--text-muted)", marginBottom: 10 }}>Card {index + 1} of {cards.length} · Click to flip</p>
    <div onClick={onFlip} style={{ background: flipped ? "var(--accent-light)" : "var(--bg-card)", border: `1px solid ${flipped ? "var(--accent)" : "var(--border)"}`, borderRadius: 14, padding: 36, minHeight: 180, display: "flex", alignItems: "center", justifyContent: "center", cursor: "pointer", textAlign: "center", transition: "all 0.3s" }}>
      <div><div style={{ fontSize: 10, color: "var(--text-muted)", marginBottom: 8, textTransform: "uppercase", letterSpacing: 1 }}>{flipped ? "Answer" : "Question"}</div><div style={{ fontSize: 17, fontWeight: 600, lineHeight: 1.5 }}>{flipped ? cards[index].back : cards[index].front}</div></div>
    </div>
    <div style={{ display: "flex", justifyContent: "center", gap: 10, marginTop: 14 }}>
      <Btn label="← Prev" onClick={onPrev} disabled={index === 0} /><Btn label="Next →" onClick={onNext} disabled={index === cards.length - 1} />
    </div>
  </div>;
}

function Btn({ label, onClick, disabled }: { label: string; onClick: () => void; disabled: boolean }) {
  return <button onClick={onClick} disabled={disabled} style={{ padding: "7px 18px", borderRadius: 8, border: "1px solid var(--border)", background: "var(--bg-card)", color: disabled ? "var(--text-muted)" : "var(--text-primary)", cursor: disabled ? "not-allowed" : "pointer", fontSize: 12, opacity: disabled ? 0.5 : 1 }}>{label}</button>;
}

function QuizViewer({ questions, mode, answers, submitted, onAnswer, onSubmit }: { questions: any[]; mode: string; answers: Record<number, string>; submitted: boolean; onAnswer: (i: number, a: string) => void; onSubmit: () => void }) {
  const isTF = mode === "quiz_tf";
  const score = submitted ? questions.filter((q, i) => isTF ? String(q.correct_answer) === answers[i] : q.correct_answer === answers[i]).length : 0;
  return <div className="animate-fade-in" style={{ maxWidth: 560, margin: "0 auto" }}>
    {submitted && <div style={{ textAlign: "center", padding: 16, marginBottom: 16, borderRadius: 12, background: score >= questions.length * .7 ? "rgba(52,211,153,0.1)" : "rgba(248,113,113,0.1)", border: `1px solid ${score >= questions.length * .7 ? "var(--success)" : "var(--danger)"}` }}><div style={{ fontSize: 28, fontWeight: 800 }}>{score}/{questions.length}</div><div style={{ fontSize: 13, color: "var(--text-secondary)" }}>{score >= questions.length * .7 ? "Great job!" : "Keep studying!"}</div></div>}
    {questions.map((q, i) => {
      const opts = isTF ? ["true", "false"] : (q.options || []);
      const correct = isTF ? String(q.correct_answer) : q.correct_answer;
      const sel = answers[i];
      return <div key={i} style={{ background: "var(--bg-card)", border: "1px solid var(--border)", borderRadius: 12, padding: 16, marginBottom: 10 }}>
        <p style={{ fontWeight: 600, marginBottom: 10, fontSize: 13 }}>{i + 1}. {isTF ? q.statement : q.question}</p>
        <div style={{ display: "flex", flexDirection: "column", gap: 5 }}>
          {opts.map((opt: string) => {
            const v = isTF ? opt : opt.charAt(0); const on = sel === v;
            const ok = submitted && v === correct, bad = submitted && on && sel !== correct;
            return <button key={opt} onClick={() => !submitted && onAnswer(i, v)} style={{ display: "flex", alignItems: "center", gap: 8, padding: "8px 12px", borderRadius: 6, border: "1px solid", width: "100%", textAlign: "left", fontSize: 12, borderColor: ok ? "var(--success)" : bad ? "var(--danger)" : on ? "var(--accent)" : "var(--border)", background: ok ? "rgba(52,211,153,0.1)" : bad ? "rgba(248,113,113,0.1)" : on ? "var(--accent-light)" : "var(--bg-secondary)", color: "var(--text-primary)", cursor: submitted ? "default" : "pointer" }}>
              {submitted && ok && <CheckCircle2 size={14} color="var(--success)" />}{submitted && bad && <XCircle size={14} color="var(--danger)" />}
              {isTF ? (opt === "true" ? "True" : "False") : opt}
            </button>;
          })}
        </div>
        {submitted && q.explanation && <p style={{ marginTop: 8, fontSize: 11, color: "var(--text-secondary)", lineHeight: 1.5, fontStyle: "italic" }}>{q.explanation}</p>}
      </div>;
    })}
    {!submitted && <button onClick={onSubmit} style={{ width: "100%", padding: "10px 0", borderRadius: 8, border: "none", background: "var(--accent)", color: "white", fontSize: 14, fontWeight: 600, cursor: "pointer", marginTop: 6 }}>Submit Answers</button>}
  </div>;
}