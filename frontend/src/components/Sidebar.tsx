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

  useEffect(() => {
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
          <button
            key={c.id}
            onClick={() => onSelect(c.id)}
            className={`w-full text-left px-3 py-2 rounded-lg text-sm truncate transition ${currentId === c.id ? 'bg-gray-800 text-white font-medium' : 'hover:bg-gray-800'}`}
          >
            {c.title || "New Conversation"}
          </button>
        ))}
        {conversations.length === 0 && (
          <p className="text-xs text-gray-500 text-center mt-4">No history yet</p>
        )}
      </div>
    </div>
  );
}
