"use client";
import { useState, useRef, useEffect, useId } from "react";
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
  variant = "default",
  label,
}: {
  options: SelectOption[];
  value: string;
  onChange: (val: string) => void;
  disabled?: boolean;
  className?: string;
  variant?: "default" | "inline";
  label?: string;
}) {
  const [isOpen, setIsOpen] = useState(false);
  const [focusedIndex, setFocusedIndex] = useState(-1);
  const containerRef = useRef<HTMLDivElement>(null);
  const listboxRef = useRef<HTMLDivElement>(null);
  const buttonRef = useRef<HTMLButtonElement>(null);
  const instanceId = useId();
  const listboxId = `${instanceId}-listbox`;

  const selectedOption = options.find((o) => o.value === value) || options[0];

  // Close on outside click
  useEffect(() => {
    const handleOutsideClick = (e: MouseEvent) => {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setIsOpen(false);
      }
    };
    if (isOpen) document.addEventListener("mousedown", handleOutsideClick);
    return () => document.removeEventListener("mousedown", handleOutsideClick);
  }, [isOpen]);

  // Set focused index when opening
  useEffect(() => {
    if (isOpen) {
      // eslint-disable-next-line react-hooks/set-state-in-effect
      setFocusedIndex(options.findIndex(o => o.value === value));
    }
  }, [isOpen, value, options]);

  // Scroll focused option into view
  useEffect(() => {
    if (isOpen && listboxRef.current && focusedIndex >= 0) {
      const optionEl = listboxRef.current.children[focusedIndex] as HTMLElement;
      if (optionEl) {
        optionEl.scrollIntoView({ block: "nearest" });
      }
    }
  }, [focusedIndex, isOpen]);

  // Viewport-safe positioning: detect if dropdown would overflow bottom
  const [dropUp, setDropUp] = useState(false);
  useEffect(() => {
    if (isOpen && buttonRef.current && variant === "default") {
      const rect = buttonRef.current.getBoundingClientRect();
      const spaceBelow = window.innerHeight - rect.bottom;
      setDropUp(spaceBelow < 240);
    } else if (!isOpen) {
      setDropUp(false);
    }
  }, [isOpen, variant]);

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (disabled) return;
    
    if (e.key === "Enter" || e.key === " ") {
      e.preventDefault();
      if (isOpen && focusedIndex >= 0) {
        onChange(options[focusedIndex].value);
        setIsOpen(false);
        buttonRef.current?.focus();
      } else {
        setIsOpen(true);
      }
    } else if (e.key === "Escape") {
      e.preventDefault();
      setIsOpen(false);
      buttonRef.current?.focus();
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
    } else if (e.key === "Home") {
      e.preventDefault();
      if (isOpen) setFocusedIndex(0);
    } else if (e.key === "End") {
      e.preventDefault();
      if (isOpen) setFocusedIndex(options.length - 1);
    }
  };

  const buttonClasses = variant === "inline"
    ? `flex items-center gap-1 bg-transparent text-zinc-400 hover:text-zinc-200 text-xs font-medium cursor-pointer transition-colors rounded-md px-1.5 py-1 focus-visible:ring-2 focus-visible:ring-zinc-500 focus-visible:ring-offset-1 focus-visible:ring-offset-zinc-950 focus-visible:text-zinc-200 outline-none ${disabled ? 'opacity-50 cursor-not-allowed' : ''}`
    : `w-full flex items-center justify-between gap-2 px-4 py-2.5 text-sm text-zinc-200 bg-zinc-900/60 border border-zinc-700/60 rounded-lg transition-all duration-150 focus-visible:border-zinc-500 focus-visible:ring-2 focus-visible:ring-zinc-500/40 hover:border-zinc-600 outline-none ${disabled ? 'opacity-50 cursor-not-allowed' : ''}`;

  // Dropdown positioning classes
  const dropdownPosition = variant === 'inline'
    ? 'min-w-[160px] left-0 bottom-full mb-1.5'
    : dropUp
      ? 'w-full min-w-[120px] left-0 bottom-full mb-1.5'
      : 'w-full min-w-[120px] left-0 mt-1.5';

  return (
    <div className={`relative ${className}`} ref={containerRef}>
      {label && (
        <label className="block text-xs font-medium text-zinc-400 uppercase tracking-wider mb-1.5">
          {label}
        </label>
      )}
      <button
        ref={buttonRef}
        type="button"
        disabled={disabled}
        onClick={() => setIsOpen(!isOpen)}
        onKeyDown={handleKeyDown}
        className={buttonClasses}
        aria-haspopup="listbox"
        aria-expanded={isOpen}
        aria-controls={isOpen ? listboxId : undefined}
        aria-activedescendant={isOpen && focusedIndex >= 0 ? `${instanceId}-opt-${focusedIndex}` : undefined}
        aria-label={label || `Select: ${selectedOption?.label}`}
      >
        <span className="truncate capitalize">{selectedOption?.label}</span>
        <ChevronDown 
          size={variant === "inline" ? 12 : 14} 
          className={`text-zinc-500 flex-shrink-0 transition-transform duration-150 ${isOpen ? 'rotate-180' : ''}`} 
        />
      </button>

      {isOpen && (
        <div 
          ref={listboxRef}
          id={listboxId}
          className={`absolute z-50 p-1 bg-zinc-900 border border-zinc-800/80 rounded-xl shadow-2xl max-h-60 overflow-auto ${dropdownPosition}`}
          role="listbox"
          aria-label={label || "Options"}
        >
          {options.map((opt, i) => {
            const isSelected = opt.value === value;
            const isFocused = i === focusedIndex;
            return (
              <div
                key={opt.value}
                id={`${instanceId}-opt-${i}`}
                role="option"
                aria-selected={isSelected}
                onClick={() => {
                  onChange(opt.value);
                  setIsOpen(false);
                  buttonRef.current?.focus();
                }}
                onMouseEnter={() => setFocusedIndex(i)}
                className={`flex items-center justify-between px-3 py-2 text-sm rounded-lg cursor-pointer transition-colors capitalize ${isSelected ? 'text-zinc-100 font-medium' : 'text-zinc-400'} ${isFocused ? 'bg-zinc-800/80 text-zinc-200' : ''} hover:bg-zinc-800/80`}
              >
                <span className="truncate">{opt.label}</span>
                {isSelected && <Check size={14} className="text-zinc-400 flex-shrink-0" />}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
