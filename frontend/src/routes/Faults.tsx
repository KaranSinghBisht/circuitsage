import { useEffect, useState } from "react";
import { useLocation } from "wouter";
import { api } from "../lib/api";

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
      <header className="topbar"><button className="ghost" onClick={() => setLocation("/")}>CircuitSage</button><h1>Fault Gallery</h1></header>
      {Object.entries(groups).map(([topology, items]) => (
        <section className="fault-group" key={topology}>
          <h2>{topology.replaceAll("_", " ")}</h2>
          <div className="fault-grid">
            {items.map((fault) => (
              <article className="fault-card" key={fault.id}>
                <span>{fault.id}</span>
                <h3>{fault.name}</h3>
                <p>{fault.why}</p>
                <small>{fault.verification_test}</small>
                <button onClick={() => tryFault(fault)}>Try this fault</button>
              </article>
            ))}
          </div>
        </section>
      ))}
    </main>
  );
}
