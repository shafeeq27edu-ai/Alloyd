"use client";
import React, { createContext, useContext, useState, useCallback, ReactNode } from "react";
import { X, CheckCircle2, AlertCircle, Info } from "lucide-react";

export type ToastType = "success" | "error" | "info";

export interface ToastMessage {
  id: string;
  message: string;
  type: ToastType;
}

interface ToastContextProps {
  addToast: (message: string, type?: ToastType) => void;
}

const ToastContext = createContext<ToastContextProps | undefined>(undefined);

export function useToast() {
  const context = useContext(ToastContext);
  if (!context) throw new Error("useToast must be used within ToastProvider");
  return context;
}

export function ToastProvider({ children }: { children: ReactNode }) {
  const [toasts, setToasts] = useState<ToastMessage[]>([]);

  const addToast = useCallback((message: string, type: ToastType = "info") => {
    const id = Math.random().toString(36).substr(2, 9);
    setToasts((prev) => [...prev, { id, message, type }]);
    
    setTimeout(() => {
      setToasts((prev) => prev.filter((t) => t.id !== id));
    }, 5000);
  }, []);

  const removeToast = (id: string) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  };

  return (
    <ToastContext.Provider value={{ addToast }}>
      {children}
      <div className="fixed bottom-6 right-6 z-[100] flex flex-col gap-3 pointer-events-none">
        {toasts.map((toast) => (
          <div
            key={toast.id}
            className={`pointer-events-auto flex items-center gap-3 px-4 py-3 min-w-[280px] max-w-[400px] rounded-xl shadow-2xl border backdrop-blur-md transition-all duration-300
              ${toast.type === "success" ? "bg-zinc-900/90 border-zinc-700 text-zinc-200" : ""}
              ${toast.type === "error" ? "bg-red-950/90 border-red-900/50 text-red-200" : ""}
              ${toast.type === "info" ? "bg-zinc-900/90 border-zinc-700/80 text-zinc-200" : ""}
            `}
            role="alert"
            aria-live="assertive"
          >
            {toast.type === "success" && <CheckCircle2 size={18} className="text-green-500 flex-shrink-0" />}
            {toast.type === "error" && <AlertCircle size={18} className="text-red-500 flex-shrink-0" />}
            {toast.type === "info" && <Info size={18} className="text-blue-500 flex-shrink-0" />}
            
            <p className="text-[13px] font-medium flex-1">{toast.message}</p>
            
            <button 
              onClick={() => removeToast(toast.id)}
              className={`p-1.5 rounded-lg transition-colors flex-shrink-0 
                ${toast.type === "success" ? "hover:bg-zinc-800 text-zinc-400" : ""}
                ${toast.type === "error" ? "hover:bg-red-900/50 text-red-300" : ""}
                ${toast.type === "info" ? "hover:bg-zinc-800 text-zinc-400" : ""}
              `}
              aria-label="Close"
            >
              <X size={14} />
            </button>
          </div>
        ))}
      </div>
    </ToastContext.Provider>
  );
}
