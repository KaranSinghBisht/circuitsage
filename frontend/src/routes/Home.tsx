import { useEffect, useState } from "react";
import { useLocation } from "wouter";
import { Bot, CircuitBoard, Loader2, Plus, Sparkles } from "lucide-react";
import { api } from "../lib/api";
import type { LabSession } from "../lib/types";
import { LanguageSwitcher } from "../components/LanguageSwitcher";
import { useI18n } from "../hooks/useI18n";

const DEMO_TILES = [
  { slug: "op-amp", titleKey: "demoOpAmpTitle", detailKey: "demoOpAmpDetail" },
  { slug: "rc-lowpass", titleKey: "demoRcTitle", detailKey: "demoRcDetail" },
  { slug: "voltage-divider", titleKey: "demoDividerTitle", detailKey: "demoDividerDetail" },
  { slug: "bjt-common-emitter", titleKey: "demoBjtTitle", detailKey: "demoBjtDetail" },
  { slug: "op-amp-noninverting", titleKey: "demoNonInvTitle", detailKey: "demoNonInvDetail" },
  { slug: "active-highpass", titleKey: "demoHighpassTitle", detailKey: "demoHighpassDetail" },
  { slug: "integrator", titleKey: "demoIntegratorTitle", detailKey: "demoIntegratorDetail" },
  { slug: "schmitt-trigger", titleKey: "demoSchmittTitle", detailKey: "demoSchmittDetail" },
  { slug: "timer-555-astable", titleKey: "demoTimerTitle", detailKey: "demoTimerDetail" },
  { slug: "nmos-low-side", titleKey: "demoNmosTitle", detailKey: "demoNmosDetail" },
  { slug: "instrumentation-amplifier", titleKey: "demoInstrumentationTitle", detailKey: "demoInstrumentationDetail" },
] as const;

export function Home() {
  const [, setLocation] = useLocation();
  const { t } = useI18n();
  const [sessions, setSessions] = useState<LabSession[]>([]);
  const [loading, setLoading] = useState(false);
  const [title, setTitle] = useState(t.defaultSessionTitle);

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
          <p>{t.homePitch}</p>
        </div>
        <div className="hero-actions">
          <button onClick={() => setLocation("/companion")}><Bot size={18} /> {t.openCompanion}</button>
          <button className="primary" onClick={() => seed("op-amp")} disabled={loading}>
            {loading ? <Loader2 className="spin" size={18} /> : <Sparkles size={18} />}
            {t.loadDemo}
          </button>
          <div className="create-row">
            <input value={title} onChange={(event) => setTitle(event.target.value)} aria-label={t.sessionTitle} />
            <button onClick={create} disabled={loading}><Plus size={18} /> {t.newSession}</button>
          </div>
        </div>
      </section>

      <section className="demo-grid">
        {DEMO_TILES.map((demo) => (
          <button className="demo-tile" key={demo.slug} onClick={() => seed(demo.slug)} disabled={loading}>
            <span>{t.demo}</span>
            <strong>{t[demo.titleKey]}</strong>
            <small>{t[demo.detailKey]}</small>
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
