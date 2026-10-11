"use client";
import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { ErrorBanner } from "@/components/Field";

const f = (x?: number) => (x === undefined || Number.isNaN(x) ? "n/a" : x.toFixed(3));

export default function About() {
  const [info, setInfo] = useState<any>(null);
  const [err, setErr] = useState("");
  useEffect(() => { api.modelInfo().then(setInfo).catch((e) => setErr(e.message)); }, []);

  const rows: [string, any][] = info ? [
    ["Persistence (queued now means queued later)", info.baselines.persistence.test],
    ["Historical average by time of day", info.baselines.historical_average.test],
    ["Logistic regression", info.baselines.logistic_regression.test],
    ["LightGBM + calibration (final)", info.lightgbm.test],
  ] : [];

  return (
    <div className="space-y-8">
      <h1 className="text-4xl font-extrabold">About the model</h1>
      {err && <ErrorBanner message={err} />}
      {info?.data_source === "synthetic" && (
        <p className="rounded border-l-4 border-amber bg-[#FBF1D3] px-4 py-2">These numbers come from synthetic stand-in data. Retrain on TrafficFlowBench for real results. Synthetic traffic is easier to predict than real traffic.</p>
      )}
      <section className="space-y-2">
        <h2 className="text-2xl font-bold">How it avoids peeking at the future</h2>
        <ul className="list-disc space-y-1 pl-5">
          <li>Every input is computed from the 60 minutes up to the prediction time.</li>
          <li>Training, validation and test periods are whole days in time order, with a 90-minute gap between them.</li>
          <li>Missing or low-quality ramp readings are treated as missing evidence, never as zero flow.</li>
        </ul>
      </section>
      {info && (
        <>
          <section>
            <h2 className="text-2xl font-bold">Queue prediction, test period</h2>
            <div className="mt-3 overflow-x-auto">
              <table className="w-full min-w-[34rem] text-left">
                <thead><tr className="border-b-2 border-ink/60"><th className="py-2">Model</th><th>F1</th><th>Precision</th><th>Recall</th><th>IoU</th><th>PR-AUC</th><th>ROC-AUC</th></tr></thead>
                <tbody>
                  {rows.map(([n, m], i) => (
                    <tr key={n} className={`border-b border-lane ${i === 3 ? "font-bold" : ""}`}>
                      <td className="py-2 pr-2">{n}</td><td>{f(m.f1)}</td><td>{f(m.precision)}</td><td>{f(m.recall)}</td><td>{f(m.iou)}</td><td>{f(m.pr_auc)}</td><td>{f(m.roc_auc)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>
          <section>
            <h2 className="text-2xl font-bold">Sensor-gap reconstruction, test period</h2>
            <ul className="mt-2 space-y-1">
              <li>Speed RMSE: <b>{f(info.reconstruction.speed.rmse_lightgbm)} km/h</b> (straight-line fill: {f(info.reconstruction.speed.rmse_linear_interpolation)})</li>
              <li>Flow per lane RMSE: <b>{f(info.reconstruction.flow_pl.rmse_lightgbm)} veh/h</b> (straight-line fill: {f(info.reconstruction.flow_pl.rmse_linear_interpolation)})</li>
            </ul>
          </section>
          <section>
            <h2 className="text-2xl font-bold">Limits</h2>
            <ul className="list-disc space-y-1 pl-5">
              <li>It replays recorded windows; it does not connect to live sensors.</li>
              <li>A queue caused by an event after the prediction time, such as a crash, cannot be foreseen.</li>
              <li>The physics check is a simple rule set, not a full traffic simulation.</li>
            </ul>
            <p className="mt-3 text-sm text-ink/70">Model {info.queue_model_version}, trained {info.trained_at}.</p>
          </section>
        </>
      )}
    </div>
  );
}
