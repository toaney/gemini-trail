"use client";

import { GameState } from "@/lib/types";

const HEALTH_COLORS: Record<string, string> = {
  Good:     "text-green-400",
  Fair:     "text-yellow-400",
  Poor:     "text-orange-400",
  Critical: "text-red-400",
  Dead:     "text-zinc-600",
};

const WEATHER_ICONS: Record<string, string> = {
  clear:        "☀",
  cloudy:       "☁",
  rain:         "🌧",
  storm:        "⛈",
  extreme_heat: "🔥",
  extreme_cold: "❄",
};

interface Props {
  game: GameState;
}

export default function StatsPanel({ game }: Props) {
  const { party, supplies, vehicle_condition, day, distance_traveled, weather, pace, rations, phase, current_landmark, next_landmark } = game;
  const milesLeft = Math.max(0, 3245 - distance_traveled).toFixed(0);
  const weatherIcon = WEATHER_ICONS[weather] ?? "?";
  const atStop = phase === "at_landmark" || phase === "event";

  return (
    <div className="flex flex-col gap-4 font-mono text-sand-200 text-sm">
      <div>
        <div className="text-sand-300 text-xs uppercase tracking-widest mb-1">Journey</div>
        <div>Day {day}</div>
        <div>{distance_traveled.toFixed(0)} mi traveled</div>
        <div>{milesLeft} mi to DC</div>
        <div className="mt-1">
          {atStop ? (
            <span className="text-rust-400">{current_landmark ?? "Event"}</span>
          ) : (
            <span className="text-zinc-400">→ {next_landmark}</span>
          )}
        </div>
      </div>

      <div>
        <div className="text-sand-300 text-xs uppercase tracking-widest mb-1">Conditions</div>
        <div>{weatherIcon} {weather.replace("_", " ")}</div>
        <div>Pace: {pace}</div>
        <div>Rations: {rations.replace("_", " ")}</div>
        <div className="flex items-center gap-1 mt-1">
          <span>Vehicle:</span>
          <span className={vehicle_condition > 60 ? "text-green-400" : vehicle_condition > 30 ? "text-yellow-400" : "text-red-400"}>
            {vehicle_condition}%
          </span>
        </div>
        <DrainBar value={vehicle_condition} max={100} />
      </div>

      <div>
        <div className="text-sand-300 text-xs uppercase tracking-widest mb-1">Party</div>
        {party.map((member) => (
          <div key={member.name} className="flex justify-between">
            <span className={member.alive ? "text-sand-200" : "text-zinc-600 line-through"}>
              {member.name}
            </span>
            <span className={HEALTH_COLORS[member.health_label] ?? "text-zinc-400"}>
              {member.health_label}
            </span>
          </div>
        ))}
      </div>

      <div>
        <div className="text-sand-300 text-xs uppercase tracking-widest mb-1">Supplies</div>
        <SupplyRow label="Food"  value={`${supplies.food_days.toFixed(1)}d`}   warn={supplies.food_days < 5} />
        <DrainBar value={supplies.food_days}    max={100} warn={supplies.food_days < 5} />
        <SupplyRow label="Water" value={`${supplies.water_days.toFixed(1)}d`}  warn={supplies.water_days < 3} />
        <DrainBar value={supplies.water_days}   max={50}  warn={supplies.water_days < 3} />
        <SupplyRow label="Fuel"  value={`${supplies.fuel_gallons.toFixed(1)}g`} warn={supplies.fuel_gallons < 10} />
        <DrainBar value={supplies.fuel_gallons} max={80}  warn={supplies.fuel_gallons < 10} />
        <div className="mt-1"/>
        <SupplyRow label="Medicine" value={`${supplies.medicine_kits} kits`}  warn={supplies.medicine_kits === 0} />
        <SupplyRow label="Ammo"     value={`${supplies.ammo_rounds} rds`}     warn={supplies.ammo_rounds < 10} />
        <SupplyRow label="Trade"    value={`${supplies.trade_goods} goods`}   warn={false} />
      </div>

      <div>
        <div className="text-sand-300 text-xs uppercase tracking-widest mb-1">Parts</div>
        <SupplyRow label="Tires"   value={`${supplies.spare_tires}`}   warn={supplies.spare_tires === 0} />
        <SupplyRow label="Engine"  value={`${supplies.engine_kits}`}   warn={false} />
        <SupplyRow label="Generic" value={`${supplies.generic_parts}`} warn={false} />
      </div>
    </div>
  );
}

function DrainBar({ value, max, warn }: { value: number; max: number; warn?: boolean }) {
  const pct = Math.min(100, Math.max(0, (value / max) * 100));
  const color = warn         ? "bg-red-500"
              : pct > 60     ? "bg-green-600"
              : pct > 25     ? "bg-yellow-500"
              :                "bg-red-500";
  return (
    <div className="h-0.5 bg-ash-700 rounded-full mb-1.5 mt-0.5">
      <div
        className={`h-full rounded-full transition-all duration-700 ${color}`}
        style={{ width: `${pct}%` }}
      />
    </div>
  );
}

function SupplyRow({ label, value, warn }: { label: string; value: string; warn: boolean }) {
  return (
    <div className="flex justify-between">
      <span className="text-zinc-400">{label}</span>
      <span className={warn ? "text-red-400" : "text-sand-200"}>{value}</span>
    </div>
  );
}
