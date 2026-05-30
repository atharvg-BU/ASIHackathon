"use client";

import type { SimResult } from "@/lib/types";
import { riskColor } from "@/lib/api";

export default function DelayCascadeGraph({ simulation }: { simulation?: SimResult }) {
  const nodes = simulation?.delay_cascade_graph.nodes.slice(0, 14) || [];
  const edges = simulation?.delay_cascade_graph.edges || [];
  return (
    <section className="glass rounded-lg p-4">
      <h2 className="text-sm font-semibold text-white">Delay Cascade</h2>
      <svg viewBox="0 0 700 260" className="mt-3 h-[260px] w-full rounded-md bg-slate-950/50">
        {nodes.length === 0 && <text x="24" y="42" fill="#94a3b8" fontSize="14">Run simulation to reveal propagation graph.</text>}
        {edges.map((edge, idx) => {
          const a = nodes.findIndex((n) => n.id === edge.source);
          const b = nodes.findIndex((n) => n.id === edge.target);
          if (a < 0 || b < 0) return null;
          const ax = 70 + (a % 7) * 95;
          const ay = 70 + Math.floor(a / 7) * 105;
          const bx = 70 + (b % 7) * 95;
          const by = 70 + Math.floor(b / 7) * 105;
          return <line key={`${edge.source}-${edge.target}-${idx}`} x1={ax} y1={ay} x2={bx} y2={by} stroke="#51667a" strokeWidth="1.5" />;
        })}
        {nodes.map((node, idx) => {
          const x = 70 + (idx % 7) * 95;
          const y = 70 + Math.floor(idx / 7) * 105;
          return (
            <g key={node.id}>
              <circle cx={x} cy={y} r="24" fill={riskColor(node.risk)} fillOpacity="0.18" stroke={riskColor(node.risk)} strokeWidth="2" />
              <text x={x} y={y - 2} textAnchor="middle" fill="#e8f4ff" fontSize="10" fontWeight="700">{node.id}</text>
              <text x={x} y={y + 12} textAnchor="middle" fill="#94a3b8" fontSize="10">{node.delay}m</text>
            </g>
          );
        })}
      </svg>
    </section>
  );
}
