"use client";
import { useState, useEffect, useRef } from "react";
import { useRouter } from "next/navigation";
import { fetchWithAuth } from "@/lib/api";
import Sidebar from "@/components/Sidebar";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { Prism as SyntaxHighlighter } from "react-syntax-highlighter";
import { vscDarkPlus } from "react-syntax-highlighter/dist/esm/styles/prism";
import { Menu, Settings, SendHorizontal, AlertCircle } from "lucide-react";
import Select from "@/components/Select";
import { useToast } from "@/components/Toast";

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
  const [isSidebarOpen, setIsSidebarOpen] = useState(false);
  const { addToast } = useToast();
  
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
      } catch (err) {
        // fetchWithAuth will redirect on 401
        console.error(err);
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
      // eslint-disable-next-line react-hooks/set-state-in-effect
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
      const payload: Record<string, string> = { mode, message: userMsg.content };
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
              } catch {}
            } else if (currentEvent === "error") {
              try {
                const errData = JSON.parse(dataStr);
                // Map known codes to user-friendly messages
                let userMsg = errData.detail;
                if (typeof errData.detail === 'object' && errData.detail.code) {
                  const codes: Record<string, string> = {
                    "INVALID_API_KEY": "The API key for this provider appears to be invalid or missing.",
                    "RATE_LIMIT": "This provider is temporarily rate limited. Please wait a moment.",
                    "TIMEOUT": "The request took too long. Please try again.",
                    "PROVIDER_UNAVAILABLE": "This AI provider is temporarily unavailable.",
                    "CAPABILITY_NOT_SUPPORTED": "The selected model cannot handle this type of request."
                  };
                  userMsg = codes[errData.detail.code] || errData.detail.message;
                }
                setError(userMsg);
              } catch {
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
              } catch {}
            }
          }
        }
      }
    } catch {
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
    { name: "Code Review", prompt: "@reviewer Review this code: " },
    { name: "Explain Code", prompt: "@explainer How does this work? " },
    { name: "Summarization", prompt: "@summarizer Summarize the following: " },
    { name: "Writing", prompt: "@writer Draft a professional email: " },
    { name: "Brainstorming", prompt: "@brainstormer Give me ideas for: " },
    { name: "Research Analysis", prompt: "@researcher Research and analyze: " }
  ];

  return (
    <div className="flex h-screen bg-zinc-950 text-zinc-50 overflow-hidden font-sans selection:bg-zinc-800 selection:text-white">
      <Sidebar 
        onSelect={setCurrentConversationId} 
        currentId={currentConversationId} 
        isOpen={isSidebarOpen}
        onClose={() => setIsSidebarOpen(false)}
      />
      
      <div className="flex-1 flex flex-col h-full relative">
        <header className="flex justify-between items-center px-6 py-4 z-10 w-full">
          <div className="flex items-center gap-3">
            <button onClick={() => setIsSidebarOpen(true)} className="md:hidden p-1.5 -ml-2 text-zinc-500 hover:text-zinc-200 hover:bg-zinc-800/50 rounded-md transition-colors" aria-label="Open sidebar">
              <Menu size={18} />
            </button>
            <h1 className="text-sm font-semibold tracking-wide text-zinc-300">Alloyd</h1>
            <span className="text-zinc-600">/</span>
            <span className="text-sm text-zinc-500 truncate max-w-[200px]">
              {currentConversationId ? "Active Session" : "New Session"}
            </span>
          </div>
        
          <div className="flex items-center gap-3">
            <button onClick={() => router.push("/settings")} className="p-2 text-zinc-500 hover:text-zinc-200 hover:bg-zinc-800/50 rounded-md transition-colors" aria-label="Settings">
              <Settings size={18} />
            </button>
          </div>
        </header>

        <main className="flex-1 overflow-y-auto px-4 pb-32 flex flex-col w-full max-w-3xl mx-auto scroll-smooth">
          {messages.length === 0 ? (
            <div className="flex flex-col justify-center h-full max-w-2xl mx-auto w-full pt-10">
              <h2 className="text-2xl font-medium text-zinc-100 tracking-tight mb-2">Good afternoon.</h2>
              <p className="text-zinc-500 mb-10 text-sm">What would you like to build today?</p>
              
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 w-full">
                {skills.map(skill => (
                  <button 
                    key={skill.name}
                    onClick={() => handleSend(skill.prompt)}
                    className="p-4 bg-zinc-900/40 hover:bg-zinc-800/60 border border-zinc-800/60 hover:border-zinc-700 rounded-xl text-left transition-all group flex flex-col gap-1"
                  >
                    <div className="font-medium text-sm text-zinc-300 group-hover:text-zinc-100 transition-colors">{skill.name}</div>
                    <div className="text-xs text-zinc-500 truncate font-mono">{skill.prompt.replace(/^@\w+\s+/, '')}</div>
                  </button>
                ))}
              </div>
            </div>
          ) : (
            <div className="flex flex-col gap-8 py-6">
              {messages.map((m, i) => (
                <div key={i} className={`flex w-full group ${m.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                  {m.role === 'user' ? (
                    <div className="px-5 py-3.5 bg-zinc-800/80 text-zinc-100 rounded-2xl rounded-tr-sm max-w-[85%] text-[15px] leading-relaxed shadow-sm">
                      {m.content}
                    </div>
                  ) : (
                    <div className="flex flex-col w-full">
                      {m.provider && (
                        <div className="flex items-center gap-2 mb-2 text-xs font-mono text-zinc-500 opacity-0 group-hover:opacity-100 transition-opacity">
                          <span className="uppercase text-zinc-400 font-medium">{m.provider}</span>
                          <span className="text-zinc-700">/</span>
                          <span>{m.model}</span>
                          {m.category && (
                            <>
                              <span className="text-zinc-700">/</span>
                              <span className="text-zinc-400">{m.category}</span>
                            </>
                          )}
                          {m.mode === 'auto' && (
                            <span className="ml-2 flex items-center gap-1 text-zinc-400 bg-zinc-900 px-1.5 py-0.5 rounded border border-zinc-800">
                              <svg xmlns="http://www.w3.org/2000/svg" width="10" height="10" viewBox="0 0 24 24" fill="currentColor" stroke="none"><path d="M12 2l2.4 7.6 7.6 2.4-7.6 2.4-2.4 7.6-2.4-7.6-7.6-2.4 7.6-2.4z"/></svg> Auto
                            </span>
                          )}
                        </div>
                      )}
                      <div className="prose prose-invert prose-zinc max-w-none text-[15px] prose-p:leading-relaxed prose-pre:bg-zinc-900 prose-pre:border prose-pre:border-zinc-800/80 prose-pre:shadow-sm prose-code:text-zinc-300 prose-a:text-blue-400">
                        <ReactMarkdown
                          remarkPlugins={[remarkGfm]}
                          components={{
                            // eslint-disable-next-line @typescript-eslint/no-explicit-any, @typescript-eslint/no-unused-vars
                            code({node, inline, className, children, ...props}: any) {
                              const match = /language-(\w+)/.exec(className || '')
                              return !inline && match ? (
                                <SyntaxHighlighter
                                  // eslint-disable-next-line @typescript-eslint/no-explicit-any
                                  style={vscDarkPlus as any}
                                  language={match[1]}
                                  PreTag="div"
                                  className="rounded-xl !my-5 !bg-zinc-900 !text-sm border border-zinc-800/80"
                                  {...props}
                                >
                                  {String(children).replace(/\n$/, '')}
                                </SyntaxHighlighter>
                              ) : (
                                <code className="bg-zinc-800/60 text-zinc-200 px-1.5 py-0.5 rounded-md text-[13px] font-mono before:content-none after:content-none border border-zinc-700/50" {...props}>
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
                  )}
                </div>
              ))}
            </div>
          )}
          {error && (
            <div className="flex items-start gap-3 p-4 rounded-xl bg-red-950/50 border border-red-900/50 text-red-400 self-center w-full max-w-2xl mt-4 text-[13px] font-medium leading-snug" aria-live="assertive">
              <AlertCircle size={16} className="mt-0.5 flex-shrink-0" />
              <span>{error}</span>
            </div>
          )}
          <div ref={messagesEndRef} />
        </main>

        <div className="absolute bottom-0 left-0 right-0 bg-gradient-to-t from-zinc-950 via-zinc-950/90 to-transparent pt-10 pb-6 px-4">
          <form onSubmit={e => { e.preventDefault(); handleSend(); }} className="max-w-3xl mx-auto relative flex flex-col bg-zinc-900/80 border border-zinc-800/80 rounded-2xl shadow-xl backdrop-blur-md focus-within:border-zinc-600 transition-colors">
            
            <div className="flex items-center gap-2 px-4 pt-3 pb-1 border-b border-zinc-800/50">
              <Select 
                options={[{value: "auto", label: "Auto Route"}, {value: "manual", label: "Manual Select"}]}
                value={mode} 
                onChange={setMode}
                variant="inline"
              />
              
              {mode === "manual" && (
                <div className="flex items-center gap-2 text-xs font-mono text-zinc-500">
                  <span>/</span>
                  <Select 
                    options={Object.keys(models).map(p => ({value: p, label: p}))}
                    value={selectedProvider} 
                    onChange={val => {
                      setSelectedProvider(val);
                      setSelectedModel(models[val][0]);
                    }}
                    variant="inline"
                  />
                  <span>/</span>
                  <Select 
                    options={models[selectedProvider].map(m => ({value: m, label: m}))}
                    value={selectedModel} 
                    onChange={setSelectedModel}
                    variant="inline"
                  />
                </div>
              )}
            </div>

            <div className="relative flex items-end">
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
                placeholder="Ask Alloyd anything..." 
                className="flex-1 p-4 bg-transparent outline-none resize-none overflow-hidden text-[15px] leading-relaxed text-zinc-100 placeholder:text-zinc-500"
                rows={1}
                style={{ minHeight: '56px', maxHeight: '200px' }}
              />
              <button 
                type="submit" 
                disabled={isStreaming || !input.trim()}
                className="mb-3 mr-3 p-2.5 bg-zinc-100 rounded-xl text-zinc-900 hover:bg-white disabled:opacity-30 disabled:hover:bg-zinc-100 transition-all flex-shrink-0"
                aria-label="Send message"
              >
                <SendHorizontal size={18} />
              </button>
            </div>
          </form>
          <div className="text-center mt-3 text-[11px] text-zinc-600 font-medium tracking-wide">
            Alloyd BYOK Workspace • AI models can make mistakes.
          </div>
        </div>
      </div>
    </div>
  );
}
