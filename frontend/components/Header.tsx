import Link from "next/link";

const NAV = [
  { href: "/predict", label: "Predict queue" },
  { href: "/reconstruct", label: "Fill sensor gaps" },
  { href: "/about", label: "About the model" },
];

export default function Header() {
  return (
    <header className="bg-sign text-paint">
      <div className="mx-auto max-w-4xl px-4 py-3">
        <div className="flex flex-wrap items-center justify-between gap-x-6 gap-y-2 rounded-md border-2 border-paint/90 px-4 py-2">
          <Link href="/" className="font-display text-2xl font-bold tracking-tight">TrafficFlowIQ</Link>
          <nav aria-label="Main" className="flex flex-wrap gap-x-5 gap-y-1 text-base">
            {NAV.map((n) => (
              <Link key={n.href} href={n.href} className="underline-offset-4 hover:underline">{n.label}</Link>
            ))}
          </nav>
        </div>
      </div>
    </header>
  );
}
