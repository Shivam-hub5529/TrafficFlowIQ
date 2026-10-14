"use client";
import { useState } from "react";
import { api } from "@/lib/api";
import { useScenario } from "@/lib/useScenario";
import type { ReconResult } from "@/lib/types";
import TimeSeriesChart from "@/components/TimeSeriesChart";
import { ErrorBanner, Field, buttonCls, fmtDate, selectCls } from "@/components/Field";

const addMin = (iso: string, m: number) => {
  const d = new Date(iso + "Z"); d.setUTCMinutes(d.getUTCMinutes() + m);
  return d.toISOString().slice(0, 19);
};

export default function ReconstructPage() {
  const s = useScenario();
  const [hours, setHours] = useState(2);
  const [rate, setRate] = useState(0.2);
  const [seed, setSeed] = useState(7);
  const [res, setRes] = useState<ReconResult | null>(null);
  const [showPhysics, setShowPhysics] = useState(false);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");

  const start = s.date && s.time ? `${s.date}T${s.time}:00` : "";
  const run = async (sd = seed) => {
    if (s.linkId === null || !start) return;
    setBusy(true); setErr("");
    try { setRes(await api.reconstruct(s.linkId, start, addMin(start, hours * 60), rate, sd)); } catch (e: any) { setErr(e.message); setRes(null); } finally { setBusy(false); }
  };
  const retry = () => { const n = seed + 1; setSeed(n); run(n); };

  const labels = res?.points.map((p) => p.t.slice(11, 16)) ?? [];
  const mk = (key: "speed" | "flow") => {
    const P = res!.points;
    const miss = (p: (typeof P)[number]) => (key === "speed" ? p.was_missing_speed : p.was_missing_flow);
    const g = (p: (typeof P)[number], k: string) => (p as any)[`${key}_${k}`] as number | null;
    return [
      { name: "True value (hidden from the model)", color: "#A9B0A8", kind: "line" as const, width: 5, values: P.map((p) => g(p, "true")) },
      { name: "Sensor reading kept", color: "#26302C", kind: "line" as const, values: P.map((p) => (miss(p) ? null : g(p, "obs"))) },
      { name: "Straight-line fill (baseline)", color: "#C0392B", kind: "dots" as const, values: P.map((p) => (miss(p) ? g(p, "interp") : null)) },
      { name: "TrafficFlowIQ reconstruction", color: "#0B5C45", kind: "dots" as const, values: P.map((p) => (miss(p) ? g(p, "est") : null)) },
    ];
  };

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-4xl font-extrabold">Fill sensor gaps</h1>
        <p className="mt-2 max-w-xl">Sensors drop out. Choose a window, hide some readings on purpose, and see how closely the model rebuilds them.</p>
      </div>
      {s.error && <ErrorBanner message={s.error} />}

      <section className="space-y-4 rounded-md border-2 border-ink/60 bg-paint p-5">
        <div className="grid gap-4 sm:grid-cols-3">
          <Field label="Freeway link">
            <select className={selectCls} value={s.linkId ?? ""} onChange={(e) => s.setLinkId(Number(e.target.value))}>
              {s.links.map((l) => <option key={l.link_id} value={l.link_id}>{l.name}</option>)}
            </select>
          </Field>
          <Field label="Date">
            <select className={selectCls} value={s.date} onChange={(e) => s.setDate(e.target.value)} disabled={!s.dates.length}>
              <option value="">Select a date</option>
              {s.dates.map((d) => <option key={d} value={d}>{fmtDate(d)}</option>)}
            </select>
          </Field>
          <Field label="Window start">
            <select className={selectCls} value={s.time} onChange={(e) => s.setTime(e.target.value)} disabled={!s.times.length}>
              <option value="">{s.timesLoading ? "Loading times…" : s.date ? "Select a time" : "Pick a date first"}</option>
              {s.times.map((t) => <option key={t} value={t}>{t}</option>)}
            </select>
          </Field>
          <Field label="Window length">
            <select className={selectCls} value={hours} onChange={(e) => setHours(Number(e.target.value))}>
              {[1, 2, 3, 4].map((h) => <option key={h} value={h}>{h} hour{h > 1 ? "s" : ""}</option>)}
            </select>
          </Field>
          <Field label={`Readings hidden: ${Math.round(rate * 100)}%`}>
            <input type="range" min={0.1} max={0.4} step={0.05} value={rate} onChange={(e) => setRate(Number(e.target.value))} className="w-full accent-[#0B5C45]" />
          </Field>
        </div>
        <div className="flex flex-wrap items-center gap-4">
          <button className={buttonCls} disabled={!start || busy} onClick={() => run()}>{busy ? "Reconstructing…" : "Hide readings and reconstruct"}</button>
          {res && <button onClick={retry} className="underline underline-offset-4">Try another dropout pattern</button>}
        </div>
      </section>

      {err && <ErrorBanner message={err} />}

      {res && (
        <div className="space-y-8">
          <section>
            <h2 className="text-2xl font-bold">Speed</h2>
            <TimeSeriesChart ariaLabel="Speed true versus reconstructed" unit="km/h" labels={labels} series={mk("speed")} />
          </section>
          <section>
            <h2 className="text-2xl font-bold">Flow per lane</h2>
            <TimeSeriesChart ariaLabel="Flow per lane true versus reconstructed" unit="veh/h/lane" labels={labels} series={mk("flow")} />
          </section>
          <section>
            <h2 className="text-2xl font-bold">How close was it?</h2>
            <table className="mt-3 w-full text-left">
              <thead><tr className="border-b-2 border-ink/60"><th className="py-2">Typical error (RMSE)</th><th>TrafficFlowIQ</th><th>Straight-line fill</th></tr></thead>
              <tbody>
                <tr className="border-b border-lane"><td className="py-2">Speed ({res.n_masked_speed} hidden)</td><td className="font-bold">{res.rmse.speed ?? "n/a"} km/h</td><td>{res.rmse_baseline_linear.speed ?? "n/a"} km/h</td></tr>
                <tr className="border-b border-lane"><td className="py-2">Flow per lane ({res.n_masked_flow} hidden)</td><td className="font-bold">{res.rmse.flow_per_lane ?? "n/a"} veh/h</td><td>{res.rmse_baseline_linear.flow_per_lane ?? "n/a"} veh/h</td></tr>
              </tbody>
            </table>
          </section>
          <section>
            <label className="inline-flex items-center gap-2 font-semibold">
              <input type="checkbox" checked={showPhysics} onChange={(e) => setShowPhysics(e.target.checked)} className="h-5 w-5 accent-[#0B5C45]" /> Show physics check
            </label>
            {showPhysics && (
              <div className="mt-3 rounded border-l-4 border-sign bg-mist px-4 py-3">
                <p>{res.physics.explanation}</p>
                <ul className="mt-2 list-disc pl-5 text-sm">{res.physics.checks.map((c) => <li key={c}>{c}</li>)}</ul>
                <p className="mt-2 text-sm">Out of {res.physics.checked_points} reconstructed points, {res.physics.violations_pct_raw}% broke a rule before correction and {res.physics.violations_pct_after_correction}% after.</p>
              </div>
            )}
          </section>
        </div>
      )}
    </div>
  );
}
