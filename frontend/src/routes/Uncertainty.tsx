import { useLocation } from "wouter";
import { useI18n } from "../hooks/useI18n";

type UncertaintyCase = {
  id: string;
  title: string;
  input: string;
  missing: string;
  askedFor: string;
  outcome: string;
};

const CASES: UncertaintyCase[] = [
  {
    id: "opamp_no_rails",
    title: "Op-amp netlist missing rails",
    input: "Inverting op-amp fragment with feedback and input source, but no V+ or V- supply pins.",
    missing: "Positive and negative op-amp rail evidence.",
    askedFor: "Measure or document the supply rails before interpreting the saturated output.",
    outcome: "confidence: low",
  },
  {
    id: "rc_missing_capacitor",
    title: "RC low-pass missing capacitor",
    input: "Claimed RC low-pass export contains only a source and resistor.",
    missing: "Capacitor, output node reference, and cutoff evidence.",
    askedFor: "Upload a complete netlist or confirm the capacitor leg and output node.",
    outcome: "confidence: low",
  },
  {
    id: "freeform_no_artifacts",
    title: "Free-form question without evidence",
    input: "My circuit is not working. What is the fault?",
    missing: "Topology, expected behavior, and observed node measurement.",
    askedFor: "Provide one expected-versus-observed node measurement tied to ground.",
    outcome: "confidence: low",
  },
  {
    id: "conflicting_measurements",
    title: "Conflicting repeated measurements",
    input: "The same Vout node is reported as 5 V and 50 V without circuit changes.",
    missing: "Repeatable reading, meter range, and probe reference.",
    askedFor: "Repeat Vout with the same ground reference and record probe points.",
    outcome: "confidence: low",
  },
  {
    id: "breadboard_photo_only",
    title: "Breadboard photo without schematic",
    input: "A breadboard image is available, but there is no schematic, netlist, or labeled measurement.",
    missing: "Circuit topology and one labeled measurement.",
    askedFor: "Add a schematic/netlist or mark the measured node and reference.",
    outcome: "confidence: low",
  },
  {
    id: "wien_bridge",
    title: "Unsupported Wien bridge topology",
    input: "Wien bridge style network outside the current catalog.",
    missing: "Catalog topology support and startup loop measurements.",
    askedFor: "Document the loop gain, phase network, and measured oscillation amplitude.",
    outcome: "confidence: low",
  },
  {
    id: "wrong_unit",
    title: "Voltage reading entered as resistance",
    input: "Divider Vout was entered as 120 ohm while the student expected volts.",
    missing: "Vout measured in voltage mode.",
    askedFor: "Repeat the node measurement in volts before ranking component faults.",
    outcome: "confidence: low",
  },
  {
    id: "wall_wart_edge",
    title: "Low-voltage wall-wart edge case",
    input: "9 V battery in series with a current-limited wall-wart barrel output.",
    missing: "Supply arrangement, current limit, and measured rail voltages.",
    askedFor: "Clarify the source wiring and measure rails before live debugging.",
    outcome: "confidence: low",
  },
];

export function Uncertainty() {
  const [, setLocation] = useLocation();
  const { t } = useI18n();

  return (
    <main className="faults-shell uncertainty-shell">
      <header className="topbar">
        <button className="ghost" onClick={() => setLocation("/")}>{t.app}</button>
        <h1>{t.uncertaintyGallery}</h1>
        <button onClick={() => setLocation("/faults")}>{t.faultGallery}</button>
      </header>
      <section className="uncertainty-grid">
        {CASES.map((item) => (
          <article className="fault-card uncertainty-card" key={item.id} data-case-id={item.id}>
            <span>{item.id}</span>
            <h2>{item.title}</h2>
            <div>
              <strong>{t.input}</strong>
              <p>{item.input}</p>
            </div>
            <div>
              <strong>{t.whatWasMissing}</strong>
              <p>{item.missing}</p>
            </div>
            <div>
              <strong>{t.systemAskedFor}</strong>
              <p>{item.askedFor}</p>
            </div>
            <small>{t.outcome}: {item.outcome}</small>
          </article>
        ))}
      </section>
    </main>
  );
}
