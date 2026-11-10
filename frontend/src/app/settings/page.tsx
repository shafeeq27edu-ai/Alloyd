"use client";
import { useState, useEffect, useRef, Suspense, useCallback } from "react";
import { fetchWithAuth, resetCsrfToken } from "@/lib/api";
import { useRouter, useSearchParams } from "next/navigation";
import { useToast } from "@/components/Toast";
import Select from "@/components/Select";
import { Settings2, X, Trash2, LogOut } from "lucide-react";

function SettingsContent() {
  const [provider, setProvider] = useState("groq");
  const [key, setKey] = useState("");
  const [isSaving, setIsSaving] = useState(false);
  // State updates don't land before a same-tick double click re-enters the
  // handler, so the ref is the actual guard; the state only drives the button.
  const savingRef = useRef(false);
  const [configuredKeys, setConfiguredKeys] = useState<{provider_name: string, masked_key: string}[]>([]);
  const [showDeleteAccount, setShowDeleteAccount] = useState(false);
  const [accountPassword, setAccountPassword] = useState("");
  const [isDeletingAccount, setIsDeletingAccount] = useState(false);
  const deletingRef = useRef(false);
  const router = useRouter();
  const searchParams = useSearchParams();
  const isOnboarding = searchParams.get("onboarding") === "true";
  const { addToast } = useToast();

  const fetchKeys = useCallback(async () => {
    try {
      const res = await fetchWithAuth("/keys/");
      if (res.ok) {
        const data = await res.json();
        setConfiguredKeys(data.keys || []);
      }
    } catch (e) {
      console.error(e);
    }
  }, []);

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    void fetchKeys();
  }, [fetchKeys]);

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!key) {
      addToast("Please enter an API key", "error");
      return;
    }
    if (savingRef.current) return;
    savingRef.current = true;
    setIsSaving(true);
    try {
      const res = await fetchWithAuth("/keys/", {
        method: "POST",
        body: JSON.stringify({ provider_name: provider, key }),
      });
      if (res.ok) {
        setKey("");
        fetchKeys();
        addToast("Key saved successfully", "success");
        if (isOnboarding) router.push("/");
      } else {
        const data = await res.json().catch(() => null);
        if (res.status === 400) {
          addToast(data?.detail || "Invalid API key. Check the key and try again.", "error");
        } else if (res.status === 429) {
          addToast("Provider rate limit reached. Try again later.", "error");
        } else if (res.status === 502 || res.status === 504 || res.status === 503) {
          addToast("Could not verify the key right now.", "error");
        } else {
          addToast("Failed to save key", "error");
        }
      }
    } catch {
      addToast("Network error saving key", "error");
    } finally {
      savingRef.current = false;
      setIsSaving(false);
    }
  };

  const handleDeleteKey = async (providerName: string) => {
    if (!confirm(`Remove ${providerName} key?`)) return;
    try {
      const res = await fetchWithAuth(`/keys/${providerName}`, { method: "DELETE" });
      if (res.ok) {
        fetchKeys();
        addToast("Key removed", "success");
      } else {
        addToast("Failed to remove key", "error");
      }
    } catch {
      addToast("Network error", "error");
    }
  };

  const handleSignOut = async () => {
    try {
      const res = await fetchWithAuth("/auth/logout", { method: "POST" });
      resetCsrfToken();
      if (res.ok) router.push("/login");
      else addToast("Failed to sign out", "error");
    } catch {
      addToast("Network error during sign out", "error");
    }
  };

  const handleDeleteAccount = async (e: React.FormEvent) => {
    e.preventDefault();
    if (deletingRef.current || !accountPassword) return;
    if (!confirm("Permanently delete your account, saved keys, and all conversations? This cannot be undone.")) return;
    deletingRef.current = true;
    setIsDeletingAccount(true);
    try {
      const res = await fetchWithAuth("/auth/account", {
        method: "DELETE",
        body: JSON.stringify({ password: accountPassword }),
      });
      if (res.ok) {
        resetCsrfToken();
        router.push("/login");
        return;
      }
      const data = await res.json().catch(() => null);
      addToast(data?.detail || "Could not delete the account", "error");
    } catch {
      addToast("Network error deleting account", "error");
    } finally {
      deletingRef.current = false;
      setIsDeletingAccount(false);
    }
  };

  const providerOptions = [
    { value: "groq", label: "Groq" },
    { value: "gemini", label: "Google Gemini" },
    { value: "anthropic", label: "Anthropic (Claude)" }
  ];

  // Improved input classes — same contrast fix as login
  const inputClasses = "w-full px-4 py-2.5 rounded-lg bg-zinc-800/40 border border-zinc-700/50 focus:border-zinc-500 focus:bg-zinc-800/60 focus:ring-2 focus:ring-zinc-500/30 outline-none text-zinc-100 text-sm transition-all placeholder:text-zinc-500 font-mono shadow-inner shadow-zinc-950/20";

  return (
    <div className="flex min-h-screen flex-col items-center justify-center bg-zinc-950 text-zinc-50 font-sans px-4">
      <div className="w-full max-w-[420px] p-8 bg-zinc-900/50 rounded-2xl shadow-2xl border border-zinc-800/80 backdrop-blur-sm">
        <div className="flex justify-between items-center mb-6">
          <h1 className="text-xl font-semibold tracking-tight flex items-center gap-2">
            <Settings2 size={20} className="text-zinc-400" />
            Workspace Settings
          </h1>
          <button 
            onClick={() => router.push("/")} 
            className="text-zinc-500 hover:text-zinc-200 transition-colors p-1.5 rounded-md hover:bg-zinc-800/50 focus-visible:ring-2 focus-visible:ring-zinc-500 outline-none" 
            aria-label="Close settings"
          >
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
            <ul className="space-y-2.5" aria-label="Configured API keys">
              {configuredKeys.map((k, i) => (
                <li key={i} className="flex justify-between items-center text-sm px-3 py-2.5 bg-zinc-950/50 border border-zinc-800/50 rounded-lg">
                  <span className="capitalize font-medium text-zinc-200">{k.provider_name}</span>
                  <div className="flex items-center gap-3">
                    <span className="text-zinc-400 flex items-center gap-1.5 text-xs font-mono">
                      <span className="w-1.5 h-1.5 bg-green-500 rounded-full" aria-hidden="true"></span>
                      {k.masked_key}
                    </span>
                    <button 
                      onClick={() => handleDeleteKey(k.provider_name)}
                      className="text-zinc-500 hover:text-red-400 transition-colors p-1 rounded-md focus-visible:ring-2 focus-visible:ring-zinc-500 outline-none"
                      aria-label={`Remove ${k.provider_name} key`}
                    >
                      <Trash2 size={14} />
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
              label="Provider"
            />
            <div className="flex flex-col gap-1.5">
              <label htmlFor="api-key-input" className="text-xs font-medium text-zinc-400 uppercase tracking-wider">API Key</label>
              <input 
                id="api-key-input"
                type="password" 
                placeholder="sk-..." 
                className={inputClasses} 
                value={key} onChange={e => setKey(e.target.value)}
                autoComplete="off"
              />
            </div>
            <button 
              type="submit" 
              disabled={isSaving}
              className="w-full py-2.5 mt-1 bg-zinc-100 hover:bg-white text-zinc-950 font-medium rounded-lg transition-colors text-sm shadow-sm disabled:opacity-50 focus-visible:ring-2 focus-visible:ring-zinc-400 focus-visible:ring-offset-2 focus-visible:ring-offset-zinc-900 outline-none cursor-pointer"
            >
              {isSaving ? "Saving…" : "Save Provider Key"}
            </button>
          </div>
        </form>

        <div className="mt-8 pt-6 border-t border-zinc-800">
          <h2 className="text-sm font-medium text-red-400/90 uppercase tracking-wider mb-2">Danger Zone</h2>
          {!showDeleteAccount ? (
            <button
              type="button"
              onClick={() => setShowDeleteAccount(true)}
              className="flex items-center gap-2 text-xs font-medium text-red-400 hover:text-red-300 transition-colors px-3 py-1.5 rounded-md hover:bg-red-950/30 focus-visible:ring-2 focus-visible:ring-red-500 outline-none"
            >
              <Trash2 size={14} />
              Delete account
            </button>
          ) : (
            <form onSubmit={handleDeleteAccount} className="flex flex-col gap-3">
              <p className="text-xs text-zinc-500 leading-relaxed">
                This permanently deletes your account, saved API keys, and every conversation. This cannot be undone.
              </p>
              <div className="flex flex-col gap-1.5">
                <label htmlFor="delete-password" className="text-xs font-medium text-zinc-400 uppercase tracking-wider">Confirm with your password</label>
                <input
                  id="delete-password"
                  type="password"
                  className={inputClasses}
                  value={accountPassword}
                  onChange={e => setAccountPassword(e.target.value)}
                  autoComplete="current-password"
                />
              </div>
              <div className="flex gap-2">
                <button
                  type="button"
                  onClick={() => { setShowDeleteAccount(false); setAccountPassword(""); }}
                  className="flex-1 py-2.5 border border-zinc-700 text-zinc-300 hover:bg-zinc-800/60 rounded-lg text-sm font-medium transition-colors focus-visible:ring-2 focus-visible:ring-zinc-500 outline-none"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={isDeletingAccount || !accountPassword}
                  className="flex-1 py-2.5 bg-red-500/90 hover:bg-red-500 text-white rounded-lg text-sm font-medium transition-colors disabled:opacity-50 focus-visible:ring-2 focus-visible:ring-red-400 outline-none"
                >
                  {isDeletingAccount ? "Deleting…" : "Delete account"}
                </button>
              </div>
            </form>
          )}
        </div>

        <div className="mt-6 pt-5 border-t border-zinc-800 flex justify-center">
          <button
            type="button"
            onClick={handleSignOut}
            className="flex items-center gap-2 text-xs font-medium text-zinc-500 hover:text-zinc-200 transition-colors px-3 py-1.5 rounded-md hover:bg-zinc-800/50 focus-visible:ring-2 focus-visible:ring-zinc-500 outline-none"
          >
            <LogOut size={14} />
            Sign out
          </button>
        </div>
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
