"use client";

import { useState, useCallback, useRef } from "react";
import { GameState, SSEEvent } from "./types";

export function useGameStream() {
  const [narrative, setNarrative] = useState<string[]>([]);
  const [gameState, setGameState] = useState<GameState | null>(null);
  const [suggestions, setSuggestions] = useState<string[]>([]);
  const [streaming, setStreaming] = useState(false);
  const [threadId, setThreadId] = useState<string | null>(null);
  const [gameOver, setGameOver] = useState<{ outcome: string; reason: string } | null>(null);
  const currentTokenRef = useRef<string>("");

  const startNewGame = useCallback(async (form: {
    partyNames: string[];
    occupation: string;
    departureMonth: string;
  }) => {
    const res = await fetch("/api/game/new", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        party_names: form.partyNames,
        player_name: form.partyNames[0],
        occupation: form.occupation,
        departure_month: form.departureMonth,
      }),
    });

    if (!res.ok) throw new Error("Failed to start game");
    const data = await res.json();
    setThreadId(data.thread_id);
    setNarrative([]);
    setSuggestions(["Buy food and water", "Stock up on fuel", "Buy spare parts"]);
    setGameOver(null);
    return data.thread_id;
  }, []);

  const sendAction = useCallback(async (message: string) => {
    if (!threadId || streaming) return;

    setStreaming(true);
    currentTokenRef.current = "";
    setNarrative(prev => [...prev, `> ${message}`, ""]);

    const narrativeIndex = narrative.length + 1;

    try {
      const res = await fetch("/api/game/stream", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ thread_id: threadId, message }),
      });

      if (!res.ok || !res.body) throw new Error("Stream failed");

      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n");
        buffer = lines.pop() ?? "";

        for (const line of lines) {
          if (!line.startsWith("data: ")) continue;
          const raw = line.slice(6).trim();
          if (!raw) continue;

          try {
            const event: SSEEvent = JSON.parse(raw);
            handleSSEEvent(event, narrativeIndex);
          } catch {
            // malformed chunk
          }
        }
      }
    } finally {
      setStreaming(false);
    }
  }, [threadId, streaming, narrative.length]);

  const handleSSEEvent = useCallback((event: SSEEvent, narrativeIndex: number) => {
    switch (event.type) {
      case "token":
        if (event.content) {
          currentTokenRef.current += event.content;
          setNarrative(prev => {
            const updated = [...prev];
            updated[narrativeIndex] = currentTokenRef.current;
            return updated;
          });
        }
        break;

      case "state_update":
        if (event.game) {
          setGameState(event.game);
        }
        break;

      case "suggestions":
        if (event.actions) {
          setSuggestions(event.actions);
        }
        break;

      case "game_over":
        setGameOver({ outcome: event.outcome ?? "unknown", reason: event.reason ?? "" });
        break;
    }
  }, []);

  return {
    narrative,
    gameState,
    suggestions,
    streaming,
    threadId,
    gameOver,
    startNewGame,
    sendAction,
  };
}
