"use client";

import { useState, useEffect, useRef, useCallback } from "react";
import { GameState } from "@/lib/types";

interface SavePoint {
  id: number;
  name: string;
  thread_id: string;
  day: number;
  distance: number;
  phase: string;
  created_at: string;
}

interface Props {
  threadId: string | null;
  gameState: GameState | null;
  onLoad: (threadId: string, gameState: GameState, narrative: string, suggestions: string[]) => void;
}

export default function DevSaveMenu({ threadId, gameState, onLoad }: Props) {
  const [open, setOpen] = useState(false);
  const [saves, setSaves] = useState<SavePoint[]>([]);
  const [saving, setSaving] = useState(false);
  const [loading, setLoading] = useState(false);
  const [saveName, setSaveName] = useState("");
  const ref = useRef<HTMLDivElement>(null);

  const fetchSaves = useCallback(async () => {
    const res = await fetch("/api/game/saves");
    if (res.ok) setSaves(await res.json());
  }, []);

  useEffect(() => {
    if (open) fetchSaves();
  }, [open, fetchSaves]);

  useEffect(() => {
    if (!gameState) return;
    const landmark = gameState.current_landmark || gameState.next_landmark || "";
    setSaveName(`Day ${gameState.day} — ${landmark}`);
  }, [gameState]);

  // Close on outside click
  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, []);

  const handleSave = async () => {
    if (!threadId || !gameState || saving) return;
    setSaving(true);
    try {
      await fetch("/api/game/save", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ thread_id: threadId, name: saveName || `Day ${gameState.day}`, game_state: gameState }),
      });
      await fetchSaves();
      setSaveName(`Day ${gameState.day} — ${gameState.current_landmark || gameState.next_landmark || ""}`);
    } finally {
      setSaving(false);
    }
  };

  const handleLoad = async (save: SavePoint) => {
    if (loading) return;
    setLoading(true);
    try {
      const res = await fetch("/api/game/load", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ save_id: save.id }),
      });
      if (!res.ok) return;
      const data = await res.json();
      onLoad(data.thread_id, data.game_state, data.narrative, data.suggestions);
      setOpen(false);
    } finally {
      setLoading(false);
    }
  };

  const handleDelete = async (e: React.MouseEvent, id: number) => {
    e.stopPropagation();
    await fetch(`/api/game/save/${id}`, { method: "DELETE" });
    setSaves(prev => prev.filter(s => s.id !== id));
  };

  return (
    <div ref={ref} className="relative ml-auto">
      <button
        onClick={() => setOpen(o => !o)}
        className="text-xs font-mono px-2 py-1 border border-dashed border-zinc-600 text-zinc-500 hover:border-rust-500 hover:text-rust-400 transition-colors"
      >
        DEV ▾
      </button>

      {open && (
        <div className="absolute right-0 top-full mt-1 w-80 bg-ash-900 border border-ash-600 shadow-xl z-50 font-mono text-xs">
          {/* Save current state */}
          {threadId && gameState && (
            <div className="p-3 border-b border-ash-700">
              <div className="text-zinc-500 uppercase tracking-widest mb-2">Save Current State</div>
              <input
                value={saveName}
                onChange={e => setSaveName(e.target.value)}
                className="w-full bg-ash-800 border border-ash-700 text-sand-100 px-2 py-1 text-xs focus:outline-none focus:border-rust-500 mb-2"
                placeholder="Save name…"
              />
              <button
                onClick={handleSave}
                disabled={saving}
                className="w-full py-1.5 border border-rust-500 text-rust-400 hover:bg-rust-500 hover:text-ash-900 transition-colors disabled:opacity-40"
              >
                {saving ? "Saving…" : "Save"}
              </button>
            </div>
          )}

          {/* Save list */}
          <div className="max-h-64 overflow-y-auto">
            {saves.length === 0 ? (
              <div className="p-3 text-zinc-600">No saves yet.</div>
            ) : (
              saves.map(save => (
                <button
                  key={save.id}
                  onClick={() => handleLoad(save)}
                  disabled={loading}
                  className="w-full text-left px-3 py-2 hover:bg-ash-700 transition-colors border-b border-ash-800 last:border-0 group disabled:opacity-40"
                >
                  <div className="flex justify-between items-start">
                    <span className="text-sand-200">{save.name}</span>
                    <span
                      onClick={e => handleDelete(e, save.id)}
                      className="text-zinc-600 hover:text-red-400 transition-colors ml-2 cursor-pointer"
                    >
                      ×
                    </span>
                  </div>
                  <div className="text-zinc-500 mt-0.5">
                    Day {save.day} · {save.distance.toFixed(0)} mi · {save.phase.replace("_", " ")}
                  </div>
                  <div className="text-zinc-600 mt-0.5">
                    {new Date(save.created_at).toLocaleString()}
                  </div>
                </button>
              ))
            )}
          </div>
        </div>
      )}
    </div>
  );
}
