"use client";
import { useState, useEffect, useRef } from "react";
import { useRouter } from "next/navigation";
import { API_BASE_URL } from "@/lib/api";

type Message = { role: string; content: string; provider?: string; model?: string; mode?: string };

export default function ChatPage() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [isStreaming, setIsStreaming] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const router = useRouter();
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const [mode, setMode] = useState("auto");
  const [selectedProvider, setSelectedProvider] = useState("groq");
  const [selectedModel, setSelectedModel] = useState("llama3-8b-8192");

  useEffect(() => {
    const checkAuth = async () => {
      try {
        const res = await fetchWithAuth("/auth/me");
      } catch (e) {
        // fetchWithAuth will redirect on 401
      }
    };
    checkAuth();
  }, [router]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const handleSend = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || isStreaming) return;
    
    const userMsg = { role: "user", content: input };
    setMessages(prev => [...prev, userMsg, { role: "assistant", content: "" }]);
    setInput("");
    setIsStreaming(true);
    setError(null);

    try {
      const payload: any = { mode, message: userMsg.content };
      if (mode === "manual") {
        payload.provider = selectedProvider;
        payload.model = selectedModel;
      }

      const response = await fetchWithAuth("/chat", {
        method: "POST",
        body: JSON.stringify(payload),
      });

      if (!response.ok && response.status !== 401) {
        const err = await response.json();
        setError(err.detail || "Request failed");
        setIsStreaming(false);
        return;
      }

      const reader = response.body?.getReader();
      const decoder = new TextDecoder("utf-8");
      if (!reader) return;

      let currentEvent = "";

      while (true) {
        const { value, done } = await reader.read();
        if (done) break;
        const chunk = decoder.decode(value);
        const lines = chunk.split("\n").filter(l => l.trim() !== "");
        for (const line of lines) {
          if (line.startsWith("event: ")) {
            currentEvent = line.slice(7).trim();
          } else if (line.startsWith("data: ")) {
            const dataStr = line.slice(6);
            if (currentEvent === "done") {
              break;
            } else if (currentEvent === "routing") {
              try {
                const routingData = JSON.parse(dataStr);
                setMessages(prev => {
                  const newMessages = [...prev];
                  const last = newMessages[newMessages.length - 1];
                  if (last.role === "assistant") {
                    last.provider = routingData.provider;
                    last.model = routingData.model;
                    last.mode = routingData.mode;
                  }
                  return newMessages;
                });
              } catch (e) {}
            } else if (currentEvent === "error") {
              try {
                const errData = JSON.parse(dataStr);
                setError(errData.detail);
              } catch (e) {
                setError(dataStr);
              }
              break;
            } else if (currentEvent === "message") {
              try {
                const data = JSON.parse(dataStr);
                setMessages(prev => {
                  const newMessages = [...prev];
                  const last = newMessages[newMessages.length - 1];
                  if (last.role === "assistant") {
                    last.content += data.content;
                  }
                  return newMessages;
                });
              } catch (e) {}
            }
          }
        }
      }
    } catch (e) {
      setError("Network error");
    } finally {
      setIsStreaming(false);
    }
  };

  const models: Record<string, string[]> = {
    groq: ["llama3-8b-8192", "llama3-70b-8192"],
    anthropic: ["claude-3-5-sonnet-20240620", "claude-3-haiku-20240307"],
    gemini: ["gemini-1.5-pro", "gemini-1.5-flash"]
  };

  return (
    <div className="flex flex-col h-screen bg-gray-900 text-white">
      <header className="flex justify-between items-center p-4 bg-gray-800 border-b border-gray-700">
        <h1 className="text-xl font-bold">Alloyd Chat</h1>
        
        <div className="flex items-center gap-4">
          <div className="flex gap-2">
            <select 
              value={mode} 
              onChange={e => setMode(e.target.value)}
              className="bg-gray-700 p-2 rounded text-sm outline-none"
            >
              <option value="auto">✨ Auto Route</option>
              <option value="manual">Manual Route</option>
            </select>
            
            {mode === "manual" && (
              <>
                <select 
                  value={selectedProvider} 
                  onChange={e => {
                    const newProvider = e.target.value;
                    setSelectedProvider(newProvider);
                    setSelectedModel(models[newProvider][0]);
                  }}
                  className="bg-gray-700 p-2 rounded text-sm outline-none capitalize"
                >
                  {Object.keys(models).map(p => <option key={p} value={p}>{p}</option>)}
                </select>
                <select 
                  value={selectedModel} 
                  onChange={e => setSelectedModel(e.target.value)}
                  className="bg-gray-700 p-2 rounded text-sm outline-none"
                >
                  {models[selectedProvider].map(m => <option key={m} value={m}>{m}</option>)}
                </select>
              </>
            )}
          </div>
          
          <button onClick={() => router.push("/settings")} className="text-blue-400 hover:underline">
            Settings
          </button>
        </div>
      </header>

      <main className="flex-1 overflow-y-auto p-4 flex flex-col gap-4">
        {messages.map((m, i) => (
          <div key={i} className={`p-4 rounded-lg max-w-2xl ${m.role === 'user' ? 'bg-blue-600 self-end' : 'bg-gray-800 self-start'}`}>
            {m.role === 'assistant' && m.provider && (
              <div className="text-xs text-gray-400 mb-2 border-b border-gray-700 pb-1 flex gap-2">
                <span className="uppercase font-bold text-blue-400">{m.provider}</span>
                <span>•</span>
                <span>{m.model}</span>
                {m.mode === 'auto' && <span className="ml-auto text-yellow-500">✨ Auto-Routed</span>}
              </div>
            )}
            <p className="whitespace-pre-wrap">{m.content}</p>
          </div>
        ))}
        {error && (
          <div className="p-4 rounded-lg bg-red-900 text-red-200 self-center">
            {error}
          </div>
        )}
        <div ref={messagesEndRef} />
      </main>

      <footer className="p-4 bg-gray-800 border-t border-gray-700">
        <form onSubmit={handleSend} className="flex gap-2 max-w-4xl mx-auto">
          <input 
            type="text" 
            value={input} 
            onChange={e => setInput(e.target.value)} 
            disabled={isStreaming}
            placeholder="Type a message..." 
            className="flex-1 p-3 rounded-lg bg-gray-700 border-none outline-none focus:ring-2 focus:ring-blue-500"
          />
          <button 
            type="submit" 
            disabled={isStreaming || !input.trim()}
            className="px-6 py-3 bg-blue-600 rounded-lg font-bold hover:bg-blue-700 disabled:opacity-50"
          >
            Send
          </button>
        </form>
      </footer>
    </div>
  );
}
