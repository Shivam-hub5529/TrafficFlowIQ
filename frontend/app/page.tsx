import Link from "next/link";
import { buttonCls } from "@/components/Field";

export default function Home() {
  return (
    <div className="space-y-12">
      <section>
        <h1 className="max-w-2xl text-4xl font-extrabold sm:text-6xl">Will this stretch of freeway back up in the next 30 minutes?</h1>
        <p className="mt-5 max-w-xl text-lg">
          Pick a freeway link and a moment in time. TrafficFlowIQ reads the previous hour of traffic and tells you the chance of a queue, and why.
        </p>
        <div className="mt-6 flex flex-wrap items-center gap-4">
          <Link href="/predict" className={buttonCls}>Check a link</Link>
          <Link href="/reconstruct" className="underline underline-offset-4">Or see how it fills in missing sensor data</Link>
        </div>
      </section>

      <div className="lane-rule" aria-hidden />

      <section className="grid gap-8 sm:grid-cols-3">
        {[
          ["What counts as a queue", "A link is queued when traffic moves at 60% of its free-flow speed or slower."],
          ["What the model sees", "Only the last 60 minutes of speed, flow and occupancy, plus ramp data when it is trustworthy. Never the future."],
          ["What you get back", "A risk percentage, a minute-by-minute forecast, and the top reasons in plain language."],
        ].map(([t, d]) => (
          <div key={t}>
            <h2 className="text-xl font-bold">{t}</h2>
            <p className="mt-2">{d}</p>
          </div>
        ))}
      </section>
    </div>
  );
}
