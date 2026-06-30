"use client";

import { useState, KeyboardEvent } from "react";

interface Props {
  suggestions: string[];
  streaming: boolean;
  disabled: boolean;
  phase?: string;
  autoTravel?: boolean;
  onSubmit: (message: string) => void;
  onToggleAutoTravel?: () => void;
}

export default function ActionInput({
  suggestions,
  streaming,
  disabled,
  phase,
  autoTravel,
  onSubmit,
  onToggleAutoTravel,
}: Props) {
  const [input, setInput] = useState("");

  const handleSubmit = () => {
    const msg = input.trim();
    if (!msg || streaming || disabled) return;
    onSubmit(msg);
    setInput("");
  };

  const handleKey = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  const handleSuggestion = (text: string) => {
    setInput(text);
  };

  return (
    <div className="border-t border-ash-700 p-3 space-y-2">
      {/* Begin journey — only during preparation */}
      {phase === "preparation" && (
        <button
          onClick={() => onSubmit("depart")}
          disabled={streaming || disabled}
          className="w-full py-2 border border-rust-500 bg-rust-500 bg-opacity-10 text-rust-400 hover:bg-opacity-30 transition-colors text-xs tracking-widest uppercase font-mono disabled:opacity-40 disabled:cursor-not-allowed"
        >
          BEGIN JOURNEY →
        </button>
      )}

      {/* Auto-travel toggle — only while on the trail */}
      {phase === "on_trail" && onToggleAutoTravel && (
        <button
          onClick={onToggleAutoTravel}
          disabled={disabled}
          className={`px-3 py-1 text-xs font-mono border transition-colors rounded ${
            autoTravel
              ? "border-rust-500 bg-rust-500 text-ash-900 font-bold"
              : "border-ash-600 text-zinc-400 hover:border-rust-500 hover:text-rust-400"
          }`}
        >
          {autoTravel ? "■ STOP" : "▶ AUTO-TRAVEL"}
        </button>
      )}

      {suggestions.length > 0 && (
        <div className="flex flex-wrap gap-2">
          {suggestions.map((s, i) => (
            <button
              key={i}
              onClick={() => handleSuggestion(s)}
              disabled={streaming || disabled}
              className="text-xs px-3 py-1 rounded border border-rust-500 text-rust-400 hover:bg-rust-500 hover:text-ash-900 transition-colors disabled:opacity-40 disabled:cursor-not-allowed font-mono"
            >
              {s}
            </button>
          ))}
        </div>
      )}

      <div className="flex gap-2">
        <textarea
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKey}
          disabled={streaming || disabled}
          placeholder={streaming ? "…" : "What do you do?"}
          rows={1}
          className="flex-1 bg-ash-800 border border-ash-700 text-sand-100 font-mono text-sm px-3 py-2 rounded resize-none focus:outline-none focus:border-rust-500 placeholder-zinc-600 disabled:opacity-40"
        />
        <button
          onClick={handleSubmit}
          disabled={!input.trim() || streaming || disabled}
          className="px-4 py-2 bg-rust-500 text-ash-900 font-mono text-sm rounded hover:bg-rust-400 transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
        >
          {streaming ? "…" : "Go"}
        </button>
      </div>
    </div>
  );
}
