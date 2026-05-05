import { useEffect, useState } from "react";
import { useLocation } from "wouter";
import { api } from "../lib/api";
import { useI18n } from "../hooks/useI18n";

type FaultCard = {
  topology: string;
  id: string;
  name: string;
  why: string;
  requires_measurements: string[];
  verification_test: string;
  fix_recipe: string;
};

export function Faults() {
  const [, setLocation] = useLocation();
  const { t } = useI18n();
  const [faults, setFaults] = useState<FaultCard[]>([]);
  useEffect(() => {
    api.faults().then(setFaults).catch(() => setFaults([]));
  }, []);

  async function tryFault(fault: FaultCard) {
    const session = await api.seedFault(fault.topology, fault.id);
    setLocation(`/studio/${session.id}`);
  }

  const groups = faults.reduce<Record<string, FaultCard[]>>((acc, fault) => {
    acc[fault.topology] = [...(acc[fault.topology] ?? []), fault];
    return acc;
  }, {});

  return (
    <main className="faults-shell">
      <header className="topbar">
        <button className="ghost" onClick={() => setLocation("/")}>{t.app}</button>
        <h1>{t.faultGallery}</h1>
        <button onClick={() => setLocation("/uncertainty")}>{t.uncertainty}</button>
      </header>
      {Object.entries(groups).map(([topology, items]) => (
        <section className="fault-group" key={topology}>
          <h2>{topology.replaceAll("_", " ")}</h2>
          <div className="fault-grid">
            {items.map((fault) => (
              <article className="fault-card" key={fault.id}>
                <span>{fault.id}</span>
                <h3>{fault.name}</h3>
                <div className="fault-scope-thumb" role="img" aria-label={`${fault.name} scope before and after thumbnail`}>
                  <svg viewBox="0 0 160 54" aria-hidden="true"><path d="M0 18 C20 4 34 4 52 18 S88 32 106 18 140 4 160 18" /><path d="M0 38 H160" /></svg>
                </div>
                <p>{fault.why}</p>
                <small>{t.needs}: {fault.requires_measurements.join(", ") || t.generalInspection}</small>
                <small>{fault.verification_test}</small>
                <small>{fault.fix_recipe}</small>
                <button onClick={() => tryFault(fault)}>{t.tryThisFault}</button>
              </article>
            ))}
          </div>
        </section>
      ))}
    </main>
  );
}
