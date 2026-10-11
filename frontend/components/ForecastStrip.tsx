export default function ForecastStrip({ horizon }: { horizon: Record<string, number> }) {
  const keys = Object.keys(horizon).sort((a, b) => Number(a) - Number(b));
  return (
    <div>
      <h3 className="text-xl font-bold">Chance of being queued, minute by minute</h3>
      <ol className="mt-3 grid grid-cols-3 gap-2 sm:grid-cols-6">
        {keys.map((k) => {
          const p = horizon[k];
          return (
            <li key={k} className="rounded border border-lane bg-paint p-2 text-center">
              <div className="text-sm text-ink/70">in {k} min</div>
              <div className="font-display text-xl font-bold">{Math.round(p * 100)}%</div>
              <div className="mt-1 h-2 w-full rounded-sm bg-concrete" aria-hidden>
                <div className="h-2 rounded-sm" style={{ width: `${Math.max(p * 100, 2)}%`, background: p >= 0.6 ? "#C0392B" : p >= 0.3 ? "#F2B21B" : "#0B5C45" }} />
              </div>
            </li>
          );
        })}
      </ol>
    </div>
  );
}
