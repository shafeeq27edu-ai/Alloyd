"use client";
import { useState } from "react";
import { fetchWithAuth } from "@/lib/api";
import { useRouter } from "next/navigation";

export default function SettingsPage() {
  const [provider, setProvider] = useState("groq");
  const [key, setKey] = useState("");
  const router = useRouter();

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    const res = await fetchWithAuth("/keys", {
      method: "POST",
      body: JSON.stringify({ provider_name: provider, key }),
    });
    if (res.ok) {
      alert("Key saved securely!");
      router.push("/");
    } else {
      alert("Failed to save key");
    }
  };

  return (
    <div className="flex min-h-screen flex-col items-center justify-center bg-gray-900 text-white">
      <div className="w-full max-w-sm p-6 bg-gray-800 rounded-lg">
        <h1 className="text-2xl font-bold mb-4">Settings</h1>
        <form onSubmit={handleSave} className="flex flex-col gap-4">
          <select 
            value={provider} onChange={e => setProvider(e.target.value)}
            className="p-2 rounded bg-gray-700 border-none"
          >
            <option value="groq">Groq</option>
          </select>
          <input 
            type="password" 
            placeholder="API Key" 
            className="p-2 rounded bg-gray-700 border-none" 
            value={key} onChange={e => setKey(e.target.value)}
          />
          <button type="submit" className="p-2 bg-blue-600 rounded">Save Key</button>
        </form>
      </div>
    </div>
  );
}
