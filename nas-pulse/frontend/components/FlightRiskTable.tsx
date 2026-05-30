"use client";

import { Search } from "lucide-react";
import { useMemo, useState } from "react";
import type { Flight } from "@/lib/types";

export default function FlightRiskTable({
  flights,
  selected,
  emergencyFlightId,
  onSelect,
  onFlagEmergency
}: {
  flights: Flight[];
  selected?: string;
  emergencyFlightId?: string;
  onSelect: (flight: Flight) => void;
  onFlagEmergency?: (flight: Flight) => void;
}) {
  const [query, setQuery] = useState("");
  const visibleFlights = useMemo(() => {
    const normalized = query.trim().toLowerCase();
    const ranked = flights.slice().sort((a, b) => (b.total_risk || 0) - (a.total_risk || 0));
    if (!normalized) return ranked.slice(0, 40);
    return ranked.filter((flight) => {
      const text = `${flight.flight_id} ${flight.origin} ${flight.destination} ${flight.airline}`.toLowerCase();
      return text.includes(normalized);
    }).slice(0, 40);
  }, [flights, query]);

  return (
    <section className="glass rounded-lg p-4">
      <div className="flex items-center justify-between gap-2">
        <h2 className="text-sm font-semibold text-white">Selectable Flights</h2>
        <span className="text-xs text-slate-400">{flights.length} airborne</span>
      </div>
      <label className="mt-3 flex items-center gap-2 rounded-md border border-white/10 bg-white/[0.04] px-2 py-2 text-sm text-slate-300">
        <Search size={15} className="shrink-0 text-slate-500" />
        <input
          value={query}
          onChange={(event) => setQuery(event.target.value)}
          placeholder="Search flight, route, carrier..."
          className="min-w-0 flex-1 bg-transparent text-sm text-white outline-none placeholder:text-slate-500"
        />
      </label>
      <div className="mt-3 max-h-[315px] space-y-2 overflow-auto pr-1">
        {flights.length === 0 && <div className="rounded-md bg-white/[0.04] p-3 text-sm text-slate-400">No flights are active at this traffic clock time.</div>}
        {visibleFlights.map((flight) => (
          <div
            key={flight.flight_id}
            className={`rounded-md border p-2 text-sm ${emergencyFlightId === flight.flight_id ? "border-danger bg-danger/10" : selected === flight.flight_id ? "border-cyanline bg-cyanline/10" : "border-white/10 bg-white/[0.035]"}`}
          >
            <button onClick={() => onSelect(flight)} className="grid w-full grid-cols-[1fr_auto] text-left">
              <span className="font-semibold">{flight.flight_id} <span className="font-normal text-slate-400">{flight.origin}-{flight.destination}</span></span>
              <span className={`risk-${flight.risk_level}`}>{flight.risk_level || "low"}</span>
              <span className="text-xs text-slate-400">{flight.airline} · {flight.data_source === "hackathon_data_bundle" ? "bundle route" : "demo route"}</span>
              <span className="text-xs text-slate-400">{Math.round((flight.total_risk || 0) * 100)}%</span>
            </button>
            {onFlagEmergency && (
              <button
                onClick={() => onFlagEmergency(flight)}
                className="mt-2 w-full rounded bg-danger/15 px-2 py-1 text-xs font-semibold text-danger hover:bg-danger/25"
              >
                {emergencyFlightId === flight.flight_id ? "Emergency flagged" : "Flag emergency"}
              </button>
            )}
          </div>
        ))}
      </div>
    </section>
  );
}
