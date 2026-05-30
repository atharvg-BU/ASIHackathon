"use client";

export default function TimeSlider({ value, onChange }: { value: string; onChange: (value: string) => void }) {
  const [hh, mm] = value.split(":").map(Number);
  const minutes = hh * 60 + mm;
  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between text-xs uppercase tracking-wide text-slate-400">
        <span>Traffic Clock</span>
        <span className="text-cyanline">{value} UTC</span>
      </div>
      <input
        className="w-full accent-cyanline"
        type="range"
        min={0}
        max={1439}
        step={5}
        value={minutes}
        onChange={(event) => {
          const total = Number(event.target.value);
          const nextH = String(Math.floor(total / 60)).padStart(2, "0");
          const nextM = String(total % 60).padStart(2, "0");
          onChange(`${nextH}:${nextM}`);
        }}
      />
    </div>
  );
}
