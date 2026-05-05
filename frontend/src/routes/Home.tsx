import { useEffect, useState } from "react";
import { useLocation } from "wouter";
import { Bot, CircuitBoard, Loader2, Plus, Sparkles } from "lucide-react";
import { api } from "../lib/api";
import type { LabSession } from "../lib/types";
import { LanguageSwitcher } from "../components/LanguageSwitcher";
import { useI18n } from "../hooks/useI18n";

const DEMO_TILES = [
  { slug: "op-amp", title: "Inverting Op-Amp", detail: "saturated output, floating reference input" },
  { slug: "rc-lowpass", title: "RC Low-Pass", detail: "unexpected attenuation below cutoff" },
  { slug: "voltage-divider", title: "Voltage Divider", detail: "loaded output pulled below expectation" },
  { slug: "bjt-common-emitter", title: "BJT Common Emitter", detail: "collector biased into saturation" },
  { slug: "op-amp-noninverting", title: "Non-Inverting Op-Amp", detail: "unity gain instead of configured gain" },
];

export function Home() {
  const [, setLocation] = useLocation();
  const { t } = useI18n();
  const [sessions, setSessions] = useState<LabSession[]>([]);
  const [loading, setLoading] = useState(false);
  const [title, setTitle] = useState("Inverting Op-Amp Amplifier");

  useEffect(() => {
    api.sessions().then(setSessions).catch(console.error);
  }, []);

  async function seed(slug = "op-amp") {
    setLoading(true);
    try {
      const session = await api.seedDemo(slug);
      setLocation(`/studio/${session.id}`);
    } finally {
      setLoading(false);
    }
  }

  async function create() {
    setLoading(true);
    try {
      const session = await api.create(title);
      setLocation(`/studio/${session.id}`);
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="home-shell">
      <LanguageSwitcher />
      <section className="hero-band">
        <div>
          <div className="eyebrow"><CircuitBoard size={16} /> {t.app}</div>
          <h1>{t.tagline}</h1>
          <p>A local-first Gemma lab partner that follows students from simulation to oscilloscope and asks for the next measurement.</p>
        </div>
        <div className="hero-actions">
          <button onClick={() => setLocation("/companion")}><Bot size={18} /> {t.openCompanion}</button>
          <button className="primary" onClick={() => seed("op-amp")} disabled={loading}>
            {loading ? <Loader2 className="spin" size={18} /> : <Sparkles size={18} />}
            {t.loadDemo}
          </button>
          <div className="create-row">
            <input value={title} onChange={(event) => setTitle(event.target.value)} aria-label="Session title" />
            <button onClick={create} disabled={loading}><Plus size={18} /> {t.newSession}</button>
          </div>
        </div>
      </section>

      <section className="demo-grid">
        {DEMO_TILES.map((demo) => (
          <button className="demo-tile" key={demo.slug} onClick={() => seed(demo.slug)} disabled={loading}>
            <span>{t.demo}</span>
            <strong>{demo.title}</strong>
            <small>{demo.detail}</small>
          </button>
        ))}
      </section>

      <section className="session-grid">
        {sessions.map((session) => (
          <button className="session-tile" key={session.id} onClick={() => setLocation(`/studio/${session.id}`)}>
            <span>{session.status}</span>
            <strong>{session.title}</strong>
            <small>{session.student_level}</small>
          </button>
        ))}
      </section>
    </main>
  );
}
