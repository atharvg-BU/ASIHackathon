"use client";

import type { Optimization } from "@/lib/types";

export default function InterventionList({ optimization }: { optimization?: Optimization }) {
  const actions = optimization?.recommended_actions || [];
  return (
    <section className="glass rounded-lg p-4">
      <h2 className="text-sm font-semibold text-white">Recommended Interventions</h2>
      <div className="mt-3 space-y-2">
        {actions.length === 0 && <div className="rounded-md bg-white/[0.04] p-3 text-sm text-slate-400">Run optimizer to rank the minimum intervention set.</div>}
        {actions.slice(0, 8).map((action) => (
          <div key={`${action.flight_id}-${action.action_type}`} className="rounded-md border border-white/10 bg-white/[0.04] p-3 text-sm">
            <div className="flex justify-between gap-3">
              <span className="font-semibold text-white">{action.flight_id}</span>
              <span className="text-runway">{action.expected_delay_reduction_minutes} min saved</span>
            </div>
            <div className="mt-1 text-cyanline">{String(action.action_type).replaceAll("_", " ")}</div>
            <p className="mt-1 text-xs leading-5 text-slate-400">{action.explanation}</p>
          </div>
        ))}
      </div>
    </section>
  );
}
