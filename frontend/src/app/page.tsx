"use client";
import { useState, useEffect, useRef } from "react";
import { useRouter } from "next/navigation";
import { fetchWithAuth } from "@/lib/api";
import { SSEParser, type SSEEvent } from "@/lib/sse";
import Sidebar, { type ConversationInfo } from "@/components/Sidebar";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { Prism as SyntaxHighlighter } from "react-syntax-highlighter";
import { vscDarkPlus } from "react-syntax-highlighter/dist/esm/styles/prism";
import { Menu, Settings, SendHorizontal, AlertCircle, Sparkles, Square, RotateCcw, Copy, Check } from "lucide-react";
import Select from "@/components/Select";
import { useToast } from "@/components/Toast";

type Message = { role: string; content: string; provider?: string; model?: string; mode?: string; category?: string };
type ModelOption = { id: string; name: string; capabilities: string[] };

export default function ChatPage() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [isStreaming, setIsStreaming] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const router = useRouter();
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const { addToast } = useToast();

  const [mode, setMode] = useState("auto");
  const [models, setModels] = useState<Record<string, ModelOption[]>>({});
  const [configuredProviders, setConfiguredProviders] = useState<string[]>([]);
  const [selectedProvider, setSelectedProvider] = useState("");
  const [selectedModel, setSelectedModel] = useState("");
  const [isSidebarOpen, setIsSidebarOpen] = useState(false);
  const [currentConversationId, setCurrentConversationId] = useState<string | null>(null);
  const streamedConversationIdRef = useRef<string | null>(null);
  // Which conversation the user is viewing, and which one the live stream
  // belongs to. When they differ, stream chunks must not touch the view.
  const activeConversationRef = useRef<string | null>(null);
  const streamTargetRef = useRef<string | null>(null);
  const abortRef = useRef<AbortController | null>(null);
  const lastUserTextRef = useRef("");
  const [copiedIndex, setCopiedIndex] = useState<number | null>(null);

  useEffect(() => {
    const checkAuth = async () => {
      try {
        await fetchWithAuth("/auth/me");
        const keysRes = await fetchWithAuth("/keys/");
        let availableProviders: string[] = [];
        if (keysRes.ok) {
          const keysData = await keysRes.json();
          availableProviders = (keysData.keys || []).map(
            (k: { provider_name: string }) => k.provider_name
          );
          setConfiguredProviders(availableProviders);
          if (availableProviders.length === 0) {
            router.push("/settings?onboarding=true");
          }
        }

        const modelsRes = await fetchWithAuth("/models");
        if (modelsRes.ok) {
          const modelsData = await modelsRes.json();
          const catalog: Record<string, ModelOption[]> = {};
          for (const provider of modelsData.providers || []) {
            catalog[provider.provider] = provider.models;
          }
          setModels(catalog);
          const firstProvider =
            Object.keys(catalog).find((p) => availableProviders.includes(p)) ??
            Object.keys(catalog)[0];
          if (firstProvider && catalog[firstProvider].length > 0) {
            setSelectedProvider(firstProvider);
            setSelectedModel(catalog[firstProvider][0].id);
          }
        }
      } catch (err) {
        // fetchWithAuth will redirect on 401
        console.error(err);
      }
    };
    checkAuth();
  }, [router]);

  const handleSelectConversation = (conversation: ConversationInfo | null) => {
    activeConversationRef.current = conversation?.id ?? null;
    streamedConversationIdRef.current = null;
    setError(null);
    setCurrentConversationId(conversation?.id ?? null);
    if (conversation) {
      setMode(conversation.mode === "manual" ? "manual" : "auto");
      if (conversation.mode === "manual" && conversation.provider && conversation.model) {
        setSelectedProvider(conversation.provider);
        setSelectedModel(conversation.model);
      }
    }
  };

  useEffect(() => {
    if (!currentConversationId) {
      // eslint-disable-next-line react-hooks/set-state-in-effect
      setMessages([]);
      return;
    }
    // A stream created this conversation; its messages are already in state.
    if (streamedConversationIdRef.current === currentConversationId) return;

    let cancelled = false;
    fetchWithAuth(`/conversations/${currentConversationId}/messages`)
      .then(res => (res.ok ? res.json() : null))
      .then(data => {
        if (!cancelled && data) setMessages(data.messages || []);
      })
      .catch(() => {});
    return () => { cancelled = true; };
  }, [currentConversationId]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const dropEmptyAssistant = () => {
    setMessages(prev => {
      if (activeConversationRef.current !== streamTargetRef.current) return prev;
      const last = prev[prev.length - 1];
      return last && last.role === "assistant" && !last.content ? prev.slice(0, -1) : prev;
    });
  };

  const handleInput = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setInput(e.target.value);
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, 200)}px`;
    }
  };

  const runChat = async ({ message, regenerate = false }: { message: string; regenerate?: boolean }) => {
    if (isStreaming) return;
    if (!regenerate && !message.trim()) return;

    lastUserTextRef.current = message;
    if (regenerate) {
      setMessages(prev => [...prev, { role: "assistant", content: "" }]);
    } else {
      setMessages(prev => [...prev, { role: "user", content: message }, { role: "assistant", content: "" }]);
    }
    setIsStreaming(true);
    setError(null);
    streamTargetRef.current = currentConversationId;

    const controller = new AbortController();
    abortRef.current = controller;

    try {
      const payload: Record<string, string | boolean> = { mode, message };
      if (regenerate) payload.regenerate = true;
      if (mode === "manual") {
        payload.provider = selectedProvider;
        payload.model = selectedModel;
      }
      if (currentConversationId) {
        payload.conversation_id = currentConversationId;
      }

      const response = await fetchWithAuth("/chat/", {
        method: "POST",
        body: JSON.stringify(payload),
        signal: controller.signal,
      });

      if (!response.ok && response.status !== 401) {
        const err = await response.json().catch(() => null);
        setError(err?.detail || `Request failed (${response.status})`);
        dropEmptyAssistant();
        return;
      }

      const reader = response.body?.getReader();
      const decoder = new TextDecoder("utf-8");
      if (!reader) return;

      const parser = new SSEParser();
      let stopped = false;
      let noticeShown = false;

      const handleEvent = (ev: SSEEvent) => {
        if (ev.event === "done") {
          stopped = true;
          return;
        }

        if (ev.event === "error") {
          try {
            const errData = JSON.parse(ev.data);
            const detail = errData.detail ?? errData;
            let userMsg = typeof detail === "string" ? detail : detail?.message || "The request failed.";
            if (detail && typeof detail === "object" && detail.code) {
              const codes: Record<string, string> = {
                "INVALID_API_KEY": "The API key for this provider appears to be invalid or missing.",
                "RATE_LIMIT": "This provider is temporarily rate limited. Please wait a moment.",
                "TIMEOUT": "The request took too long. Please try again.",
                "PROVIDER_UNAVAILABLE": "This AI provider is temporarily unavailable.",
                "MODEL_UNAVAILABLE": "The selected model is no longer available.",
                "CAPABILITY_NOT_SUPPORTED": "The selected model cannot handle this type of request."
              };
              userMsg = codes[detail.code] || detail.message || userMsg;
            }
            setError(userMsg);
            dropEmptyAssistant();
            addToast(typeof userMsg === "string" ? userMsg : "An error occurred", "error");
          } catch {
            setError(ev.data);
          }
          stopped = true;
          return;
        }

        if (ev.event === "routing") {
          try {
            const routingData = JSON.parse(ev.data);
            if (!currentConversationId && activeConversationRef.current === null) {
              streamedConversationIdRef.current = routingData.conversation_id;
              streamTargetRef.current = routingData.conversation_id;
              activeConversationRef.current = routingData.conversation_id;
              setCurrentConversationId(routingData.conversation_id);
              window.dispatchEvent(new Event("alloyd:conversations-changed"));
            }
            if (routingData.notice && !noticeShown) {
              noticeShown = true;
              addToast(routingData.notice, "info");
            }
            setMessages(prev => {
              if (activeConversationRef.current !== streamTargetRef.current) return prev;
              const last = prev[prev.length - 1];
              if (!last || last.role !== "assistant") return prev;
              return [
                ...prev.slice(0, -1),
                {
                  ...last,
                  provider: routingData.provider,
                  model: routingData.model,
                  mode: routingData.mode,
                  category: routingData.category,
                },
              ];
            });
          } catch { /* ignore parse errors */ }
          return;
        }

        if (ev.event === "message") {
          try {
            const data = JSON.parse(ev.data);
            // Updaters must stay pure: StrictMode runs them twice in dev, and
            // mutating `last` would append every token twice.
            setMessages(prev => {
              if (activeConversationRef.current !== streamTargetRef.current) return prev;
              const last = prev[prev.length - 1];
              if (!last || last.role !== "assistant") return prev;
              return [...prev.slice(0, -1), { ...last, content: last.content + data.content }];
            });
          } catch { /* ignore parse errors */ }
        }
      };

      while (!stopped) {
        const { value, done } = await reader.read();
        if (done) break;
        for (const ev of parser.push(decoder.decode(value, { stream: true }))) {
          handleEvent(ev);
          if (stopped) break;
        }
      }

      if (!stopped) {
        for (const ev of parser.finish()) {
          handleEvent(ev);
          if (stopped) break;
        }
      }

      if (stopped) {
        await reader.cancel().catch(() => {});
      }
    } catch (err) {
      if (err instanceof DOMException && err.name === "AbortError") {
        dropEmptyAssistant();
        addToast("Generation stopped", "info");
      } else {
        setError("Network error — unable to reach the server.");
        addToast("Network error — please check your connection.", "error");
      }
    } finally {
      abortRef.current = null;
      setIsStreaming(false);
    }
  };

  const handleSend = async (messageText = input) => {
    if (!messageText.trim() || isStreaming) return;
    if (messageText === input) {
      setInput("");
      if (textareaRef.current) textareaRef.current.style.height = 'auto';
    }
    await runChat({ message: messageText });
  };

  const handleStop = () => {
    abortRef.current?.abort();
  };

  const handleRegenerate = () => {
    if (isStreaming || !currentConversationId) return;
    const last = messages[messages.length - 1];
    if (!last || last.role !== "assistant") return;
    const lastUser = [...messages].reverse().find(m => m.role === "user");
    if (!lastUser) return;
    setMessages(prev => prev.slice(0, -1));
    void runChat({ message: lastUser.content, regenerate: true });
  };

  const handleRetry = () => {
    if (isStreaming) return;
    const text = lastUserTextRef.current;
    if (!text) return;
    if (currentConversationId) {
      void runChat({ message: text, regenerate: true });
    } else {
      const last = messages[messages.length - 1];
      if (last?.role === "user" && last.content === text) {
        setMessages(prev => prev.slice(0, -1));
      }
      void handleSend(text);
    }
  };

  const handleCopy = async (index: number, content: string) => {
    try {
      await navigator.clipboard.writeText(content);
      setCopiedIndex(index);
      setTimeout(() => setCopiedIndex(null), 1500);
    } catch {
      addToast("Could not copy to clipboard", "error");
    }
  };

  const skills = [
    { name: "Code Review", prompt: "@reviewer Review this code: " },
    { name: "Explain Code", prompt: "@explainer How does this work? " },
    { name: "Summarization", prompt: "@summarizer Summarize the following: " },
    { name: "Writing", prompt: "@writer Draft a professional email: " },
    { name: "Brainstorming", prompt: "@brainstormer Give me ideas for: " },
    { name: "Research Analysis", prompt: "@researcher Research and analyze: " }
  ];

  const manualProviders = Object.keys(models).filter(p => configuredProviders.includes(p));

  return (
    <div className="flex h-screen bg-zinc-950 text-zinc-50 overflow-hidden font-sans selection:bg-zinc-800 selection:text-white">
      <Sidebar 
        onSelect={handleSelectConversation} 
        currentId={currentConversationId} 
        isOpen={isSidebarOpen}
        onClose={() => setIsSidebarOpen(false)}
      />
      
      <div className="flex-1 flex flex-col h-full relative min-w-0">
        <header className="flex justify-between items-center px-4 sm:px-6 py-4 z-10 w-full">
          <div className="flex items-center gap-3 min-w-0">
            <button 
              onClick={() => setIsSidebarOpen(true)} 
              className="md:hidden p-2 -ml-1 text-zinc-500 hover:text-zinc-200 hover:bg-zinc-800/50 rounded-md transition-colors focus-visible:ring-2 focus-visible:ring-zinc-500 outline-none" 
              aria-label="Open sidebar"
            >
              <Menu size={18} />
            </button>
            <h1 className="text-sm font-semibold tracking-wide text-zinc-300">Alloyd</h1>
            <span className="text-zinc-600" aria-hidden="true">/</span>
            <span className="text-sm text-zinc-500 truncate max-w-[200px]">
              {currentConversationId ? "Active Session" : "New Session"}
            </span>
          </div>
        
          <div className="flex items-center gap-2">
            <button 
              onClick={() => router.push("/settings")} 
              className="p-2 text-zinc-500 hover:text-zinc-200 hover:bg-zinc-800/50 rounded-md transition-colors focus-visible:ring-2 focus-visible:ring-zinc-500 outline-none" 
              aria-label="Settings"
            >
              <Settings size={18} />
            </button>
          </div>
        </header>

        <main className="flex-1 overflow-y-auto px-4 pb-32 flex flex-col w-full max-w-3xl mx-auto scroll-smooth">
          {messages.length === 0 ? (
            <div className="flex flex-col justify-center h-full max-w-2xl mx-auto w-full pt-10">
              <h2 className="text-2xl font-medium text-zinc-100 tracking-tight mb-2">Good afternoon.</h2>
              <p className="text-zinc-500 mb-10 text-sm">What would you like to build today?</p>
              
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 w-full" role="list" aria-label="Quick start skills">
                {skills.map(skill => (
                  <button 
                    key={skill.name}
                    role="listitem"
                    onClick={() => handleSend(skill.prompt)}
                    className="p-4 bg-zinc-900/40 hover:bg-zinc-800/60 border border-zinc-800/60 hover:border-zinc-700 rounded-xl text-left transition-all group flex flex-col gap-1 focus-visible:ring-2 focus-visible:ring-zinc-500 focus-visible:ring-offset-1 focus-visible:ring-offset-zinc-950 outline-none"
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
                    <div className="flex flex-col w-full min-w-0">
                      <div className="flex items-center gap-2 mb-2 min-h-[20px] text-xs font-mono text-zinc-500">
                        {m.provider && (
                          <div className="flex items-center gap-2 opacity-0 group-hover:opacity-100 transition-opacity">
                            <span className="uppercase text-zinc-400 font-medium">{m.provider}</span>
                            <span className="text-zinc-700" aria-hidden="true">/</span>
                            <span>{m.model}</span>
                            {m.category && (
                              <>
                                <span className="text-zinc-700" aria-hidden="true">/</span>
                                <span className="text-zinc-400">{m.category}</span>
                              </>
                            )}
                            {m.mode === 'auto' && (
                              <span className="ml-2 flex items-center gap-1 text-zinc-400 bg-zinc-900 px-1.5 py-0.5 rounded border border-zinc-800 text-[11px]">
                                <Sparkles size={10} />
                                Auto
                              </span>
                            )}
                          </div>
                        )}
                        {m.content && (
                          <div className="ml-auto flex items-center gap-1 opacity-0 group-hover:opacity-100 focus-within:opacity-100 transition-opacity">
                            <button
                              onClick={() => handleCopy(i, m.content)}
                              className="p-1.5 text-zinc-500 hover:text-zinc-200 hover:bg-zinc-800/60 rounded-md transition-colors focus-visible:ring-2 focus-visible:ring-zinc-500 outline-none"
                              aria-label={copiedIndex === i ? "Copied" : "Copy response"}
                            >
                              {copiedIndex === i ? <Check size={13} /> : <Copy size={13} />}
                            </button>
                            {i === messages.length - 1 && !isStreaming && (
                              <button
                                onClick={handleRegenerate}
                                className="p-1.5 text-zinc-500 hover:text-zinc-200 hover:bg-zinc-800/60 rounded-md transition-colors focus-visible:ring-2 focus-visible:ring-zinc-500 outline-none"
                                aria-label="Regenerate response"
                              >
                                <RotateCcw size={13} />
                              </button>
                            )}
                          </div>
                        )}
                      </div>
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
            <div 
              className="flex items-start gap-3 p-4 rounded-xl bg-red-950/50 border border-red-900/50 text-red-300 self-center w-full max-w-2xl mt-4 text-[13px] font-medium leading-snug" 
              role="alert"
              aria-live="assertive"
            >
              <AlertCircle size={16} className="mt-0.5 flex-shrink-0 text-red-400" />
              <span>{typeof error === 'string' ? error : 'An unexpected error occurred.'}</span>
              <button
                onClick={handleRetry}
                disabled={isStreaming}
                className="ml-auto shrink-0 px-3 py-1.5 rounded-lg border border-red-900/60 text-red-200 hover:bg-red-900/30 disabled:opacity-40 transition-colors focus-visible:ring-2 focus-visible:ring-red-400 outline-none"
              >
                Retry
              </button>
            </div>
          )}
          <div ref={messagesEndRef} />
        </main>

        <div className="absolute bottom-0 left-0 right-0 bg-gradient-to-t from-zinc-950 via-zinc-950/90 to-transparent pt-10 pb-6 px-4">
          <form onSubmit={e => { e.preventDefault(); handleSend(); }} className="max-w-3xl mx-auto relative flex flex-col bg-zinc-900/80 border border-zinc-800/80 rounded-2xl shadow-xl backdrop-blur-md focus-within:border-zinc-600 transition-colors">
            
            <div className="flex flex-wrap items-center gap-2 px-4 pt-3 pb-1 border-b border-zinc-800/50">
              <Select 
                options={[{value: "auto", label: "Auto Route"}, {value: "manual", label: "Manual Select"}]}
                value={mode} 
                onChange={setMode}
                variant="inline"
                label="Routing mode"
              />
              
              {mode === "manual" && (
                <div className="flex flex-wrap items-center gap-2 text-xs font-mono text-zinc-500">
                  <span aria-hidden="true">/</span>
                  <Select 
                    options={manualProviders.map(p => ({value: p, label: p}))}
                    value={selectedProvider} 
                    onChange={val => {
                      setSelectedProvider(val);
                      setSelectedModel(models[val]?.[0]?.id ?? "");
                    }}
                    variant="inline"
                    label="Provider"
                  />
                  <span aria-hidden="true">/</span>
                  <Select 
                    options={(models[selectedProvider] ?? []).map(m => ({value: m.id, label: m.name}))}
                    value={selectedModel} 
                    onChange={setSelectedModel}
                    variant="inline"
                    label="Model"
                  />
                </div>
              )}
            </div>

            <div className="relative flex items-end">
              <label htmlFor="chat-input" className="sr-only">Message input</label>
              <textarea
                id="chat-input"
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
              {isStreaming ? (
                <button
                  type="button"
                  onClick={handleStop}
                  className="mb-3 mr-3 p-2.5 bg-zinc-100 rounded-xl text-zinc-900 hover:bg-white transition-all flex-shrink-0 focus-visible:ring-2 focus-visible:ring-zinc-400 focus-visible:ring-offset-2 focus-visible:ring-offset-zinc-900 outline-none cursor-pointer"
                  aria-label="Stop generating"
                >
                  <Square size={18} fill="currentColor" />
                </button>
              ) : (
                <button
                  type="submit"
                  disabled={!input.trim()}
                  className="mb-3 mr-3 p-2.5 bg-zinc-100 rounded-xl text-zinc-900 hover:bg-white disabled:opacity-30 disabled:hover:bg-zinc-100 transition-all flex-shrink-0 focus-visible:ring-2 focus-visible:ring-zinc-400 focus-visible:ring-offset-2 focus-visible:ring-offset-zinc-900 outline-none cursor-pointer"
                  aria-label="Send message"
                >
                  <SendHorizontal size={18} />
                </button>
              )}
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
