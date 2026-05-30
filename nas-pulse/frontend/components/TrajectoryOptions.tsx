"use client";

import type { Optimization } from "@/lib/types";

export default function TrajectoryOptions({ optimization, selectedFlightId }: { optimization?: Optimization; selectedFlightId?: string }) {
  const options = selectedFlightId ? optimization?.trajectory_options?.[selectedFlightId] || [] : [];
  return (
    <section className="glass rounded-lg p-4">
      <h2 className="text-sm font-semibold text-white">Trajectory Options</h2>
      <div className="mt-3 grid gap-2">
        {options.length === 0 && <div className="rounded-md bg-white/[0.04] p-3 text-sm text-slate-400">Select a high-risk optimized flight to compare options.</div>}
        {options.map((option: any) => (
          <div key={option.label} className="rounded-md border border-white/10 bg-white/[0.04] p-3 text-sm">
            <div className="flex justify-between">
              <span className="font-semibold">{option.label}</span>
              <span className="text-amber">{option.expected_delay_minutes} min</span>
            </div>
            <div className="mt-1 text-cyanline">{String(option.action_type).replaceAll("_", " ")}</div>
            <div className="mt-1 text-xs text-slate-400">Fuel {option.fuel_impact} · residual risk {option.residual_risk}</div>
          </div>
        ))}
      </div>
    </section>
  );
}
