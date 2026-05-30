"use client";

import type { CaseMatch } from "@/lib/types";

export default function HistoricalCaseMatch({ matches }: { matches: CaseMatch[] }) {
  return (
    <section className="glass rounded-lg p-4">
      <div className="flex items-center justify-between gap-3">
        <h2 className="text-sm font-semibold text-white">Historical Case Match</h2>
        <span className="rounded-full border border-amber/30 bg-amber/10 px-2 py-1 text-[11px] text-amber">Analogy only</span>
      </div>
      <p className="mt-2 text-xs text-slate-400">Historical analogy only - not operational guidance.</p>
      <div className="mt-3 space-y-3">
        {matches.length === 0 && <div className="rounded-md bg-white/[0.04] p-3 text-sm text-slate-400">Run simulation to compare current tags against historical memory.</div>}
        {matches.map((match) => (
          <article key={match.case_id} className="rounded-md border border-white/10 bg-white/[0.04] p-3">
            <div className="flex justify-between gap-2 text-sm">
              <h3 className="font-semibold text-white">{match.case_name}</h3>
              <span className="text-cyanline">{Math.round(match.similarity_score * 100)}%</span>
            </div>
            <div className="mt-2 flex flex-wrap gap-1">
              {match.matched_tags.map((tag) => <span key={tag} className="rounded bg-cyanline/10 px-2 py-1 text-[11px] text-cyanline">{tag}</span>)}
            </div>
            <h4 className="mt-3 text-xs font-semibold uppercase text-slate-400">What happened</h4>
            <p className="mt-1 text-xs leading-5 text-slate-300">{match.situation_summary}</p>
            <h4 className="mt-3 text-xs font-semibold uppercase text-slate-400">System lesson</h4>
            <p className="mt-1 text-xs leading-5 text-slate-300">{match.system_lesson}</p>
            <h4 className="mt-3 text-xs font-semibold uppercase text-slate-400">How NAS Pulse uses this</h4>
            <ul className="mt-1 space-y-1 text-xs leading-5 text-slate-300">
              {match.how_nas_pulse_uses_it.slice(0, 3).map((item) => <li key={item}>- {item}</li>)}
            </ul>
          </article>
        ))}
      </div>
    </section>
  );
}
