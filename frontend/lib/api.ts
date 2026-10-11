import type { Featured, HistoryPoint, Link, Outcome, QueueResult, ReconResult } from "./types";

const BASE = (process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000").replace(/\/$/, "");

export class ApiError extends Error {
  constructor(message: string, public status: number) { super(message); }
}

async function call<T>(path: string, init?: RequestInit): Promise<T> {
  let res: Response;
  try {
    res = await fetch(`${BASE}${path}`, { ...init, headers: { "Content-Type": "application/json" } });
  } catch {
    throw new ApiError("Cannot reach the prediction server. It may be waking up. Wait a few seconds and try again.", 0);
  }
  if (!res.ok) {
    let detail = `Request failed (${res.status}).`;
    try {
      const j = await res.json();
      if (typeof j.detail === "string") detail = j.detail;
      else if (Array.isArray(j.detail)) detail = "Some inputs are not valid. Check the link and time you selected.";
    } catch { /* ignore */ }
    throw new ApiError(detail, res.status);
  }
  return res.json() as Promise<T>;
}

export const api = {
  health: () => call<{ status: string; data_source: string }>("/health"),
  links: () => call<{ data_source: string; links: Link[] }>("/links"),
  datesFor: (id: number) => call<{ dates: string[]; featured: Featured[] }>(`/scenarios?link_id=${id}`),
  timesFor: (id: number, date: string) => call<{ times: string[] }>(`/scenarios?link_id=${id}&date=${date}`),
  history: (id: number, ts: string) =>
    call<{ history: HistoryPoint[]; queue_speed_kmh: number; free_flow_kmh: number }>(`/history?link_id=${id}&timestamp=${encodeURIComponent(ts)}`),
  predict: (id: number, ts: string) => call<QueueResult>("/predict/queue", { method: "POST", body: JSON.stringify({ link_id: id, timestamp: ts }) }),
  outcome: (id: number, ts: string) => call<Outcome>(`/outcome?link_id=${id}&timestamp=${encodeURIComponent(ts)}`),
  reconstruct: (id: number, start: string, end: string, rate: number, seed: number) =>
    call<ReconResult>("/reconstruct", { method: "POST", body: JSON.stringify({ link_id: id, start, end, mask_rate: rate, seed }) }),
  modelInfo: () => call<any>("/model/info"),
};
