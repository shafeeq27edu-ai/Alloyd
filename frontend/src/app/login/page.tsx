"use client";
import { useState } from "react";
import { API_BASE_URL } from "@/lib/api";
import { useRouter } from "next/navigation";

export default function LoginPage() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const router = useRouter();

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    const formData = new URLSearchParams();
    formData.append("username", email);
    formData.append("password", password);

    const res = await fetch(`${API_BASE_URL}/auth/token`, {
      method: "POST",
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
      body: formData,
      credentials: "include",
    });
    if (res.ok) {
      router.push("/");
    } else {
      alert("Login failed");
    }
  };

  const handleRegister = async (e: React.FormEvent) => {
    e.preventDefault();
    const res = await fetch(`${API_BASE_URL}/auth/register`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, password }),
      credentials: "include",
    });
    if (res.ok) {
      handleLogin(e);
    } else {
      alert("Registration failed");
    }
  };

  return (
    <div className="flex min-h-screen flex-col items-center justify-center bg-gray-900 text-white">
      <div className="w-full max-w-sm p-8 bg-gray-800 rounded-xl shadow-lg border border-gray-700">
        <div className="text-center mb-8">
          <h1 className="text-3xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-blue-400 to-purple-500">Alloyd</h1>
          <p className="text-gray-400 mt-2 text-sm">Sign in to your multi-AI workspace</p>
        </div>

        <form className="flex flex-col gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-400 mb-1">Email</label>
            <input 
              type="email" 
              placeholder="you@example.com" 
              className="w-full p-3 rounded-lg bg-gray-900 border border-gray-700 focus:border-blue-500 focus:ring-1 focus:ring-blue-500 outline-none transition" 
              value={email} onChange={e => setEmail(e.target.value)}
              required
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-400 mb-1">Password</label>
            <input 
              type="password" 
              placeholder="••••••••" 
              className="w-full p-3 rounded-lg bg-gray-900 border border-gray-700 focus:border-blue-500 focus:ring-1 focus:ring-blue-500 outline-none transition" 
              value={password} onChange={e => setPassword(e.target.value)}
              required
            />
          </div>

          <div className="flex flex-col gap-2 mt-4">
            <button 
              onClick={handleLogin} 
              className="w-full p-3 bg-blue-600 hover:bg-blue-700 text-white font-semibold rounded-lg transition"
            >
              Sign In
            </button>
            <button 
              onClick={handleRegister} 
              className="w-full p-3 bg-transparent border border-gray-600 hover:bg-gray-700 text-gray-300 font-semibold rounded-lg transition"
            >
              Create Account
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
