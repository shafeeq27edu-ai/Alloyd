"use client";
import { useState, useEffect, useRef } from "react";
import { useRouter } from "next/navigation";
import { API_BASE_URL, fetchWithAuth } from "@/lib/api";
import Sidebar from "@/components/Sidebar";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { Prism as SyntaxHighlighter } from "react-syntax-highlighter";
import { vscDarkPlus } from "react-syntax-highlighter/dist/esm/styles/prism";

type Message = { role: string; content: string; provider?: string; model?: string; mode?: string; category?: string };

export default function ChatPage() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [isStreaming, setIsStreaming] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const router = useRouter();
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const [mode, setMode] = useState("auto");
  const [selectedProvider, setSelectedProvider] = useState("groq");
  const [selectedModel, setSelectedModel] = useState("llama3-8b-8192");
  
  const [currentConversationId, setCurrentConversationId] = useState<string | null>(null);

  useEffect(() => {
    const checkAuth = async () => {
      try {
        await fetchWithAuth("/auth/me");
        const keysRes = await fetchWithAuth("/keys");
        if (keysRes.ok) {
          const keysData = await keysRes.json();
          if (!keysData.keys || keysData.keys.length === 0) {
            router.push("/settings?onboarding=true");
          }
        }
      } catch (e) {
        // fetchWithAuth will redirect on 401
      }
    };
    checkAuth();
  }, [router]);

  useEffect(() => {
    if (currentConversationId) {
      fetchWithAuth(`/conversations/${currentConversationId}/messages`)
        .then(res => res.json())
        .then(data => {
          setMessages(data.messages || []);
        });
    } else {
      setMessages([]);
    }
  }, [currentConversationId]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const handleInput = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setInput(e.target.value);
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, 200)}px`;
    }
  };

  const handleSend = async (messageText = input) => {
    if (!messageText.trim() || isStreaming) return;
    
    const userMsg = { role: "user", content: messageText };
    setMessages(prev => [...prev, userMsg, { role: "assistant", content: "" }]);
    if (messageText === input) {
      setInput("");
      if (textareaRef.current) textareaRef.current.style.height = 'auto';
    }
    setIsStreaming(true);
    setError(null);

    try {
      const payload: any = { mode, message: userMsg.content };
      if (mode === "manual") {
        payload.provider = selectedProvider;
        payload.model = selectedModel;
      }
      if (currentConversationId) {
        payload.conversation_id = currentConversationId;
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
                if (!currentConversationId) {
                  setCurrentConversationId(routingData.conversation_id);
                }
                setMessages(prev => {
                  const newMessages = [...prev];
                  const last = newMessages[newMessages.length - 1];
                  if (last.role === "assistant") {
                    last.provider = routingData.provider;
                    last.model = routingData.model;
                    last.mode = routingData.mode;
                    last.category = routingData.category;
                  }
                  return newMessages;
                });
              } catch (e) {}
            } else if (currentEvent === "error") {
              try {
                const errData = JSON.parse(dataStr);
                // Map known codes to user-friendly messages
                let userMsg = errData.detail;
                if (typeof errData.detail === 'object' && errData.detail.code) {
                  const codes: any = {
                    "INVALID_API_KEY": "The API key for this provider appears to be invalid or missing.",
                    "RATE_LIMIT": "This provider is temporarily rate limited. Please wait a moment.",
                    "TIMEOUT": "The request took too long. Please try again.",
                    "PROVIDER_UNAVAILABLE": "This AI provider is temporarily unavailable.",
                    "CAPABILITY_NOT_SUPPORTED": "The selected model cannot handle this type of request."
                  };
                  userMsg = codes[errData.detail.code] || errData.detail.message;
                }
                setError(userMsg);
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

  const skills = [
    { name: "Architect", prompt: "@architect Help me design a system architecture for..." },
    { name: "Writer", prompt: "@copywriter Draft a professional email to..." },
    { name: "Artist", prompt: "@artist Generate an image prompt for..." }
  ];

  return (
    <div className="flex h-screen bg-gray-950 text-gray-100 overflow-hidden font-sans">
      <Sidebar onSelect={setCurrentConversationId} currentId={currentConversationId} />
      
      <div className="flex-1 flex flex-col h-full bg-gray-900 relative">
        <header className="flex justify-between items-center p-4 bg-gray-900 border-b border-gray-800 shadow-sm z-10">
          <h1 className="text-2xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-blue-400 to-indigo-500 tracking-tight">Alloyd</h1>
        
          <div className="flex items-center gap-4">
            <div className="flex bg-gray-800 rounded-lg p-1 border border-gray-700 shadow-sm">
              <select 
                value={mode} 
                onChange={e => setMode(e.target.value)}
                className="bg-transparent px-3 py-1.5 rounded-md text-sm outline-none cursor-pointer focus:bg-gray-700 transition font-medium"
              >
                <option value="auto">✨ Auto Route</option>
                <option value="manual">Manual Select</option>
              </select>
              
              {mode === "manual" && (
                <>
                  <div className="w-px bg-gray-700 mx-1"></div>
                  <select 
                    value={selectedProvider} 
                    onChange={e => {
                      const newProvider = e.target.value;
                      setSelectedProvider(newProvider);
                      setSelectedModel(models[newProvider][0]);
                    }}
                    className="bg-transparent px-2 py-1.5 rounded-md text-sm outline-none capitalize cursor-pointer focus:bg-gray-700 transition"
                  >
                    {Object.keys(models).map(p => <option key={p} value={p}>{p}</option>)}
                  </select>
                  <select 
                    value={selectedModel} 
                    onChange={e => setSelectedModel(e.target.value)}
                    className="bg-transparent px-2 py-1.5 rounded-md text-sm outline-none cursor-pointer focus:bg-gray-700 transition max-w-[150px] truncate"
                  >
                    {models[selectedProvider].map(m => <option key={m} value={m}>{m}</option>)}
                  </select>
                </>
              )}
            </div>
            
            <button onClick={() => router.push("/settings")} className="text-gray-400 hover:text-white transition">
              <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M12.22 2h-.44a2 2 0 0 0-2 2v.18a2 2 0 0 1-1 1.73l-.43.25a2 2 0 0 1-2 0l-.15-.08a2 2 0 0 0-2.73.73l-.22.38a2 2 0 0 0 .73 2.73l.15.1a2 2 0 0 1 1 1.72v.51a2 2 0 0 1-1 1.74l-.15.09a2 2 0 0 0-.73 2.73l.22.38a2 2 0 0 0 2.73.73l.15-.08a2 2 0 0 1 2 0l.43.25a2 2 0 0 1 1 1.73V20a2 2 0 0 0 2 2h.44a2 2 0 0 0 2-2v-.18a2 2 0 0 1 1-1.73l.43-.25a2 2 0 0 1 2 0l.15.08a2 2 0 0 0 2.73-.73l.22-.39a2 2 0 0 0-.73-2.73l-.15-.08a2 2 0 0 1-1-1.74v-.5a2 2 0 0 1 1-1.74l.15-.09a2 2 0 0 0 .73-2.73l-.22-.38a2 2 0 0 0-2.73-.73l-.15.08a2 2 0 0 1-2 0l-.43-.25a2 2 0 0 1-1-1.73V4a2 2 0 0 0-2-2z"></path><circle cx="12" cy="12" r="3"></circle></svg>
            </button>
          </div>
        </header>

        <main className="flex-1 overflow-y-auto p-4 flex flex-col gap-6 w-full max-w-4xl mx-auto">
          {messages.length === 0 ? (
            <div className="flex flex-col items-center justify-center h-full text-center space-y-6">
              <div className="w-16 h-16 bg-gradient-to-br from-blue-500 to-purple-600 rounded-2xl flex items-center justify-center shadow-lg mb-4">
                <svg xmlns="http://www.w3.org/2000/svg" width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="m12 3-1.912 5.813a2 2 0 0 1-1.275 1.275L3 12l5.813 1.912a2 2 0 0 1 1.275 1.275L12 21l1.912-5.813a2 2 0 0 1 1.275-1.275L21 12l-5.813-1.912a2 2 0 0 1-1.275-1.275L12 3Z"/></svg>
              </div>
              <h2 className="text-3xl font-bold text-white tracking-tight">How can I help you today?</h2>
              
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mt-8 w-full max-w-3xl">
                {skills.map(skill => (
                  <button 
                    key={skill.name}
                    onClick={() => handleSend(skill.prompt)}
                    className="p-4 bg-gray-800 hover:bg-gray-700 border border-gray-700 rounded-xl text-left transition shadow-sm group"
                  >
                    <div className="font-semibold text-blue-400 group-hover:text-blue-300 transition mb-1">{skill.name}</div>
                    <div className="text-sm text-gray-400 truncate">{skill.prompt.replace(`@${skill.name.toLowerCase()} `, '')}</div>
                  </button>
                ))}
              </div>
            </div>
          ) : (
            messages.map((m, i) => (
              <div key={i} className={`flex w-full ${m.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                <div className={`p-5 rounded-2xl max-w-3xl shadow-sm ${
                  m.role === 'user' 
                    ? 'bg-blue-600 text-white rounded-tr-sm' 
                    : 'bg-gray-800 border border-gray-700 rounded-tl-sm w-full'
                }`}>
                  {m.role === 'assistant' && m.provider && (
                    <div className="text-xs font-mono text-gray-400 mb-3 flex items-center gap-2">
                      <span className="uppercase font-bold text-gray-300">{m.provider}</span>
                      <span>•</span>
                      <span className="truncate">{m.model}</span>
                      {m.category && (
                        <>
                          <span>•</span>
                          <span className="text-indigo-400">{m.category}</span>
                        </>
                      )}
                      {m.mode === 'auto' && <span className="ml-auto flex items-center gap-1 text-yellow-500 bg-yellow-500/10 px-2 py-0.5 rounded-full border border-yellow-500/20">✨ Auto</span>}
                    </div>
                  )}
                  <div className="prose prose-invert max-w-none prose-p:leading-relaxed prose-pre:bg-gray-900 prose-pre:border prose-pre:border-gray-700">
                    <ReactMarkdown
                      remarkPlugins={[remarkGfm]}
                      components={{
                        code({node, inline, className, children, ...props}: any) {
                          const match = /language-(\w+)/.exec(className || '')
                          return !inline && match ? (
                            <SyntaxHighlighter
                              style={vscDarkPlus as any}
                              language={match[1]}
                              PreTag="div"
                              className="rounded-lg !my-4 !bg-gray-950"
                              {...props}
                            >
                              {String(children).replace(/\n$/, '')}
                            </SyntaxHighlighter>
                          ) : (
                            <code className="bg-gray-900 text-pink-300 px-1.5 py-0.5 rounded text-sm font-mono" {...props}>
                              {children}
                            </code>
                          )
                        }
                      }}
                    >
                      {m.content}
                    </ReactMarkdown>
                  </div>
                </div>
              </div>
            ))
          )}
          {error && (
            <div className="flex items-center gap-3 p-4 rounded-xl bg-red-900/50 border border-red-800 text-red-200 self-center w-full max-w-3xl">
              <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><circle cx="12" cy="12" r="10"></circle><line x1="12" y1="8" x2="12" y2="12"></line><line x1="12" y1="16" x2="12.01" y2="16"></line></svg>
              <span>{error}</span>
            </div>
          )}
          <div ref={messagesEndRef} />
        </main>

        <footer className="p-4 bg-gray-900/80 backdrop-blur-md border-t border-gray-800 z-10 w-full relative">
          <form onSubmit={e => { e.preventDefault(); handleSend(); }} className="flex gap-2 w-full max-w-4xl mx-auto relative group">
            <textarea
              ref={textareaRef}
              value={input} 
              onChange={handleInput}
              onKeyDown={(e) => {
                if (e.key === 'Enter' && !e.shiftKey) {
                  e.preventDefault();
                  handleSend();
                }
              }}
              disabled={isStreaming}
              placeholder="Message Alloyd... (Shift+Enter for new line)" 
              className="flex-1 p-4 pr-14 rounded-xl bg-gray-800 border border-gray-700 focus:border-gray-600 focus:bg-gray-750 focus:ring-1 focus:ring-gray-500 outline-none resize-none overflow-hidden text-sm leading-relaxed transition shadow-inner"
              rows={1}
              style={{ minHeight: '56px', maxHeight: '200px' }}
            />
            <button 
              type="submit" 
              disabled={isStreaming || !input.trim()}
              className="absolute right-3 bottom-3 p-2 bg-blue-600 rounded-lg text-white font-bold hover:bg-blue-500 disabled:opacity-40 disabled:hover:bg-blue-600 transition shadow-sm"
            >
              <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><line x1="22" y1="2" x2="11" y2="13"></line><polygon points="22 2 15 22 11 13 2 9 22 2"></polygon></svg>
            </button>
          </form>
          <div className="text-center mt-2 text-xs text-gray-500">
            Alloyd BYOK Workspace • AI models can make mistakes.
          </div>
        </footer>
      </div>
    </div>
  );
}
