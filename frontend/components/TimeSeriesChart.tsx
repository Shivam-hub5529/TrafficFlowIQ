"use client";

export type Series = { name: string; color: string; values: (number | null)[]; kind: "line" | "dots"; dashed?: boolean; width?: number };
type Props = {
  labels: string[]; series: Series[]; threshold?: { value: number; label: string };
  yMin?: number; yMax?: number; unit: string; ariaLabel: string; nowIndex?: number; height?: number;
};

const W = 640, PAD = { l: 46, r: 12, t: 14, b: 28 };

export default function TimeSeriesChart({ labels, series, threshold, yMin = 0, yMax, unit, ariaLabel, nowIndex, height = 230 }: Props) {
  const H = height;
  const all = series.flatMap((s) => s.values).filter((v): v is number => v !== null);
  const top = yMax ?? Math.max(10, ...all, threshold?.value ?? 0) * 1.08;
  const n = Math.max(labels.length - 1, 1);
  const x = (i: number) => PAD.l + (i / n) * (W - PAD.l - PAD.r);
  const y = (v: number) => PAD.t + (1 - (v - yMin) / (top - yMin)) * (H - PAD.t - PAD.b);
  const step = Math.max(1, Math.ceil(labels.length / 7));
  const ticks = [0, 0.5, 1].map((f) => yMin + f * (top - yMin));

  const paths = (s: Series) => {
    const segs: string[] = [];
    let cur = "";
    s.values.forEach((v, i) => {
      if (v === null) { if (cur) segs.push(cur); cur = ""; return; }
      cur += `${cur ? "L" : "M"}${x(i).toFixed(1)},${y(v).toFixed(1)}`;
    });
    if (cur) segs.push(cur);
    return segs;
  };

  return (
    <figure className="w-full">
      <svg viewBox={`0 0 ${W} ${H}`} role="img" aria-label={ariaLabel} className="w-full h-auto">
        {ticks.map((t) => (
          <g key={t}>
            <line x1={PAD.l} x2={W - PAD.r} y1={y(t)} y2={y(t)} stroke="#B9BFB7" strokeWidth="1" />
            <text x={PAD.l - 8} y={y(t) + 4} textAnchor="end" fontSize="12" fill="#4B5651">{Math.round(t)}</text>
          </g>
        ))}
        {labels.map((l, i) => i % step === 0 && (
          <text key={i} x={x(i)} y={H - 8} textAnchor="middle" fontSize="12" fill="#4B5651">{l}</text>
        ))}
        {threshold && (
          <g>
            <line x1={PAD.l} x2={W - PAD.r} y1={y(threshold.value)} y2={y(threshold.value)} stroke="#C0392B" strokeWidth="2" strokeDasharray="7 5" />
            <text x={W - PAD.r - 2} y={y(threshold.value) - 6} textAnchor="end" fontSize="12" fontWeight="600" fill="#C0392B">{threshold.label}</text>
          </g>
        )}
        {nowIndex !== undefined && nowIndex >= 0 && (
          <g>
            <line x1={x(nowIndex)} x2={x(nowIndex)} y1={PAD.t} y2={H - PAD.b} stroke="#26302C" strokeWidth="1.5" />
            <text x={x(nowIndex) + 5} y={PAD.t + 10} fontSize="12" fill="#26302C">prediction time</text>
          </g>
        )}
        {series.map((s) =>
          s.kind === "line" ? paths(s).map((d, k) => (
            <path key={`${s.name}${k}`} d={d} fill="none" stroke={s.color} strokeWidth={s.width ?? 2.5} strokeDasharray={s.dashed ? "6 4" : undefined} strokeLinejoin="round" />
          )) : s.values.map((v, i) => v === null ? null : <circle key={`${s.name}${i}`} cx={x(i)} cy={y(v)} r="4.2" fill={s.color} stroke="#FAFAF6" strokeWidth="1.2" />)
        )}
        <text x={4} y={12} fontSize="12" fill="#4B5651">{unit}</text>
      </svg>
      <figcaption className="mt-2 flex flex-wrap gap-x-5 gap-y-1 text-sm">
        {series.map((s) => (
          <span key={s.name} className="inline-flex items-center gap-2">
            <span aria-hidden className="inline-block h-[3px] w-5" style={{ background: s.kind === "line" ? s.color : "transparent", borderTop: s.kind === "dots" ? `4px dotted ${s.color}` : undefined }} />
            {s.name}
          </span>
        ))}
      </figcaption>
    </figure>
  );
}
