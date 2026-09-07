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
    });
    if (res.ok) {
      const data = await res.json();
      localStorage.setItem("token", data.access_token);
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
    });
    if (res.ok) {
      handleLogin(e);
    } else {
      alert("Registration failed");
    }
  };

  return (
    <div className="flex min-h-screen flex-col items-center justify-center bg-gray-900 text-white">
      <div className="w-full max-w-sm p-6 bg-gray-800 rounded-lg">
        <h1 className="text-2xl font-bold mb-4">Login to Alloyd</h1>
        <form className="flex flex-col gap-4">
          <input 
            type="email" 
            placeholder="Email" 
            className="p-2 rounded bg-gray-700 border-none" 
            value={email} onChange={e => setEmail(e.target.value)}
          />
          <input 
            type="password" 
            placeholder="Password" 
            className="p-2 rounded bg-gray-700 border-none" 
            value={password} onChange={e => setPassword(e.target.value)}
          />
          <button onClick={handleLogin} className="p-2 bg-blue-600 rounded">Login</button>
          <button onClick={handleRegister} className="p-2 bg-gray-600 rounded">Register</button>
        </form>
      </div>
    </div>
  );
}
