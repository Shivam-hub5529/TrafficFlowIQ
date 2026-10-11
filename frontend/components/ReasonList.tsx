import type { QueueResult } from "@/lib/types";

export default function ReasonList({ r }: { r: QueueResult }) {
  return (
    <div>
      <h3 className="text-xl font-bold">Why this prediction</h3>
      <ul className="mt-3 space-y-2">
        {r.reasons.map((x) => (
          <li key={x.concept} className="flex items-start gap-3 rounded border border-lane bg-paint p-3">
            <span aria-label={x.direction === "up" ? "raises the risk" : "lowers the risk"}
              className={`mt-0.5 inline-flex h-7 w-7 shrink-0 items-center justify-center rounded-sm text-lg font-bold ${x.direction === "up" ? "bg-brake text-paint" : "bg-sign text-paint"}`}>
              {x.direction === "up" ? "▲" : "▼"}
            </span>
            <span>{x.text}<span className="block text-sm text-ink/70">{x.direction === "up" ? "Raises the risk" : "Lowers the risk"}</span></span>
          </li>
        ))}
      </ul>
      <p className={`mt-3 rounded border-l-4 px-3 py-2 text-sm ${r.data_quality.ramp_available === false ? "border-amber bg-[#FBF1D3]" : "border-sign bg-mist"}`}>
        {r.data_quality.note}
        {r.data_quality.missing_speed_readings > 0 && ` ${r.data_quality.missing_speed_readings} of the last 12 speed readings were missing.`}
      </p>
      <details className="mt-3">
        <summary className="underline underline-offset-4">Advanced details</summary>
        <table className="mt-2 w-full text-sm">
          <thead><tr className="text-left"><th className="py-1 pr-2">Signal</th><th className="pr-2">Value</th><th>Push on risk</th></tr></thead>
          <tbody>
            {r.advanced.map((a) => (
              <tr key={a.feature} className="border-t border-lane">
                <td className="py-1 pr-2 font-mono text-xs">{a.feature}</td><td className="pr-2">{a.value ?? "missing"}</td>
                <td>{a.contribution > 0 ? "+" : ""}{a.contribution}</td>
              </tr>
            ))}
          </tbody>
        </table>
        <p className="mt-1 text-xs text-ink/70">Values are SHAP contributions in log-odds units from the LightGBM model.</p>
      </details>
    </div>
  );
}
