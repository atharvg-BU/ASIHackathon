"use client";

import { AlertTriangle, Pause, Play, RadioTower } from "lucide-react";
import type { LiveFlight } from "@/lib/types";

export default function LiveFlightPanel({
  liveFlight,
  playing,
  onTogglePlay,
  onFlagEmergency
}: {
  liveFlight?: LiveFlight;
  playing: boolean;
  onTogglePlay: () => void;
  onFlagEmergency: () => void;
}) {
  const flight = liveFlight?.flight;
  return (
    <section className="glass rounded-lg p-4">
      <div className="mb-4 flex items-center justify-between gap-3">
        <div className="flex items-center gap-2 text-sm font-semibold text-white">
          <RadioTower size={16} className="text-cyanline" />
          Selected Flight Live Sim
        </div>
        <span className="rounded-full bg-cyanline/10 px-2 py-1 text-[11px] font-semibold text-cyanline">Selectable</span>
      </div>

      {!liveFlight || !flight ? (
        <div className="h-36 animate-pulse rounded-md bg-white/[0.04]" />
      ) : (
        <div className="space-y-4">
          <div>
            <div className="text-3xl font-bold text-white">{flight.flight_id}</div>
            <div className="text-sm text-slate-400">
              {flight.origin} to {flight.destination} · {flight.airline}
            </div>
            {flight.data_source === "hackathon_data_bundle" && (
              <div className="mt-1 text-xs text-runway">Route from hackathon_data_bundle</div>
            )}
          </div>

          <div className="grid grid-cols-2 gap-2 text-sm">
            <Info label="Status" value={liveFlight.status} />
            <Info label="Risk" value={flight.risk_level || "low"} />
            <Info label="Position" value={`${liveFlight.current_position[0]}, ${liveFlight.current_position[1]}`} />
            <Info label="ETA" value={`${liveFlight.minutes_to_arrival} min`} />
          </div>

          <div>
            <div className="mb-2 flex justify-between text-xs text-slate-400">
              <span>{flight.departure_time_utc} UTC</span>
              <span>{Math.round(liveFlight.progress * 100)}%</span>
              <span>{flight.arrival_time_utc} UTC</span>
            </div>
            <div className="h-2 overflow-hidden rounded-full bg-white/10">
              <div className="h-full rounded-full bg-cyanline" style={{ width: `${liveFlight.progress * 100}%` }} />
            </div>
          </div>

          <div className="grid grid-cols-2 gap-2">
            <button onClick={onTogglePlay} className="flex items-center justify-center gap-2 rounded-md bg-cyanline px-3 py-2 text-sm font-semibold text-slate-950">
              {playing ? <Pause size={16} /> : <Play size={16} />}
              {playing ? "Pause" : "Play"}
            </button>
            <button onClick={onFlagEmergency} className="flex items-center justify-center gap-2 rounded-md bg-danger/15 px-3 py-2 text-sm font-semibold text-danger">
              <AlertTriangle size={16} />
              Flag Emergency
            </button>
          </div>

          <div className="rounded-md bg-white/[0.04] p-3 text-xs leading-5 text-slate-300">
            Nearby water context: {liveFlight.water_context?.nearby_water_bodies?.[0]?.name || "none inside demo threshold"}
          </div>
        </div>
      )}
    </section>
  );
}

function Info({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-md bg-white/[0.04] p-2">
      <div className="text-xs text-slate-400">{label}</div>
      <div className="font-semibold capitalize text-white">{value}</div>
    </div>
  );
}
