import type { QueueResult } from "@/lib/types";

const COPY = {
  low: { l1: "CLEAR AHEAD", color: "#8FE3A1" },
  moderate: { l1: "QUEUE POSSIBLE", color: "#FFB000" },
  high: { l1: "QUEUE LIKELY", color: "#FFB000" },
} as const;

export default function VmsPanel({ r, linkName }: { r: QueueResult; linkName: string }) {
  const c = COPY[r.label];
  return (
    <section aria-label="Prediction result" className="rounded-md border-4 border-[#3A4440] bg-panel p-5 sm:p-7">
      <p className="font-led text-sm tracking-wide text-[#9AA59F]">{linkName}</p>
      <div className="led-in mt-3" style={{ color: c.color }}>
        <p className="font-led text-3xl font-bold leading-tight sm:text-5xl">{c.l1}</p>
        <p className="mt-2 font-led text-xl sm:text-2xl">{Math.round(r.risk * 100)}% CHANCE, NEXT 30 MIN</p>
      </div>
      <p className="mt-4 text-base text-paint">{r.verdict}. The model flags a queue when this chance is above {Math.round(r.threshold_used * 100)}%.</p>
    </section>
  );
}
