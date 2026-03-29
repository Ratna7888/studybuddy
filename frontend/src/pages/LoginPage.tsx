import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAuthStore } from "@/store/authStore";
import { GraduationCap, Mail, Lock, User, ArrowRight, Loader2 } from "lucide-react";
import toast from "react-hot-toast";

export default function LoginPage() {
  const [isLogin, setIsLogin] = useState(true);
  const [email, setEmail] = useState("");
  const [name, setName] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const { login, register } = useAuthStore();
  const navigate = useNavigate();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    try {
      if (isLogin) {
        await login(email, password);
      } else {
        await register(email, name, password);
      }
      toast.success(isLogin ? "Welcome back!" : "Account created!");
      navigate("/study");
    } catch (err: any) {
      toast.error(err.response?.data?.detail || "Something went wrong");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div
      style={{ minHeight: "100vh", display: "flex", alignItems: "center", justifyContent: "center", background: "var(--bg-primary)", padding: "1rem" }}
    >
      <div style={{ width: "100%", maxWidth: 420 }}>
        {/* Logo */}
        <div style={{ textAlign: "center", marginBottom: "2rem" }}>
          <div
            style={{
              width: 56, height: 56, borderRadius: 16, background: "var(--accent)",
              display: "inline-flex", alignItems: "center", justifyContent: "center", marginBottom: 12,
            }}
          >
            <GraduationCap size={28} color="white" />
          </div>
          <h1 style={{ fontSize: 24, fontWeight: 700, color: "var(--text-primary)" }}>StudyBuddy AI</h1>
          <p style={{ color: "var(--text-secondary)", marginTop: 4, fontSize: 14 }}>
            Your AI-powered personal tutor
          </p>
        </div>

        {/* Card */}
        <div
          style={{
            background: "var(--bg-card)", border: "1px solid var(--border)",
            borderRadius: 16, padding: "2rem",
          }}
        >
          {/* Tabs */}
          <div style={{ display: "flex", gap: 0, marginBottom: "1.5rem", background: "var(--bg-secondary)", borderRadius: 10, padding: 4 }}>
            {["Sign In", "Sign Up"].map((label, i) => (
              <button
                key={label}
                onClick={() => setIsLogin(i === 0)}
                style={{
                  flex: 1, padding: "8px 0", borderRadius: 8, border: "none", cursor: "pointer",
                  fontSize: 14, fontWeight: 600, transition: "all 0.2s",
                  background: (i === 0 ? isLogin : !isLogin) ? "var(--accent)" : "transparent",
                  color: (i === 0 ? isLogin : !isLogin) ? "white" : "var(--text-secondary)",
                }}
              >
                {label}
              </button>
            ))}
          </div>

          <form onSubmit={handleSubmit} style={{ display: "flex", flexDirection: "column", gap: 14 }}>
            {!isLogin && (
              <InputField icon={<User size={18} />} placeholder="Full Name" value={name} onChange={setName} />
            )}
            <InputField icon={<Mail size={18} />} placeholder="Email" type="email" value={email} onChange={setEmail} />
            <InputField icon={<Lock size={18} />} placeholder="Password" type="password" value={password} onChange={setPassword} />

            <button
              type="submit"
              disabled={loading}
              style={{
                marginTop: 8, padding: "12px 0", borderRadius: 10, border: "none",
                background: "var(--accent)", color: "white", fontSize: 15, fontWeight: 600,
                cursor: loading ? "not-allowed" : "pointer", opacity: loading ? 0.7 : 1,
                display: "flex", alignItems: "center", justifyContent: "center", gap: 8,
                transition: "all 0.2s",
              }}
            >
              {loading ? <Loader2 size={18} className="animate-spin" /> : <ArrowRight size={18} />}
              {isLogin ? "Sign In" : "Create Account"}
            </button>
          </form>
        </div>
      </div>
    </div>
  );
}

function InputField({
  icon, placeholder, type = "text", value, onChange,
}: {
  icon: React.ReactNode; placeholder: string; type?: string; value: string; onChange: (v: string) => void;
}) {
  return (
    <div
      style={{
        display: "flex", alignItems: "center", gap: 10, padding: "10px 14px",
        background: "var(--bg-secondary)", borderRadius: 10, border: "1px solid var(--border)",
      }}
    >
      <span style={{ color: "var(--text-muted)" }}>{icon}</span>
      <input
        type={type}
        placeholder={placeholder}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        required
        style={{
          flex: 1, background: "transparent", border: "none", outline: "none",
          color: "var(--text-primary)", fontSize: 14,
        }}
      />
    </div>
  );
}