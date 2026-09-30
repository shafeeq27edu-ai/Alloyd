"use client";
import { useState } from "react";
import { API_BASE_URL } from "@/lib/api";
import { useRouter } from "next/navigation";
import { Loader2, AlertCircle } from "lucide-react";

export default function LoginPage() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const router = useRouter();

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!email || !password) {
      setError("Please provide both email and password.");
      return;
    }

    setIsLoading(true);
    setError(null);
    const formData = new URLSearchParams();
    formData.append("username", email);
    formData.append("password", password);

    try {
      const res = await fetch(`${API_BASE_URL}/auth/token`, {
        method: "POST",
        headers: { "Content-Type": "application/x-www-form-urlencoded" },
        body: formData,
        credentials: "include",
      });
      if (res.ok) {
        router.push("/");
      } else {
        const data = await res.json().catch(() => null);
        if (res.status === 422) {
          setError("Please enter a valid email address.");
        } else if (res.status === 429) {
          setError("Too many attempts. Please wait a moment and try again.");
        } else {
          setError(data?.detail || "The email or password is incorrect.");
        }
        setIsLoading(false);
      }
    } catch {
      setError("Unable to reach the server. Please check your connection.");
      setIsLoading(false);
    }
  };

  const handleRegister = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!email || !password) {
      setError("Please provide both email and password.");
      return;
    }
    if (password.length < 12) {
      setError("Password must be at least 12 characters.");
      return;
    }
    setIsLoading(true);
    setError(null);
    try {
      const res = await fetch(`${API_BASE_URL}/auth/register`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, password }),
        credentials: "include",
      });
      if (res.ok) {
        handleLogin(e);
      } else {
        const data = await res.json().catch(() => null);
        if (res.status === 409 || (data?.detail && typeof data.detail === 'string' && data.detail.toLowerCase().includes('exist'))) {
          setError("An account with this email already exists.");
        } else if (res.status === 422) {
          setError("Please enter a valid email address.");
        } else {
          setError(data?.detail || "Registration failed. Please try again.");
        }
        setIsLoading(false);
      }
    } catch {
      setError("Unable to reach the server. Please check your connection.");
      setIsLoading(false);
    }
  };

  // Input field classes — improved contrast:
  // Card bg: zinc-900/80 → Input bg: zinc-800/50 with zinc-700/50 border
  // Creates a visible "inset field" effect while staying monochromatic
  const inputClasses = "w-full px-4 py-2.5 rounded-lg bg-zinc-800/40 border border-zinc-700/50 focus:border-zinc-500 focus:bg-zinc-800/60 focus:ring-2 focus:ring-zinc-500/30 outline-none transition-all text-sm placeholder:text-zinc-500 text-zinc-100 shadow-inner shadow-zinc-950/20";

  return (
    <div className="flex min-h-screen flex-col items-center justify-center bg-zinc-950 text-zinc-50 font-sans selection:bg-zinc-800 selection:text-white px-4">
      <div className="w-full max-w-[360px] p-8 sm:p-10 bg-zinc-900/80 rounded-2xl shadow-2xl border border-zinc-800 backdrop-blur-sm">
        <div className="text-center mb-8">
          <h1 className="text-2xl font-semibold tracking-tight text-zinc-100">Alloyd</h1>
          <p className="text-zinc-500 mt-2 text-sm tracking-wide">Workspace Authentication</p>
        </div>

        {error && (
          <div 
            className="mb-6 p-3.5 rounded-lg bg-red-950/60 border border-red-900/50 flex items-start gap-3 text-red-300" 
            role="alert"
            aria-live="assertive"
          >
            <AlertCircle size={16} className="mt-0.5 flex-shrink-0 text-red-400" />
            <div className="text-sm font-medium leading-snug">{error}</div>
          </div>
        )}

        <form onSubmit={handleLogin} className="flex flex-col gap-5">
          <div className="flex flex-col gap-1.5">
            <label htmlFor="login-email" className="text-xs font-medium text-zinc-400 uppercase tracking-wider">Email</label>
            <input 
              id="login-email"
              type="email" 
              placeholder="you@example.com" 
              className={inputClasses} 
              value={email} onChange={e => setEmail(e.target.value)}
              autoComplete="email"
              required
              disabled={isLoading}
              aria-describedby={error ? "auth-error" : undefined}
            />
          </div>

          <div className="flex flex-col gap-1.5">
            <label htmlFor="login-password" className="text-xs font-medium text-zinc-400 uppercase tracking-wider">Password</label>
            <input 
              id="login-password"
              type="password" 
              placeholder="••••••••" 
              className={inputClasses} 
              value={password} onChange={e => setPassword(e.target.value)}
              autoComplete="current-password"
              required
              disabled={isLoading}
            />
          </div>

          <div className="flex flex-col gap-3 mt-4">
            <button 
              type="submit"
              disabled={isLoading}
              className="w-full py-2.5 bg-zinc-100 hover:bg-white text-zinc-950 font-medium rounded-lg transition-colors text-sm shadow-sm disabled:opacity-50 flex items-center justify-center gap-2 focus-visible:ring-2 focus-visible:ring-zinc-400 focus-visible:ring-offset-2 focus-visible:ring-offset-zinc-900 outline-none cursor-pointer"
            >
              {isLoading ? <Loader2 size={16} className="animate-spin text-zinc-900" /> : "Sign In"}
            </button>
            <button 
              type="button"
              onClick={handleRegister} 
              disabled={isLoading}
              className="w-full py-2.5 bg-transparent border border-zinc-700/60 hover:bg-zinc-800 hover:border-zinc-600 text-zinc-300 font-medium rounded-lg transition-colors text-sm disabled:opacity-50 focus-visible:ring-2 focus-visible:ring-zinc-400 focus-visible:ring-offset-2 focus-visible:ring-offset-zinc-900 outline-none cursor-pointer"
            >
              Create Account
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
