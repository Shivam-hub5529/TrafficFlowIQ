"use client";
import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { useScenario } from "@/lib/useScenario";
import type { HistoryPoint, Outcome, QueueResult } from "@/lib/types";
import TimeSeriesChart from "@/components/TimeSeriesChart";
import VmsPanel from "@/components/VmsPanel";
import ForecastStrip from "@/components/ForecastStrip";
import ReasonList from "@/components/ReasonList";
import { ErrorBanner, Field, buttonCls, fmtDate, hhmm, selectCls } from "@/components/Field";

export default function PredictPage() {
  const s = useScenario();
  const ts = s.date && s.time ? `${s.date}T${s.time}:00` : "";
  const [preview, setPreview] = useState<{ history: HistoryPoint[]; queue_speed_kmh: number } | null>(null);
  const [result, setResult] = useState<QueueResult | null>(null);
  const [outcome, setOutcome] = useState<Outcome | null>(null);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");

  useEffect(() => {
    setResult(null); setOutcome(null); setErr("");
    if (s.linkId === null || !ts) { setPreview(null); return; }
    api.history(s.linkId, ts).then(setPreview).catch((e) => { setPreview(null); setErr(e.message); });
  }, [s.linkId, ts]);

  const run = async () => {
    if (s.linkId === null || !ts) return;
    setBusy(true); setErr(""); setOutcome(null);
    try { setResult(await api.predict(s.linkId, ts)); } catch (e: any) { setErr(e.message); } finally { setBusy(false); }
  };
  const reveal = async () => {
    if (s.linkId === null || !ts) return;
    try { setOutcome(await api.outcome(s.linkId, ts)); } catch (e: any) { setErr(e.message); }
  };

  const hist = result?.history ?? preview?.history ?? [];
  const fut = outcome?.future ?? [];
  const labels = [...hist, ...fut].map((p) => p.t.slice(11, 16));
  const thr = result?.queue_speed_kmh ?? preview?.queue_speed_kmh;

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-4xl font-extrabold">Predict queue risk</h1>
        <p className="mt-2 max-w-xl">Choose a link and a moment from the held-out test period. The model only sees the hour before that moment.</p>
      </div>

      {(s.error) && <ErrorBanner message={s.error} />}
      {s.source === "synthetic" && (
        <p className="rounded border-l-4 border-amber bg-[#FBF1D3] px-4 py-2 text-sm">Demo data: this deployment uses synthetic traffic that mimics TrafficFlowBench. Results show how the system works, not real roads.</p>
      )}

      <section aria-label="Choose scenario" className="space-y-4 rounded-md border-2 border-ink/60 bg-paint p-5">
        <div className="grid gap-4 sm:grid-cols-3">
          <Field label="Freeway link">
            <select className={selectCls} disabled={s.loading || !s.links.length} value={s.linkId ?? ""} onChange={(e) => s.setLinkId(Number(e.target.value))}>
              {s.links.map((l) => <option key={l.link_id} value={l.link_id}>{l.name}</option>)}
            </select>
          </Field>
          <Field label="Date">
            <select className={selectCls} value={s.date} onChange={(e) => s.setDate(e.target.value)} disabled={!s.dates.length}>
              <option value="">Select a date</option>
              {s.dates.map((d) => <option key={d} value={d}>{fmtDate(d)}</option>)}
            </select>
          </Field>
          <Field label="Time (5-minute steps)">
            <select className={selectCls} value={s.time} onChange={(e) => s.setTime(e.target.value)} disabled={!s.times.length}>
              <option value="">Select a time</option>
              {s.times.map((t) => <option key={t} value={t}>{t}</option>)}
            </select>
          </Field>
        </div>

        {s.link && (
          <p className="text-sm">
            {s.link.lanes} lanes, {s.link.length_km} km. Free-flow speed {s.link.ffs_kmh} km/h, so a queue means {s.link.queue_threshold_kmh} km/h or slower.
            {s.link.ramp_type !== "none" && ` This link has an ${s.link.ramp_type}-ramp sensor.`}
          </p>
        )}

        {s.featured.length > 0 && (
          <div>
            <p className="text-sm font-semibold">Try one of these moments</p>
            <div className="mt-2 flex flex-wrap gap-2">
              {s.featured.map((f) => (
                <button key={f.timestamp} onClick={() => s.pick(f.timestamp)} className="rounded border-2 border-sign px-3 py-1 text-sm hover:bg-mist">
                  {fmtDate(f.timestamp.slice(0, 10))}, {hhmm(f.timestamp)}: {f.title}
                </button>
              ))}
            </div>
          </div>
        )}

        <button className={buttonCls} disabled={!ts || busy} onClick={run}>{busy ? "Predicting…" : "Predict queue risk"}</button>
      </section>

      {err && <ErrorBanner message={err} />}

      {!result && !preview && !err && <p className="text-ink/70">Select a link, date and time to see the last hour of traffic before predicting.</p>}

      {hist.length > 0 && (
        <section aria-label="Speed history">
          <h2 className="text-2xl font-bold">{outcome ? "What actually happened" : "Speed over the last hour"}</h2>
          <TimeSeriesChart
            ariaLabel="Speed in kilometres per hour over time compared with the queue threshold"
            unit="km/h" labels={labels} threshold={thr ? { value: thr, label: `queue at ${thr} km/h` } : undefined}
            nowIndex={outcome ? hist.length - 1 : undefined}
            series={[
              { name: "Speed seen by the model", color: "#0B5C45", kind: "line", values: [...hist.map((p) => p.speed), ...fut.map(() => null)] },
              ...(outcome ? [{ name: "Speed in the next 30 minutes", color: "#C0392B", kind: "line" as const, dashed: true, values: [...hist.map((_, i) => (i === hist.length - 1 ? hist[i].speed : null)), ...fut.map((p) => p.speed)] }] : []),
            ]}
          />
        </section>
      )}

      {result && (
        <div className="space-y-8">
          <VmsPanel r={result} linkName={s.link?.name ?? `Link ${result.link_id}`} />
          <ForecastStrip horizon={result.horizon_risk} />
          <ReasonList r={result} />
          <div>
            {!outcome ? (
              <button onClick={reveal} className="rounded border-2 border-sign px-4 py-2 font-semibold hover:bg-mist">Reveal what actually happened</button>
            ) : (
              <p className="rounded border-l-4 border-sign bg-mist px-4 py-3">
                {outcome.queued_in_next_30 ? `A queue did form: speed fell to ${outcome.min_speed_kmh} km/h.` : `No queue formed: speed stayed above ${result.queue_speed_kmh} km/h (lowest ${outcome.min_speed_kmh} km/h).`}
              </p>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
