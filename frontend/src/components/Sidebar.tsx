"use client";
import { useEffect, useState } from "react";
import { fetchWithAuth } from "@/lib/api";

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
  currentId 
}: { 
  onSelect: (id: string | null) => void;
  currentId: string | null;
}) {
  const [conversations, setConversations] = useState<ConversationInfo[]>([]);

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
    // Refresh periodically or expose a ref to refresh on new chat
    const interval = setInterval(loadConversations, 5000);
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="w-64 bg-gray-900 border-r border-gray-800 flex flex-col h-full text-gray-300">
      <div className="p-4 border-b border-gray-800">
        <button 
          onClick={() => onSelect(null)}
          className="w-full py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg text-sm font-semibold transition"
        >
          + New Chat
        </button>
      </div>
      
      <div className="flex-1 overflow-y-auto p-2 space-y-1">
        {conversations.map(c => (
          <div key={c.id} className={`group flex items-center w-full rounded-lg text-sm transition ${currentId === c.id ? 'bg-gray-800 text-white font-medium' : 'hover:bg-gray-800'}`}>
            <button
              onClick={() => onSelect(c.id)}
              className="flex-1 text-left px-3 py-2 truncate"
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
                  }
                } catch (err) {
                  console.error(err);
                }
              }}
              className="opacity-0 group-hover:opacity-100 p-2 text-gray-500 hover:text-red-400 transition"
              title="Delete conversation"
            >
              <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M3 6h18"></path><path d="M19 6v14c0 1-1 2-2 2H7c-1 0-2-1-2-2V6"></path><path d="M8 6V4c0-1 1-2 2-2h4c1 0 2 1 2 2v2"></path></svg>
            </button>
          </div>
        ))}
        {conversations.length === 0 && (
          <p className="text-xs text-gray-500 text-center mt-4">No history yet</p>
        )}
      </div>
      
      <div className="p-4 border-t border-gray-800">
        <button
          onClick={async () => {
            try {
              const res = await fetchWithAuth("/auth/logout", { method: "POST" });
              if (res.ok) {
                window.location.href = "/login";
              }
            } catch (err) {
              console.error(err);
            }
          }}
          className="w-full py-2 bg-gray-800 hover:bg-gray-700 text-gray-300 rounded-lg text-sm font-semibold transition flex items-center justify-center gap-2"
        >
          <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"></path><polyline points="16 17 21 12 16 7"></polyline><line x1="21" y1="12" x2="9" y2="12"></line></svg>
          Logout
        </button>
      </div>
    </div>
  );
}
