"use client";
import { useEffect, useRef, useState } from "react";
import { api } from "./api";
import type { Featured, Link } from "./types";

/** Loads links, then dates for the chosen link, then times for the chosen date.
 *  On first load it pre-selects an example moment so the page never looks empty. */
export function useScenario() {
  const [links, setLinks] = useState<Link[]>([]);
  const [source, setSource] = useState("");
  const [linkId, setLinkId] = useState<number | null>(null);
  const [dates, setDates] = useState<string[]>([]);
  const [featured, setFeatured] = useState<Featured[]>([]);
  const [date, setDate] = useState("");
  const [times, setTimes] = useState<string[]>([]);
  const [time, setTime] = useState("");
  const [timesLoading, setTimesLoading] = useState(false);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const pendingTime = useRef("");
  const firstLoad = useRef(true);

  useEffect(() => {
    api.links().then((r) => { setLinks(r.links); setSource(r.data_source); setLinkId(r.links[3]?.link_id ?? r.links[0]?.link_id ?? null); })
      .catch((e) => setError(e.message)).finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    if (linkId === null) return;
    setDate(""); setTime(""); setTimes([]);
    api.datesFor(linkId).then((r) => {
      setDates(r.dates); setFeatured(r.featured);
      if (firstLoad.current && r.featured.length) {
        firstLoad.current = false;
        const f = r.featured[Math.min(1, r.featured.length - 1)];
        pendingTime.current = f.timestamp.slice(11, 16);
        setDate(f.timestamp.slice(0, 10));
      }
    }).catch((e) => setError(e.message));
  }, [linkId]);

  useEffect(() => {
    if (linkId === null || !date) return;
    setTime(""); setTimesLoading(true);
    api.timesFor(linkId, date).then((r) => {
      setTimes(r.times);
      if (pendingTime.current && r.times.includes(pendingTime.current)) setTime(pendingTime.current);
      pendingTime.current = "";
    }).catch((e) => setError(e.message)).finally(() => setTimesLoading(false));
  }, [linkId, date]);

  const pick = (iso: string) => {
    const d = iso.slice(0, 10), t = iso.slice(11, 16);
    if (d === date) { pendingTime.current = ""; setTime(t); }
    else { pendingTime.current = t; setDate(d); }
  };

  return { links, source, linkId, setLinkId, dates, featured, date, setDate, times, time, setTime, timesLoading, error, setError, loading, pick,
    link: links.find((l) => l.link_id === linkId) };
}