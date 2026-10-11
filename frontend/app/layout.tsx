import type { Metadata } from "next";
import "./globals.css";
import Header from "@/components/Header";

export const metadata: Metadata = {
  title: "TrafficFlowIQ: freeway queue prediction",
  description: "Know where the queue will form before it does. A machine-learning case study on freeway congestion.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="" />
        <link href="https://fonts.googleapis.com/css2?family=Overpass:wght@600;700;800&family=Overpass+Mono:wght@500;700&family=Public+Sans:wght@400;600&display=swap" rel="stylesheet" />
      </head>
      <body>
        <Header />
        <main className="mx-auto max-w-4xl px-4 py-8">{children}</main>
        <footer className="mx-auto max-w-4xl px-4 pb-10 text-sm text-ink/70">
          TrafficFlowIQ is a portfolio case study based on the 2026 IEEE Big Data TrafficFlowBench challenge. Not for real traffic operations.
        </footer>
      </body>
    </html>
  );
}
