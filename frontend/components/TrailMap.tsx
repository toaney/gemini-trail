"use client";

import { GameState } from "@/lib/types";

const TOTAL = 3245;

const LANDMARKS = [
  { name: "Las Vegas",           mile: 270  },
  { name: "Phoenix",             mile: 565  },
  { name: "Roswell",             mile: 1025 },
  { name: "Fort Worth",          mile: 1525 },
  { name: "Shreveport",          mile: 1805 },
  { name: "Mississippi Crossing",mile: 2005 },
  { name: "Tuscaloosa",          mile: 2275 },
  { name: "Atlanta",             mile: 2425 },
  { name: "Charleston",          mile: 2715 },
];

function CarSVG({ moving }: { moving: boolean }) {
  const wheelStyle = moving
    ? { transformBox: "fill-box" as const, transformOrigin: "center", animation: "wheel-spin 0.55s linear infinite" }
    : {};

  return (
    <svg viewBox="0 0 88 40" width="52" height="24" className="overflow-visible drop-shadow-sm">
      {/* Luggage — rear box */}
      <rect x="10" y="3" width="14" height="9" rx="1.5" fill="#5a1e18" stroke="#772e25" strokeWidth="0.8"/>
      <line x1="10" y1="7.5" x2="24" y2="7.5" stroke="#772e25" strokeWidth="0.6" opacity="0.7"/>
      <line x1="17" y1="3"   x2="17" y2="12"   stroke="#772e25" strokeWidth="0.6" opacity="0.7"/>
      {/* Luggage — front box */}
      <rect x="27" y="3" width="20" height="9" rx="1.5" fill="#772e25" stroke="#C44536" strokeWidth="0.8"/>
      <line x1="27" y1="7.5" x2="47" y2="7.5" stroke="#C44536" strokeWidth="0.6" opacity="0.6"/>
      {/* Rack cross-bar */}
      <rect x="8"  y="11" width="42" height="2" rx="1" fill="#444"/>
      {/* Rack legs */}
      <rect x="11" y="11" width="2"  height="3" fill="#444"/>
      <rect x="46" y="11" width="2"  height="3" fill="#444"/>
      {/* Roof */}
      <rect x="8"  y="13" width="46" height="9" rx="3" fill="#C44536"/>
      {/* Body */}
      <rect x="2"  y="19" width="76" height="16" rx="4" fill="#C44536"/>
      {/* Rear bumper */}
      <rect x="0"  y="24" width="5"  height="8"  rx="2" fill="#772e25"/>
      {/* Front bumper / grille */}
      <rect x="77" y="24" width="6"  height="8"  rx="2" fill="#772e25"/>
      <rect x="80" y="25" width="3"  height="3"  rx="1" fill="#ffd060" opacity="0.9"/>
      {/* Windows */}
      <rect x="13" y="14" width="14" height="7" rx="1.5" fill="#1c2e2c" opacity="0.85"/>
      <rect x="30" y="14" width="19" height="7" rx="1.5" fill="#1c2e2c" opacity="0.85"/>
      {/* Rear light */}
      <rect x="2"  y="26" width="4" height="3" rx="1" fill="#ff4444" opacity="0.7"/>
      {/* Exhaust puff when moving */}
      {moving && (
        <>
          <circle cx="-4" cy="32" r="2.5" fill="#555" opacity="0.35"/>
          <circle cx="-9" cy="31" r="1.8" fill="#555" opacity="0.2"/>
        </>
      )}
      {/* Rear wheel */}
      <circle cx="20" cy="35" r="8" fill="#1a1a16"/>
      <circle cx="20" cy="35" r="5" fill="#2a2a24"/>
      <g style={wheelStyle}>
        <circle cx="20" cy="35" r="8" fill="none"/>
        <line x1="20" y1="27" x2="20" y2="43" stroke="#444" strokeWidth="1.5"/>
        <line x1="12" y1="35" x2="28" y2="35" stroke="#444" strokeWidth="1.5"/>
      </g>
      <circle cx="20" cy="35" r="2" fill="#555"/>
      {/* Front wheel */}
      <circle cx="62" cy="35" r="8" fill="#1a1a16"/>
      <circle cx="62" cy="35" r="5" fill="#2a2a24"/>
      <g style={wheelStyle}>
        <circle cx="62" cy="35" r="8" fill="none"/>
        <line x1="62" y1="27" x2="62" y2="43" stroke="#444" strokeWidth="1.5"/>
        <line x1="54" y1="35" x2="70" y2="35" stroke="#444" strokeWidth="1.5"/>
      </g>
      <circle cx="62" cy="35" r="2" fill="#555"/>
    </svg>
  );
}

interface Props {
  game: GameState;
  moving: boolean;
}

export default function TrailMap({ game, moving }: Props) {
  const pct = Math.min(100, (game.distance_traveled / TOTAL) * 100);

  return (
    <div className="relative border-b border-ash-700 bg-ash-900 select-none" style={{ height: 52 }}>
      {/* Road line */}
      <div className="absolute left-6 right-6" style={{ top: 38 }}>
        {/* Base track */}
        <div className="absolute inset-0 h-px bg-ash-600"/>
        {/* Progress fill */}
        <div
          className="absolute left-0 top-0 h-px bg-rust-500 transition-all duration-700"
          style={{ width: `${pct}%` }}
        />

        {/* Landmark dots */}
        {LANDMARKS.map(lm => {
          const lmPct = (lm.mile / TOTAL) * 100;
          const passed  = game.distance_traveled >= lm.mile;
          const current = game.current_landmark === lm.name;
          return (
            <div
              key={lm.name}
              className="absolute -translate-x-1/2"
              style={{ left: `${lmPct}%`, top: -3 }}
              title={lm.name}
            >
              <div className={`w-1.5 h-1.5 rounded-full transition-all duration-500 ${
                current ? "bg-rust-400 ring-1 ring-rust-400 ring-offset-1 ring-offset-ash-900 scale-125" :
                passed  ? "bg-rust-500 opacity-60" :
                          "bg-ash-500"
              }`} />
            </div>
          );
        })}

        {/* DC marker */}
        <div className="absolute right-0 translate-x-1/2" style={{ top: -4 }} title="Washington DC">
          <div className={`w-2 h-2 rounded-full ${pct >= 100 ? "bg-green-400" : "bg-ash-500"}`}/>
        </div>
      </div>

      {/* Car — sits on the track line */}
      <div
        className="absolute transition-all duration-700"
        style={{
          left: `calc(1.5rem + ${pct}% * (100% - 3rem) / 100%)`,
          top: 8,
          transform: "translateX(-50%)",
        }}
      >
        <CarSVG moving={moving} />
      </div>

      {/* Origin / destination labels */}
      <span className="absolute left-2 font-mono text-zinc-600" style={{ fontSize: 8, top: 40 }}>
        Long Beach
      </span>
      <span className="absolute right-2 font-mono text-zinc-600" style={{ fontSize: 8, top: 40 }}>
        Washington DC
      </span>
    </div>
  );
}
