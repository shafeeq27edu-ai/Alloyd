"use client";
import { useState, useEffect, Suspense, useCallback } from "react";
import { fetchWithAuth } from "@/lib/api";
import { useRouter, useSearchParams } from "next/navigation";
import { useToast } from "@/components/Toast";
import Select from "@/components/Select";
import { Settings2, X } from "lucide-react";

function SettingsContent() {
  const [provider, setProvider] = useState("groq");
  const [key, setKey] = useState("");
  const [configuredKeys, setConfiguredKeys] = useState<{provider_name: string, masked_key: string}[]>([]);
  const router = useRouter();
  const searchParams = useSearchParams();
  const isOnboarding = searchParams.get("onboarding") === "true";
  const { addToast } = useToast();

  const fetchKeys = useCallback(async () => {
    try {
      const res = await fetchWithAuth("/keys");
      if (res.ok) {
        const data = await res.json();
        setConfiguredKeys(data.keys || []);
      }
    } catch (e) {
      console.error(e);
    }
  }, []);

  useEffect(() => {
    void fetchKeys();
  }, [fetchKeys]);

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!key) return;
    try {
      const res = await fetchWithAuth("/keys", {
        method: "POST",
        body: JSON.stringify({ provider_name: provider, key }),
      });
      if (res.ok) {
        setKey("");
        fetchKeys();
        addToast("Key saved successfully", "success");
      } else {
        addToast("Failed to save key", "error");
      }
    } catch {
      addToast("Network error saving key", "error");
    }
  };

  const providerOptions = [
    { value: "groq", label: "Groq" },
    { value: "gemini", label: "Google Gemini" },
    { value: "anthropic", label: "Anthropic (Claude)" }
  ];

  return (
    <div className="flex min-h-screen flex-col items-center justify-center bg-zinc-950 text-zinc-50 font-sans px-4">
      <div className="w-full max-w-[420px] p-8 bg-zinc-900/50 rounded-2xl shadow-2xl border border-zinc-800/80 backdrop-blur-sm">
        <div className="flex justify-between items-center mb-6">
          <h1 className="text-xl font-semibold tracking-tight flex items-center gap-2">
            <Settings2 size={20} className="text-zinc-400" />
            Workspace Settings
          </h1>
          <button onClick={() => router.push("/")} className="text-zinc-500 hover:text-zinc-200 transition-colors p-1" aria-label="Close settings">
            <X size={18} />
          </button>
        </div>
        
        {isOnboarding && (
          <div className="mb-8 p-4 bg-zinc-800/50 border border-zinc-700 rounded-xl text-sm leading-relaxed text-zinc-300">
            <strong className="text-zinc-100 block mb-1">Welcome to Alloyd</strong>
            Please configure at least one AI provider API key before starting. We recommend Groq or Gemini.
          </div>
        )}

        <div className="mb-8 border-b border-zinc-800 pb-6">
          <h2 className="text-sm font-medium text-zinc-400 uppercase tracking-wider mb-3">Configured Providers</h2>
          {configuredKeys.length === 0 ? (
            <p className="text-zinc-500 text-sm">No keys configured yet.</p>
          ) : (
            <ul className="space-y-2.5">
              {configuredKeys.map((k, i) => (
                <li key={i} className="flex justify-between items-center text-sm px-3 py-2.5 bg-zinc-950/50 border border-zinc-800/50 rounded-lg">
                  <span className="capitalize font-medium text-zinc-200">{k.provider_name}</span>
                  <div className="flex items-center gap-3">
                    <span className="text-zinc-400 flex items-center gap-1.5 text-xs font-mono">
                      <span className="w-1.5 h-1.5 bg-green-500 rounded-full"></span>
                      {k.masked_key}
                    </span>
                    <button 
                      onClick={async () => {
                        if (confirm(`Remove ${k.provider_name} key?`)) {
                          try {
                            const res = await fetchWithAuth(`/keys/${k.provider_name}`, { method: "DELETE" });
                            if (res.ok) {
                              fetchKeys();
                              addToast("Key removed", "success");
                            } else {
                              addToast("Failed to remove key", "error");
                            }
                          } catch {
                            addToast("Network error", "error");
                          }
                        }
                      }}
                      className="text-zinc-500 hover:text-red-400 text-xs transition-colors"
                    >
                      Remove
                    </button>
                  </div>
                </li>
              ))}
            </ul>
          )}
        </div>

        <form onSubmit={handleSave} className="flex flex-col gap-4">
          <h2 className="text-sm font-medium text-zinc-400 uppercase tracking-wider">Add / Update Key</h2>
          <div className="flex flex-col gap-3">
            <Select 
              options={providerOptions}
              value={provider}
              onChange={setProvider}
            />
            <input 
              type="password" 
              placeholder="API Key" 
              className="w-full px-3 py-2.5 rounded-lg bg-zinc-950/50 border border-zinc-800 focus:border-zinc-500 outline-none text-zinc-100 text-sm transition-colors placeholder:text-zinc-600 font-mono shadow-sm" 
              value={key} onChange={e => setKey(e.target.value)}
            />
            <button type="submit" className="w-full py-2.5 mt-1 bg-zinc-100 hover:bg-white text-zinc-950 font-medium rounded-lg transition-colors text-sm shadow-sm disabled:opacity-50">Save Provider Key</button>
          </div>
        </form>
      </div>
    </div>
  );
}

export default function SettingsPage() {
  return (
    <Suspense fallback={<div className="flex min-h-screen items-center justify-center bg-zinc-950 text-zinc-50 font-sans">Loading...</div>}>
      <SettingsContent />
    </Suspense>
  );
}
