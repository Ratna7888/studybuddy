import { useState, useEffect, useCallback } from "react";
import { documentsAPI } from "@/services/api";
import type { Document } from "@/types";
import toast from "react-hot-toast";
import {
  Upload, FileText, Trash2, Loader2, CheckCircle2,
  AlertCircle, Clock, RefreshCw, Sparkles, File,
} from "lucide-react";

export default function DocumentsPage() {
  const [docs, setDocs] = useState<Document[]>([]);
  const [uploading, setUploading] = useState(false);
  const [dragOver, setDragOver] = useState(false);
  const [loading, setLoading] = useState(true);

  const fetchDocs = useCallback(async () => {
    try {
      const { data } = await documentsAPI.list();
      setDocs(data);
    } catch {
      toast.error("Failed to load documents");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchDocs();
    // Poll for processing updates
    const interval = setInterval(fetchDocs, 5000);
    return () => clearInterval(interval);
  }, [fetchDocs]);

  const handleUpload = async (files: FileList | null) => {
    if (!files || files.length === 0) return;
    setUploading(true);
    let successCount = 0;

    for (const file of Array.from(files)) {
      const ext = file.name.split(".").pop()?.toLowerCase();
      if (!["pdf", "txt", "md", "docx"].includes(ext || "")) {
        toast.error(`Unsupported file: ${file.name}`);
        continue;
      }
      try {
        await documentsAPI.upload(file);
        successCount++;
      } catch (err: any) {
        toast.error(`Failed to upload ${file.name}`);
      }
    }

    if (successCount > 0) {
      toast.success(`${successCount} file(s) uploaded and processing`);
      fetchDocs();
    }
    setUploading(false);
  };

  const handleDelete = async (id: number, title: string) => {
    if (!confirm(`Delete "${title}"?`)) return;
    try {
      await documentsAPI.delete(id);
      toast.success("Document deleted");
      setDocs((prev) => prev.filter((d) => d.id !== id));
    } catch {
      toast.error("Failed to delete document");
    }
  };

  const statusIcon = (status: string) => {
    switch (status) {
      case "ready": return <CheckCircle2 size={16} color="var(--success)" />;
      case "processing": return <Loader2 size={16} color="var(--warning)" className="animate-spin" />;
      case "failed": return <AlertCircle size={16} color="var(--danger)" />;
      default: return <Clock size={16} color="var(--text-muted)" />;
    }
  };

  const fileIcon = (type: string) => {
    const colors: Record<string, string> = { pdf: "#f87171", txt: "#60a5fa", md: "#34d399", docx: "#a78bfa" };
    return (
      <div
        style={{
          width: 40, height: 40, borderRadius: 10,
          background: `${colors[type] || "var(--text-muted)"}22`,
          display: "flex", alignItems: "center", justifyContent: "center",
        }}
      >
        <File size={18} color={colors[type] || "var(--text-muted)"} />
      </div>
    );
  };

  return (
    <div style={{ minHeight: "100vh", background: "var(--bg-primary)" }}>
      {/* Header */}
      <div
        style={{
          padding: "24px 32px", borderBottom: "1px solid var(--border)",
          display: "flex", justifyContent: "space-between", alignItems: "center",
        }}
      >
        <div>
          <h1 style={{ fontSize: 22, fontWeight: 700 }}>Documents</h1>
          <p style={{ fontSize: 13, color: "var(--text-muted)", marginTop: 2 }}>
            Upload your study materials — PDFs, text files, markdown, or DOCX
          </p>
        </div>
        <button
          onClick={fetchDocs}
          style={{
            display: "flex", alignItems: "center", gap: 6, padding: "8px 14px",
            borderRadius: 8, border: "1px solid var(--border)", background: "var(--bg-card)",
            color: "var(--text-secondary)", cursor: "pointer", fontSize: 13,
          }}
        >
          <RefreshCw size={14} /> Refresh
        </button>
      </div>

      <div style={{ maxWidth: 800, margin: "0 auto", padding: 32 }}>
        {/* Upload Zone */}
        <div
          onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
          onDragLeave={() => setDragOver(false)}
          onDrop={(e) => { e.preventDefault(); setDragOver(false); handleUpload(e.dataTransfer.files); }}
          onClick={() => {
            const inp = document.createElement("input");
            inp.type = "file";
            inp.multiple = true;
            inp.accept = ".pdf,.txt,.md,.docx";
            inp.onchange = () => handleUpload(inp.files);
            inp.click();
          }}
          style={{
            border: `2px dashed ${dragOver ? "var(--accent)" : "var(--border)"}`,
            borderRadius: 16, padding: "48px 24px", textAlign: "center",
            cursor: "pointer", transition: "all 0.2s",
            background: dragOver ? "var(--accent-light)" : "var(--bg-card)",
          }}
        >
          {uploading ? (
            <Loader2 size={36} color="var(--accent)" className="animate-spin" style={{ margin: "0 auto" }} />
          ) : (
            <Upload size={36} color={dragOver ? "var(--accent)" : "var(--text-muted)"} style={{ margin: "0 auto" }} />
          )}
          <p style={{ marginTop: 12, fontWeight: 600, color: "var(--text-primary)" }}>
            {uploading ? "Uploading..." : "Drop files here or click to upload"}
          </p>
          <p style={{ fontSize: 13, color: "var(--text-muted)", marginTop: 4 }}>
            PDF, TXT, Markdown, DOCX — up to 50MB
          </p>
        </div>

        {/* Document List */}
        <div style={{ marginTop: 32 }}>
          <h2 style={{ fontSize: 16, fontWeight: 700, marginBottom: 16 }}>
            Your Documents ({docs.length})
          </h2>

          {loading ? (
            <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
              {[1, 2, 3].map((i) => <div key={i} className="skeleton" style={{ height: 64 }} />)}
            </div>
          ) : docs.length === 0 ? (
            <div style={{ textAlign: "center", padding: 48, color: "var(--text-muted)" }}>
              <FileText size={40} style={{ margin: "0 auto 12px", opacity: 0.3 }} />
              <p>No documents yet. Upload your study materials to get started!</p>
            </div>
          ) : (
            <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
              {docs.map((doc) => (
                <div
                  key={doc.id}
                  style={{
                    display: "flex", alignItems: "center", gap: 14, padding: "14px 16px",
                    background: "var(--bg-card)", border: "1px solid var(--border)",
                    borderRadius: 12, transition: "all 0.15s",
                  }}
                >
                  {fileIcon(doc.file_type)}
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <div style={{ fontSize: 14, fontWeight: 600, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                      {doc.title}
                    </div>
                    <div style={{ fontSize: 12, color: "var(--text-muted)", marginTop: 2, display: "flex", alignItems: "center", gap: 8 }}>
                      <span style={{ textTransform: "uppercase" }}>{doc.file_type}</span>
                      <span>·</span>
                      <span>{doc.chunk_count} chunks</span>
                      <span>·</span>
                      <span>{new Date(doc.created_at).toLocaleDateString()}</span>
                    </div>
                  </div>
                  <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
                    {statusIcon(doc.processing_status)}
                    <span style={{ fontSize: 12, color: "var(--text-muted)", textTransform: "capitalize" }}>
                      {doc.processing_status}
                    </span>
                    <button
                      onClick={(e) => { e.stopPropagation(); handleDelete(doc.id, doc.title); }}
                      style={{
                        padding: 6, borderRadius: 6, border: "none",
                        background: "transparent", cursor: "pointer", color: "var(--text-muted)",
                      }}
                    >
                      <Trash2 size={16} />
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}