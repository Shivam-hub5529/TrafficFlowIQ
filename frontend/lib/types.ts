export type Link = {
  link_id: number; name: string; lanes: number; length_km: number; ffs_kmh: number;
  queue_threshold_kmh: number; ramp_type: "on" | "off" | "none";
};
export type Featured = { timestamp: string; kind: string; title: string };
export type HistoryPoint = { t: string; speed: number | null };
export type Reason = { concept: string; direction: "up" | "down"; strength: number; text: string };
export type QueueResult = {
  link_id: number; timestamp: string; risk: number; label: "low" | "moderate" | "high"; verdict: string;
  threshold_used: number; horizon_risk: Record<string, number>; queue_speed_kmh: number; free_flow_kmh: number;
  history: HistoryPoint[]; reasons: Reason[]; advanced: { feature: string; value: number | null; contribution: number }[];
  data_quality: { ramp_available: boolean | null; missing_speed_readings: number; note: string };
  model_version: string;
};
export type Outcome = { future: HistoryPoint[]; queued_in_next_30: boolean | null; min_speed_kmh: number | null };
export type ReconPoint = {
  t: string; was_missing_speed: boolean; was_missing_flow: boolean;
  speed_obs: number | null; speed_est: number | null; speed_true: number | null;
  flow_obs: number | null; flow_est: number | null; flow_true: number | null;
  speed_interp: number | null; flow_interp: number | null;
};
export type ReconResult = {
  link_id: number; points: ReconPoint[]; n_masked_speed: number; n_masked_flow: number;
  rmse: Record<string, number | null>; rmse_baseline_linear: Record<string, number | null>;
  physics: { checked_points: number; violations_pct_raw: number; violations_pct_after_correction: number; checks: string[]; explanation: string };
  model_version: string;
};
