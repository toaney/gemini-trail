"use client";

import { useState } from "react";
import { useGameStream } from "@/lib/useGameStream";
import StatsPanel from "@/components/StatsPanel";
import NarrativePanel from "@/components/NarrativePanel";
import ActionInput from "@/components/ActionInput";

const OCCUPATIONS = [
  { id: "bunker_ceo", label: "Bunker CEO", desc: "High resources, great negotiator. Soft hands." },
  { id: "engineer",   label: "Engineer",   desc: "Moderate resources. Vehicle is your domain." },
  { id: "carpenter",  label: "Carpenter",  desc: "Fewest resources. Builds and repairs anything." },
];

const MONTHS = ["January","February","March","April","May","June","July","August","September","October","November","December"];

export default function Page() {
  const [screen, setScreen] = useState<"menu" | "setup" | "game">("menu");
  const [partyNames, setPartyNames] = useState(["", "", "", ""]);
  const [occupation, setOccupation] = useState("engineer");
  const [month, setMonth] = useState("March");

  const { narrative, gameState, suggestions, streaming, gameOver, startNewGame, sendAction } = useGameStream();

  const handleStart = async () => {
    if (partyNames.some(n => !n.trim())) return;
    try {
      await startNewGame({ partyNames, occupation, departureMonth: month.toLowerCase() });
      setScreen("game");
    } catch (e) {
      console.error(e);
    }
  };

  if (screen === "menu") {
    return (
      <div className="h-screen flex flex-col items-center justify-center font-mono text-sand-200 p-8">
        <div className="max-w-md w-full space-y-6 text-center">
          <div>
            <h1 className="text-4xl text-rust-400 tracking-widest uppercase">Gemini Trail</h1>
            <p className="text-zinc-400 text-sm mt-2">Long Beach, CA → Washington, DC</p>
            <p className="text-zinc-500 text-xs mt-1">3,245 miles. Post-apocalyptic. Good luck.</p>
          </div>
          <button
            onClick={() => setScreen("setup")}
            className="w-full py-3 border border-rust-500 text-rust-400 hover:bg-rust-500 hover:text-ash-900 transition-colors text-sm tracking-widest uppercase"
          >
            Begin Journey
          </button>
        </div>
      </div>
    );
  }

  if (screen === "setup") {
    return (
      <div className="h-screen overflow-y-auto font-mono text-sand-200 p-8">
        <div className="max-w-lg mx-auto space-y-6">
          <h2 className="text-rust-400 uppercase tracking-widest">Setup Your Party</h2>

          <div className="space-y-2">
            <label className="text-xs text-zinc-400 uppercase tracking-widest">Party Members</label>
            {partyNames.map((name, i) => (
              <input
                key={i}
                value={name}
                onChange={e => {
                  const updated = [...partyNames];
                  updated[i] = e.target.value;
                  setPartyNames(updated);
                }}
                placeholder={i === 0 ? "Your name" : `Companion ${i + 1}`}
                className="w-full bg-ash-800 border border-ash-700 text-sand-100 px-3 py-2 text-sm focus:outline-none focus:border-rust-500"
              />
            ))}
          </div>

          <div className="space-y-2">
            <label className="text-xs text-zinc-400 uppercase tracking-widest">Occupation</label>
            {OCCUPATIONS.map(occ => (
              <button
                key={occ.id}
                onClick={() => setOccupation(occ.id)}
                className={`w-full text-left px-3 py-2 border text-sm transition-colors ${
                  occupation === occ.id
                    ? "border-rust-500 bg-rust-500 bg-opacity-10 text-rust-400"
                    : "border-ash-700 text-zinc-400 hover:border-ash-600"
                }`}
              >
                <span className="text-sand-200">{occ.label}</span>
                <span className="text-zinc-500 ml-2">— {occ.desc}</span>
              </button>
            ))}
          </div>

          <div className="space-y-2">
            <label className="text-xs text-zinc-400 uppercase tracking-widest">Departure Month</label>
            <select
              value={month}
              onChange={e => setMonth(e.target.value)}
              className="w-full bg-ash-800 border border-ash-700 text-sand-100 px-3 py-2 text-sm focus:outline-none focus:border-rust-500"
            >
              {MONTHS.map(m => <option key={m} value={m}>{m}</option>)}
            </select>
          </div>

          <button
            onClick={handleStart}
            disabled={partyNames.some(n => !n.trim())}
            className="w-full py-3 border border-rust-500 text-rust-400 hover:bg-rust-500 hover:text-ash-900 transition-colors text-sm tracking-widest uppercase disabled:opacity-40 disabled:cursor-not-allowed"
          >
            Head to the Market
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="h-screen flex flex-col overflow-hidden">
      <header className="border-b border-ash-700 px-4 py-2 font-mono text-xs text-zinc-400 flex gap-4">
        <span className="text-rust-400 uppercase tracking-widest">Gemini Trail</span>
        {gameState && (
          <>
            <span>Day {gameState.day}</span>
            <span>{gameState.distance_traveled.toFixed(0)} mi</span>
            <span className={gameState.region === "east" ? "text-green-500" : "text-zinc-400"}>
              {gameState.region === "east" ? "EAST" : "WEST"} of Mississippi
            </span>
            <span>{gameState.weather.replace("_", " ")}</span>
          </>
        )}
        {gameOver && (
          <span className={gameOver.outcome === "win" ? "text-green-400" : "text-red-400"}>
            {gameOver.outcome === "win" ? "YOU MADE IT" : "GAME OVER"} — {gameOver.reason}
          </span>
        )}
      </header>

      <div className="flex flex-1 overflow-hidden">
        <aside className="w-48 border-r border-ash-700 p-3 overflow-y-auto bg-ash-800 shrink-0">
          {gameState ? (
            <StatsPanel game={gameState} />
          ) : (
            <div className="text-zinc-600 text-xs font-mono">Loading...</div>
          )}
        </aside>

        <main className="flex-1 flex flex-col overflow-hidden">
          <NarrativePanel lines={narrative} streaming={streaming} />
          <ActionInput
            suggestions={suggestions}
            streaming={streaming}
            disabled={!!gameOver}
            onSubmit={sendAction}
          />
        </main>
      </div>
    </div>
  );
}
