"use client";
import { useEffect, useState } from "react";
import { fetchWithAuth } from "@/lib/api";
import { MessageSquarePlus, Trash2, LogOut, X } from "lucide-react";
import { useToast } from "@/components/Toast";

type ConversationInfo = {
  id: string;
  title: string;
  mode: string;
  provider: string;
  model: string;
  created_at: string;
};

export default function Sidebar({ 
  onSelect, 
  currentId,
  isOpen,
  onClose
}: { 
  onSelect: (id: string | null) => void;
  currentId: string | null;
  isOpen: boolean;
  onClose: () => void;
}) {
  const [conversations, setConversations] = useState<ConversationInfo[]>([]);
  const { addToast } = useToast();

  useEffect(() => {
    const loadConversations = async () => {
      try {
        const res = await fetchWithAuth("/conversations");
        if (res.ok) {
          const data = await res.json();
          setConversations(data.conversations || []);
        }
      } catch (e) {
        console.error(e);
      }
    };

    loadConversations();
    const interval = setInterval(loadConversations, 5000);
    return () => clearInterval(interval);
  }, []);

  useEffect(() => {
    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === "Escape" && isOpen) {
        onClose();
      }
    };
    document.addEventListener("keydown", handleEscape);
    return () => document.removeEventListener("keydown", handleEscape);
  }, [isOpen, onClose]);

  return (
    <>
      <div 
        className={`fixed inset-0 z-40 bg-zinc-950/80 backdrop-blur-sm transition-opacity md:hidden ${isOpen ? 'opacity-100' : 'opacity-0 pointer-events-none'}`} 
        onClick={onClose}
        aria-hidden="true"
      />
      
      <div className={`fixed inset-y-0 left-0 z-50 w-72 md:w-64 bg-zinc-950 border-r border-zinc-800/50 flex flex-col h-full text-zinc-300 font-sans transform transition-transform md:translate-x-0 md:static ${isOpen ? 'translate-x-0' : '-translate-x-full'}`}>
        <div className="p-4 border-b border-zinc-800/50 flex items-center gap-2">
          <button 
            onClick={() => {
              onSelect(null);
              if (window.innerWidth < 768) onClose();
            }}
            className="flex-1 py-2.5 bg-zinc-900 hover:bg-zinc-800 border border-zinc-800 text-zinc-100 rounded-lg text-sm font-medium transition-colors shadow-sm flex items-center justify-center gap-2"
          >
            <MessageSquarePlus size={16} />
            New Chat
          </button>
          
          <button 
            onClick={onClose}
            className="md:hidden p-2.5 text-zinc-500 hover:text-zinc-200 hover:bg-zinc-800 rounded-lg transition-colors border border-transparent hover:border-zinc-700"
            aria-label="Close sidebar"
          >
            <X size={18} />
          </button>
        </div>
        
        <div className="flex-1 overflow-y-auto p-3 space-y-0.5 custom-scrollbar">
          {conversations.map(c => (
            <div key={c.id} className={`group flex items-center w-full rounded-md text-sm transition-colors ${currentId === c.id ? 'bg-zinc-800/80 text-zinc-100 font-medium' : 'text-zinc-400 hover:bg-zinc-800/40 hover:text-zinc-200'}`}>
              <button
                onClick={() => {
                  onSelect(c.id);
                  if (window.innerWidth < 768) onClose();
                }}
                className="flex-1 text-left px-3 py-2.5 truncate"
              >
                {c.title || "New Conversation"}
              </button>
              <button
                onClick={async (e) => {
                  e.stopPropagation();
                  if (!confirm("Delete this conversation?")) return;
                  try {
                    const res = await fetchWithAuth(`/conversations/${c.id}`, { method: 'DELETE' });
                    if (res.ok) {
                      if (currentId === c.id) onSelect(null);
                      setConversations(prev => prev.filter(conv => conv.id !== c.id));
                      addToast("Conversation deleted", "success");
                    } else {
                      addToast("Failed to delete conversation", "error");
                    }
                  } catch (err) {
                    console.error(err);
                    addToast("Network error deleting conversation", "error");
                  }
                }}
                className="opacity-0 group-hover:opacity-100 p-2 text-zinc-500 hover:text-red-400 transition-colors"
                title="Delete conversation"
                aria-label={`Delete ${c.title || "conversation"}`}
              >
                <Trash2 size={14} />
              </button>
            </div>
          ))}
          {conversations.length === 0 && (
            <p className="text-xs text-zinc-600 text-center mt-6">No history yet</p>
          )}
        </div>
        
        <div className="p-3 border-t border-zinc-800/50">
          <button
            onClick={async () => {
              try {
                const res = await fetchWithAuth("/auth/logout", { method: "POST" });
                if (res.ok) {
                  window.location.href = "/login";
                } else {
                  addToast("Failed to sign out", "error");
                }
              } catch (err) {
                console.error(err);
                addToast("Network error during sign out", "error");
              }
            }}
            className="w-full py-2.5 px-3 text-zinc-500 hover:text-zinc-200 hover:bg-zinc-800/50 rounded-md text-sm font-medium transition-colors flex items-center gap-2"
          >
            <LogOut size={16} />
            Sign Out
          </button>
        </div>
      </div>
    </>
  );
}
