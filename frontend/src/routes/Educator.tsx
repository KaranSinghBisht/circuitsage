import { useEffect, useState } from "react";
import { useLocation } from "wouter";
import { api } from "../lib/api";
import { useI18n } from "../hooks/useI18n";

type EducatorOverview = {
  total_sessions: number;
  average_time_to_resolution_s: number | null;
  safety_refusals: number;
  unfinished_sessions: number;
  common_faults: Array<{ topology: string; fault: string; count: number }>;
  stalled_measurements: Array<{ label: string; count: number }>;
};

export function Educator() {
  const [, setLocation] = useLocation();
  const { t } = useI18n();
  const [overview, setOverview] = useState<EducatorOverview | null>(null);
  useEffect(() => {
    api.educatorOverview().then(setOverview).catch(() => setOverview(null));
  }, []);
  return (
    <main className="educator-shell">
      <header className="topbar"><button className="ghost" onClick={() => setLocation("/")}>{t.app}</button><h1>{t.educatorDashboard}</h1></header>
      <section className="educator-grid">
        <Metric label={t.sessions} value={overview?.total_sessions ?? 0} />
        <Metric label={t.safetyRefusals} value={overview?.safety_refusals ?? 0} />
        <Metric label={t.unfinished} value={overview?.unfinished_sessions ?? 0} />
        <Metric label={t.avgResolution} value={Math.round(overview?.average_time_to_resolution_s ?? 0)} suffix="s" />
      </section>
      <section className="panel"><h2>{t.commonFaults}</h2>{(overview?.common_faults ?? []).map((row) => <p key={`${row.topology}-${row.fault}`}>{row.topology}: {row.fault} ({row.count})</p>)}</section>
      <section className="panel"><h2>{t.stalledMeasurements}</h2>{(overview?.stalled_measurements ?? []).map((row) => <p key={row.label}>{row.label}: {row.count}</p>)}</section>
    </main>
  );
}

function Metric({ label, value, suffix = "" }: { label: string; value: number; suffix?: string }) {
  return <div className="metric"><span>{label}</span><strong>{value}{suffix}</strong></div>;
}
