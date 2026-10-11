"use client";
import { useEffect, useState } from "react";
import { api } from "./api";
import type { Featured, Link } from "./types";

/** Loads links, then dates for the chosen link, then times for the chosen date. */
export function useScenario() {
  const [links, setLinks] = useState<Link[]>([]);
  const [source, setSource] = useState("");
  const [linkId, setLinkId] = useState<number | null>(null);
  const [dates, setDates] = useState<string[]>([]);
  const [featured, setFeatured] = useState<Featured[]>([]);
  const [date, setDate] = useState("");
  const [times, setTimes] = useState<string[]>([]);
  const [time, setTime] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.links().then((r) => { setLinks(r.links); setSource(r.data_source); setLinkId(r.links[3]?.link_id ?? r.links[0]?.link_id ?? null); })
      .catch((e) => setError(e.message)).finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    if (linkId === null) return;
    setDate(""); setTime(""); setTimes([]);
    api.datesFor(linkId).then((r) => { setDates(r.dates); setFeatured(r.featured); }).catch((e) => setError(e.message));
  }, [linkId]);

  useEffect(() => {
    if (linkId === null || !date) return;
    setTime("");
    api.timesFor(linkId, date).then((r) => { setTimes(r.times); }).catch((e) => setError(e.message));
  }, [linkId, date]);

  const pick = (iso: string) => { setDate(iso.slice(0, 10)); setTimeout(() => setTime(iso.slice(11, 16)), 400); };
  return { links, source, linkId, setLinkId, dates, featured, date, setDate, times, time, setTime, error, setError, loading, pick,
    link: links.find((l) => l.link_id === linkId) };
}
