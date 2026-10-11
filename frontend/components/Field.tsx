import type { ReactNode } from "react";

export function Field({ label, children, hint }: { label: string; children: ReactNode; hint?: string }) {
  return (
    <label className="block">
      <span className="mb-1 block text-sm font-semibold">{label}</span>
      {children}
      {hint && <span className="mt-1 block text-sm text-ink/70">{hint}</span>}
    </label>
  );
}

export const selectCls = "w-full rounded border-2 border-ink/70 bg-paint px-3 py-2 text-base";
export const buttonCls = "rounded bg-sign px-5 py-3 font-display text-lg font-bold text-paint hover:bg-signdark";

export function ErrorBanner({ message }: { message: string }) {
  return <div role="alert" className="rounded border-l-4 border-brake bg-[#F8DAD5] px-4 py-3">{message}</div>;
}

export const fmtDate = (d: string) => new Date(d + "T12:00:00").toLocaleDateString("en-US", { weekday: "short", month: "short", day: "numeric" });
export const hhmm = (iso: string) => iso.slice(11, 16);
