"use client";
import { useState, useRef, useEffect } from "react";
import { ChevronDown, Check } from "lucide-react";

export type SelectOption = {
  value: string;
  label: string;
};

export default function Select({
  options,
  value,
  onChange,
  disabled = false,
  className = "",
  variant = "default"
}: {
  options: SelectOption[];
  value: string;
  onChange: (val: string) => void;
  disabled?: boolean;
  className?: string;
  variant?: "default" | "inline";
}) {
  const [isOpen, setIsOpen] = useState(false);
  const [focusedIndex, setFocusedIndex] = useState(-1);
  const containerRef = useRef<HTMLDivElement>(null);
  const listboxRef = useRef<HTMLDivElement>(null);

  const selectedOption = options.find((o) => o.value === value) || options[0];

  useEffect(() => {
    const handleOutsideClick = (e: MouseEvent) => {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setIsOpen(false);
      }
    };
    if (isOpen) document.addEventListener("mousedown", handleOutsideClick);
    return () => document.removeEventListener("mousedown", handleOutsideClick);
  }, [isOpen]);

  useEffect(() => {
    if (isOpen) {
      setFocusedIndex(options.findIndex(o => o.value === value));
    }
  }, [isOpen, value, options]);

  useEffect(() => {
    if (isOpen && listboxRef.current && focusedIndex >= 0) {
      const optionEl = listboxRef.current.children[focusedIndex] as HTMLElement;
      if (optionEl) {
        optionEl.scrollIntoView({ block: "nearest" });
      }
    }
  }, [focusedIndex, isOpen]);

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (disabled) return;
    
    if (e.key === "Enter" || e.key === " ") {
      e.preventDefault();
      if (isOpen && focusedIndex >= 0) {
        onChange(options[focusedIndex].value);
        setIsOpen(false);
      } else {
        setIsOpen(true);
      }
    } else if (e.key === "Escape") {
      e.preventDefault();
      setIsOpen(false);
    } else if (e.key === "ArrowDown") {
      e.preventDefault();
      if (!isOpen) {
        setIsOpen(true);
      } else {
        setFocusedIndex(prev => (prev < options.length - 1 ? prev + 1 : prev));
      }
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      if (!isOpen) {
        setIsOpen(true);
      } else {
        setFocusedIndex(prev => (prev > 0 ? prev - 1 : prev));
      }
    } else if (e.key === "Tab") {
      setIsOpen(false);
    }
  };

  const buttonClasses = variant === "inline"
    ? `flex items-center gap-1 bg-transparent text-zinc-400 hover:text-zinc-200 text-xs font-medium outline-none cursor-pointer transition-colors rounded-sm focus-visible:ring-1 focus-visible:ring-zinc-500 focus-visible:text-zinc-200 ${disabled ? 'opacity-50 cursor-not-allowed' : ''}`
    : `w-full flex items-center justify-between gap-2 px-4 py-2.5 text-sm text-zinc-200 bg-zinc-950/50 border border-zinc-800 rounded-lg outline-none transition-colors focus:border-zinc-500 focus:ring-1 focus:ring-zinc-500 hover:border-zinc-700 ${disabled ? 'opacity-50 cursor-not-allowed' : ''}`;

  return (
    <div className={`relative ${className}`} ref={containerRef}>
      <button
        type="button"
        disabled={disabled}
        onClick={() => setIsOpen(!isOpen)}
        onKeyDown={handleKeyDown}
        className={buttonClasses}
        aria-haspopup="listbox"
        aria-expanded={isOpen}
      >
        <span className="truncate capitalize">{selectedOption?.label}</span>
        {variant === "default" && <ChevronDown size={14} className="text-zinc-500 flex-shrink-0" />}
      </button>

      {isOpen && (
        <div 
          ref={listboxRef}
          className={`absolute z-50 mt-1.5 p-1 bg-zinc-900 border border-zinc-800/80 rounded-xl shadow-xl backdrop-blur-sm max-h-60 overflow-auto ${variant === 'inline' ? 'min-w-[140px] left-0 bottom-full mb-1.5 mt-0' : 'w-full min-w-[120px] left-0'}`}
          role="listbox"
        >
          {options.map((opt, i) => {
            const isSelected = opt.value === value;
            const isFocused = i === focusedIndex;
            return (
              <div
                key={opt.value}
                role="option"
                aria-selected={isSelected}
                onClick={() => {
                  onChange(opt.value);
                  setIsOpen(false);
                }}
                onMouseEnter={() => setFocusedIndex(i)}
                className={`flex items-center justify-between px-3 py-2 text-sm rounded-lg cursor-pointer transition-colors capitalize ${isSelected ? 'text-zinc-100 font-medium' : 'text-zinc-400'} ${isFocused ? 'bg-zinc-800/80' : ''} hover:bg-zinc-800/80`}
              >
                <span className="truncate">{opt.label}</span>
                {isSelected && <Check size={14} className="text-zinc-300" />}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
