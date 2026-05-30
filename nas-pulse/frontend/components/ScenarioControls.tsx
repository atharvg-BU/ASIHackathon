"use client";

import { Loader2, Play, Radar, Route } from "lucide-react";
import TimeSlider from "./TimeSlider";

export default function ScenarioControls(props: {
  time: string;
  setTime: (value: string) => void;
  weatherEnabled: boolean;
  setWeatherEnabled: (value: boolean) => void;
  constraintEnabled: boolean;
  setConstraintEnabled: (value: boolean) => void;
  onSimulate: () => void;
  onOptimize: () => void;
  loading: boolean;
}) {
  return (
    <section className="glass rounded-lg p-4">
      <div className="mb-4 flex items-center gap-2 text-sm font-semibold text-white">
        <Radar size={16} className="text-cyanline" />
        Scenario Controls
      </div>
      <TimeSlider value={props.time} onChange={props.setTime} />
      <label className="mt-4 flex items-center justify-between rounded-md bg-white/5 p-3 text-sm">
        Chicago weather cell
        <input type="checkbox" checked={props.weatherEnabled} onChange={(e) => props.setWeatherEnabled(e.target.checked)} />
      </label>
      <label className="mt-2 flex items-center justify-between rounded-md bg-white/5 p-3 text-sm">
        Airspace constraint
        <input type="checkbox" checked={props.constraintEnabled} onChange={(e) => props.setConstraintEnabled(e.target.checked)} />
      </label>
      <div className="mt-4 grid grid-cols-2 gap-2">
        <button onClick={props.onSimulate} className="flex items-center justify-center gap-2 rounded-md bg-cyanline px-3 py-2 text-sm font-semibold text-slate-950">
          {props.loading ? <Loader2 size={16} className="animate-spin" /> : <Play size={16} />} Sim
        </button>
        <button onClick={props.onOptimize} className="flex items-center justify-center gap-2 rounded-md bg-runway px-3 py-2 text-sm font-semibold text-slate-950">
          <Route size={16} /> Optimize
        </button>
      </div>
    </section>
  );
}
