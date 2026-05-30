"use client";

import { Activity, Gauge, Plane, TimerReset } from "lucide-react";
import type { Optimization, SimResult } from "@/lib/types";

export default function Scorecard({ simulation, optimization }: { simulation?: SimResult; optimization?: Optimization }) {
  const before = optimization?.before_metrics;
  const after = optimization?.after_metrics;
  const items = [
    { icon: TimerReset, label: "Delay Before", value: before?.total_delay_minutes ?? simulation?.total_predicted_delay_before_optimization ?? "--", suffix: "min" },
    { icon: Gauge, label: "Delay After", value: after?.total_delay_minutes ?? "--", suffix: after ? "min" : "" },
    { icon: Activity, label: "Reduction", value: optimization?.delay_reduction_percentage ?? "--", suffix: optimization ? "%" : "" },
    { icon: Plane, label: "Affected", value: simulation ? simulation.direct_impact_count + simulation.indirect_impact_count : "--", suffix: "flts" }
  ];
  return (
    <section className="glass rounded-lg p-4">
      <h2 className="text-sm font-semibold text-white">System Scorecard</h2>
      <div className="mt-3 grid grid-cols-2 gap-2">
        {items.map((item) => (
          <div key={item.label} className="rounded-md border border-white/10 bg-white/[0.04] p-3">
            <item.icon size={16} className="mb-2 text-cyanline" />
            <div className="text-xs text-slate-400">{item.label}</div>
            <div className="text-xl font-semibold">{item.value}<span className="ml-1 text-xs text-slate-400">{item.suffix}</span></div>
          </div>
        ))}
      </div>
    </section>
  );
}
