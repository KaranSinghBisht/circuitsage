import { useEffect, useState } from "react";
import { motion } from "framer-motion";

const SLIDE_MS = 2750;

const BEATS = [
  {
    kicker: "0:00",
    title: "Software has stack traces. Circuits do not.",
    detail: "A silent bench failure starts the story.",
    scene: "scope",
  },
  {
    kicker: "0:18",
    title: "Studio gathers the evidence.",
    detail: "Manual, netlist, waveform, measurements, and tool calls stay in one session.",
    scene: "studio",
  },
  {
    kicker: "0:42",
    title: "Bench Mode pairs by QR.",
    detail: "The same session follows the student from laptop to phone.",
    scene: "phone",
  },
  {
    kicker: "1:05",
    title: "Airplane mode still answers.",
    detail: "The on-device path is the Digital Equity proof point.",
    scene: "airplane",
  },
  {
    kicker: "1:35",
    title: "Ground the reference input.",
    detail: "The physical fix turns diagnosis into learning.",
    scene: "fix",
  },
  {
    kicker: "2:10",
    title: "Generate the lab report.",
    detail: "Evidence, safety, measurements, and diagnosis become a PDF.",
    scene: "report",
  },
  {
    kicker: "2:35",
    title: "Instructors see patterns.",
    detail: "Educator view surfaces repeated faults and stalled measurements.",
    scene: "educator",
  },
  {
    kicker: "2:55",
    title: "CircuitSage.",
    detail: "Stack traces for circuits.",
    scene: "close",
  },
] as const;

export function PressKit() {
  const [index, setIndex] = useState(0);
  useEffect(() => {
    const timer = window.setInterval(() => setIndex((current) => (current + 1) % BEATS.length), SLIDE_MS);
    return () => window.clearInterval(timer);
  }, []);
  const beat = BEATS[index];
  return (
    <main className="press-shell">
      <motion.section
        key={beat.title}
        className="press-stage"
        initial={{ opacity: 0, y: 18 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.45 }}
      >
        <div className="press-copy">
          <span>{beat.kicker}</span>
          <h1>{beat.title}</h1>
          <p>{beat.detail}</p>
        </div>
        <PressScene scene={beat.scene} />
      </motion.section>
      <div className="press-progress" aria-hidden="true">
        {BEATS.map((item, itemIndex) => <i className={itemIndex === index ? "active" : ""} key={item.title} />)}
      </div>
    </main>
  );
}

function PressScene({ scene }: { scene: (typeof BEATS)[number]["scene"] }) {
  return (
    <svg className={`press-scene ${scene}`} viewBox="0 0 760 460" role="img" aria-label={scene}>
      <rect className="screen" x="40" y="38" width="680" height="384" rx="6" />
      {scene === "scope" && (
        <>
          <path className="grid" d="M86 116 H676 M86 192 H676 M86 268 H676 M86 344 H676 M160 78 V382 M304 78 V382 M448 78 V382 M592 78 V382" />
          <path className="warn" d="M86 116 H676" />
          <circle className="node bad" cx="630" cy="116" r="12" />
        </>
      )}
      {scene === "studio" && (
        <>
          <rect className="panel-a" x="86" y="86" width="150" height="272" rx="4" />
          <rect className="panel-b" x="260" y="86" width="220" height="272" rx="4" />
          <rect className="panel-c" x="504" y="86" width="150" height="272" rx="4" />
          <path className="trace" d="M286 234 C330 170 374 300 424 218" />
        </>
      )}
      {scene === "phone" && (
        <>
          <rect className="phone" x="280" y="74" width="200" height="312" rx="28" />
          <rect className="qr" x="324" y="132" width="112" height="112" rx="2" />
          <path className="qr-lines" d="M342 150 H378 V186 H342 Z M392 150 H418 V176 H392 Z M350 214 H430 M350 232 H394 M410 204 V244" />
        </>
      )}
      {scene === "airplane" && (
        <>
          <rect className="phone" x="276" y="70" width="208" height="320" rx="30" />
          <path className="plane" d="M382 132 L434 162 L414 174 L388 160 L370 208 L354 198 L362 152 L326 132 L338 120 Z" />
          <rect className="answer" x="314" y="246" width="132" height="54" rx="8" />
        </>
      )}
      {scene === "fix" && (
        <>
          <path className="wire" d="M180 286 C266 220 350 352 438 226" />
          <circle className="node" cx="180" cy="286" r="18" />
          <circle className="node good" cx="438" cy="226" r="18" />
          <path className="trace good" d="M118 142 C184 86 236 200 300 142 S424 86 492 142 612 200 662 142" />
        </>
      )}
      {scene === "report" && (
        <>
          <rect className="paper" x="250" y="76" width="260" height="316" rx="4" />
          <path className="paper-lines" d="M286 128 H474 M286 166 H452 M286 204 H474 M286 242 H430 M286 280 H460 M286 318 H414" />
        </>
      )}
      {scene === "educator" && (
        <>
          <rect className="metric-one" x="112" y="104" width="146" height="96" rx="4" />
          <rect className="metric-two" x="306" y="104" width="146" height="96" rx="4" />
          <rect className="metric-three" x="500" y="104" width="146" height="96" rx="4" />
          <path className="bars" d="M132 334 V286 M176 334 V246 M220 334 V270 M330 334 V220 M374 334 V266 M418 334 V236 M528 334 V252 M572 334 V288 M616 334 V230" />
        </>
      )}
      {scene === "close" && (
        <>
          <path className="mark" d="M250 232 C300 144 460 144 510 232 C460 320 300 320 250 232 Z" />
          <circle className="node good" cx="380" cy="232" r="38" />
        </>
      )}
    </svg>
  );
}
