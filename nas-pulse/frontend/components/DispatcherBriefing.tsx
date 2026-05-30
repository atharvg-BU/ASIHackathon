"use client";

export default function DispatcherBriefing({ text }: { text?: string }) {
  return (
    <section className="glass rounded-lg p-4">
      <h2 className="text-sm font-semibold text-white">Dispatcher Briefing</h2>
      <p className="mt-3 text-sm leading-6 text-slate-300">
        {text || "Run simulation or optimization to generate a deterministic dispatcher-style briefing."}
      </p>
    </section>
  );
}
