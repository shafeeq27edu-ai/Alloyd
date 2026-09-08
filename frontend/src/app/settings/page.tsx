"use client";
import { useState, useEffect } from "react";
import { fetchWithAuth } from "@/lib/api";
import { useRouter } from "next/navigation";

export default function SettingsPage() {
  const [provider, setProvider] = useState("groq");
  const [key, setKey] = useState("");
  const [configuredKeys, setConfiguredKeys] = useState<{provider_name: string, masked_key: string}[]>([]);
  const router = useRouter();

  useEffect(() => {
    fetchKeys();
  }, []);

  const fetchKeys = async () => {
    try {
      const res = await fetchWithAuth("/keys");
      if (res.ok) {
        const data = await res.json();
        setConfiguredKeys(data.keys || []);
      }
    } catch (e) {
      console.error(e);
    }
  };

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!key) return;
    const res = await fetchWithAuth("/keys", {
      method: "POST",
      body: JSON.stringify({ provider_name: provider, key }),
    });
    if (res.ok) {
      setKey("");
      fetchKeys();
    } else {
      alert("Failed to save key");
    }
  };

  return (
    <div className="flex min-h-screen flex-col items-center justify-center bg-gray-900 text-white">
      <div className="w-full max-w-sm p-6 bg-gray-800 rounded-lg">
        <div className="flex justify-between items-center mb-4">
          <h1 className="text-2xl font-bold">Settings</h1>
          <button onClick={() => router.push("/")} className="text-sm text-blue-400 hover:underline">
            Back to Chat
          </button>
        </div>
        
        <div className="mb-6 border-b border-gray-700 pb-4">
          <h2 className="text-lg font-semibold mb-2">Configured Providers</h2>
          {configuredKeys.length === 0 ? (
            <p className="text-gray-400 text-sm">No keys configured yet.</p>
          ) : (
            <ul className="space-y-2">
              {configuredKeys.map((k, i) => (
                <li key={i} className="flex justify-between text-sm p-2 bg-gray-700 rounded">
                  <span className="capitalize">{k.provider_name}</span>
                  <span className="text-green-400">Connected {k.masked_key}</span>
                </li>
              ))}
            </ul>
          )}
        </div>

        <form onSubmit={handleSave} className="flex flex-col gap-4">
          <h2 className="text-lg font-semibold">Add / Update Key</h2>
          <select 
            value={provider} onChange={e => setProvider(e.target.value)}
            className="p-2 rounded bg-gray-700 border-none outline-none text-white"
          >
            <option value="groq">Groq</option>
          </select>
          <input 
            type="password" 
            placeholder="API Key" 
            className="p-2 rounded bg-gray-700 border-none outline-none text-white" 
            value={key} onChange={e => setKey(e.target.value)}
          />
          <button type="submit" className="p-2 bg-blue-600 rounded font-bold hover:bg-blue-700 transition">Save Key</button>
        </form>
      </div>
    </div>
  );
}
