import { useEffect, useMemo, useState } from "react";
import { motion } from "framer-motion";
import { useI18n } from "../hooks/useI18n";

type TourStep = {
  label: string;
  target: string;
};

type Rect = {
  top: number;
  left: number;
  width: number;
  height: number;
};

const STORAGE_KEY = "circuitsage:onboarded";

export function OnboardingTour() {
  const { t } = useI18n();
  const [active, setActive] = useState(false);
  const [index, setIndex] = useState(0);
  const [rect, setRect] = useState<Rect | null>(null);
  const steps = useMemo<TourStep[]>(
    () => [
      { label: t.tourTryDemo, target: "load-demo" },
      { label: t.tourSnapSchematic, target: "new-session" },
      { label: t.tourPairPhone, target: "recent-sessions" },
      { label: t.tourGenerateReport, target: "load-demo" },
    ],
    [t],
  );

  useEffect(() => {
    setActive(window.localStorage.getItem(STORAGE_KEY) !== "1");
  }, []);

  useEffect(() => {
    if (!active) return;
    const update = () => {
      const target = document.querySelector<HTMLElement>(`[data-tour="${steps[index].target}"]`);
      if (!target) {
        setRect(null);
        return;
      }
      const box = target.getBoundingClientRect();
      setRect({ top: box.top, left: box.left, width: box.width, height: box.height });
    };
    update();
    window.addEventListener("resize", update);
    window.addEventListener("scroll", update, true);
    return () => {
      window.removeEventListener("resize", update);
      window.removeEventListener("scroll", update, true);
    };
  }, [active, index, steps]);

  if (!active) return null;

  function close() {
    window.localStorage.setItem(STORAGE_KEY, "1");
    setActive(false);
  }

  const step = steps[index];
  const isLast = index === steps.length - 1;
  const popoverStyle = rect
    ? {
        top: Math.min(rect.top + rect.height + 16, window.innerHeight - 190),
        left: Math.min(Math.max(rect.left, 18), window.innerWidth - 360),
      }
    : { top: window.innerHeight / 2 - 90, left: window.innerWidth / 2 - 170 };

  return (
    <div className="tour-layer" aria-live="polite">
      {rect && (
        <motion.div
          className="tour-highlight"
          initial={false}
          animate={{
            top: rect.top - 8,
            left: rect.left - 8,
            width: rect.width + 16,
            height: rect.height + 16,
          }}
          transition={{ duration: 0.22 }}
        />
      )}
      <motion.div className="tour-popover" style={popoverStyle} initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }}>
        <span>{index + 1} / {steps.length}</span>
        <p>{step.label}</p>
        <div>
          <button className="ghost" onClick={close}>{t.skipTour}</button>
          <button onClick={() => (isLast ? close() : setIndex(index + 1))}>{isLast ? t.done : t.next}</button>
        </div>
      </motion.div>
    </div>
  );
}
