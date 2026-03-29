import { useEffect } from "react";
import { BrowserRouter, Routes, Route, Navigate, Link, useLocation } from "react-router-dom";
import { Toaster } from "react-hot-toast";
import { useAuthStore } from "@/store/authStore";
import LoginPage from "@/pages/LoginPage";
import StudyWorkspace from "@/pages/StudyWorkspace";
import DocumentsPage from "@/pages/DocumentsPage";
import ProgressPage from "@/pages/ProgressPage";
import {
  Sparkles, BookOpen, FileText, LogOut, TrendingUp,
} from "lucide-react";


function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const { isAuthenticated } = useAuthStore();
  if (!isAuthenticated) return <Navigate to="/login" replace />;
  return <>{children}</>;
}

function AppLayout({ children }: { children: React.ReactNode }) {
  const { user, logout } = useAuthStore();
  const location = useLocation();

  const navItems = [
    { path: "/study", label: "Study", icon: <BookOpen size={18} /> },
    { path: "/documents", label: "Documents", icon: <FileText size={18} /> },
    { path: "/progress", label: "Progress", icon: <TrendingUp size={18} /> },
  ];

  return (
    <div style={{ display: "flex", flexDirection: "column", height: "100vh" }}>
      {/* Top Navigation */}
      <nav
        style={{
          height: 56, padding: "0 20px",
          background: "var(--bg-secondary)", borderBottom: "1px solid var(--border)",
          display: "flex", alignItems: "center", justifyContent: "space-between",
          flexShrink: 0,
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: 24 }}>
          <Link to="/study" style={{ display: "flex", alignItems: "center", gap: 8, textDecoration: "none", color: "var(--text-primary)" }}>
            <Sparkles size={20} color="var(--accent)" />
            <span style={{ fontWeight: 700, fontSize: 16 }}>StudyBuddy</span>
          </Link>

          <div style={{ display: "flex", gap: 4 }}>
            {navItems.map((item) => {
              const active = location.pathname === item.path;
              return (
                <Link
                  key={item.path}
                  to={item.path}
                  style={{
                    display: "flex", alignItems: "center", gap: 6, padding: "6px 14px",
                    borderRadius: 8, textDecoration: "none", fontSize: 13, fontWeight: 500,
                    transition: "all 0.15s",
                    background: active ? "var(--accent-light)" : "transparent",
                    color: active ? "var(--accent)" : "var(--text-secondary)",
                  }}
                >
                  {item.icon} {item.label}
                </Link>
              );
            })}
          </div>
        </div>

        <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
          <span style={{ fontSize: 13, color: "var(--text-secondary)" }}>
            {user?.name}
          </span>
          <button
            onClick={logout}
            style={{
              display: "flex", alignItems: "center", gap: 4, padding: "6px 10px",
              borderRadius: 6, border: "none", background: "transparent",
              color: "var(--text-muted)", cursor: "pointer", fontSize: 12,
            }}
          >
            <LogOut size={14} /> Logout
          </button>
        </div>
      </nav>

      {/* Page Content */}
      <div style={{ flex: 1, overflow: "hidden" }}>
        {children}
      </div>
    </div>
  );
}

export default function App() {
  const { loadFromStorage } = useAuthStore();

  useEffect(() => {
    loadFromStorage();
  }, [loadFromStorage]);

  return (
    <BrowserRouter>
      <Toaster
        position="top-right"
        toastOptions={{
          style: {
            background: "var(--bg-card)",
            color: "var(--text-primary)",
            border: "1px solid var(--border)",
            borderRadius: 10,
            fontSize: 13,
          },
        }}
      />
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route
          path="/study"
          element={
            <ProtectedRoute>
              <AppLayout>
                <StudyWorkspace />
              </AppLayout>
            </ProtectedRoute>
          }
        />
        <Route
          path="/documents"
          element={
            <ProtectedRoute>
              <AppLayout>
                <DocumentsPage />
              </AppLayout>
            </ProtectedRoute>
          }
        />
        <Route
          path="/progress"
          element={
            <ProtectedRoute>
              <AppLayout>
                <ProgressPage />
              </AppLayout>
            </ProtectedRoute>
          }
        />
        <Route path="*" element={<Navigate to="/study" replace />} />
      </Routes>
    </BrowserRouter>
  );
}