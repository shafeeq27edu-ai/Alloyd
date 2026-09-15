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
        setError("The email or password is incorrect.");
        setIsLoading(false);
      }
    } catch {
      setError("Network error. Please try again later.");
      setIsLoading(false);
    }
  };

  const handleRegister = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!email || !password) {
      setError("Please provide both email and password.");
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
        setError(data?.detail || "Registration failed. Account may already exist.");
        setIsLoading(false);
      }
    } catch {
      setError("Network error. Please try again later.");
      setIsLoading(false);
    }
  };

  return (
    <div className="flex min-h-screen flex-col items-center justify-center bg-zinc-950 text-zinc-50 font-sans selection:bg-zinc-800 selection:text-white px-4">
      <div className="w-full max-w-[360px] p-8 sm:p-10 bg-zinc-900/80 rounded-2xl shadow-2xl border border-zinc-800 backdrop-blur-sm">
        <div className="text-center mb-8">
          <h1 className="text-2xl font-semibold tracking-tight text-zinc-100">Alloyd</h1>
          <p className="text-zinc-500 mt-2 text-sm tracking-wide">Workspace Authentication</p>
        </div>

        {error && (
          <div className="mb-6 p-3 rounded-lg bg-red-950/50 border border-red-900/50 flex items-start gap-3 text-red-400" aria-live="assertive">
            <AlertCircle size={16} className="mt-0.5 flex-shrink-0" />
            <div className="text-sm font-medium leading-snug">{error}</div>
          </div>
        )}

        <form className="flex flex-col gap-5">
          <div className="flex flex-col gap-1.5">
            <label htmlFor="email" className="text-xs font-medium text-zinc-400 uppercase tracking-wider">Email</label>
            <input 
              id="email"
              type="email" 
              placeholder="you@example.com" 
              className="w-full px-4 py-2.5 rounded-lg bg-zinc-950 border border-zinc-800 focus:border-zinc-500 focus:bg-zinc-900 focus:ring-1 focus:ring-zinc-500 outline-none transition-all text-sm placeholder:text-zinc-600 text-zinc-100 shadow-sm" 
              value={email} onChange={e => setEmail(e.target.value)}
              required
              disabled={isLoading}
            />
          </div>

          <div className="flex flex-col gap-1.5">
            <label htmlFor="password" className="text-xs font-medium text-zinc-400 uppercase tracking-wider">Password</label>
            <input 
              id="password"
              type="password" 
              placeholder="••••••••" 
              className="w-full px-4 py-2.5 rounded-lg bg-zinc-950 border border-zinc-800 focus:border-zinc-500 focus:bg-zinc-900 focus:ring-1 focus:ring-zinc-500 outline-none transition-all text-sm placeholder:text-zinc-600 text-zinc-100 shadow-sm" 
              value={password} onChange={e => setPassword(e.target.value)}
              required
              disabled={isLoading}
            />
          </div>

          <div className="flex flex-col gap-3 mt-4">
            <button 
              type="submit"
              onClick={handleLogin} 
              disabled={isLoading}
              className="w-full py-2.5 bg-zinc-100 hover:bg-white text-zinc-950 font-medium rounded-lg transition-colors text-sm shadow-sm disabled:opacity-50 flex items-center justify-center gap-2"
            >
              {isLoading ? <Loader2 size={16} className="animate-spin text-zinc-900" /> : "Sign In"}
            </button>
            <button 
              type="button"
              onClick={handleRegister} 
              disabled={isLoading}
              className="w-full py-2.5 bg-transparent border border-zinc-800 hover:bg-zinc-800 text-zinc-300 font-medium rounded-lg transition-colors text-sm disabled:opacity-50"
            >
              Create Account
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
