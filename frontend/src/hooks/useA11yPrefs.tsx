import React, { createContext, useContext, useEffect, useMemo, useState } from "react";

type A11yPrefs = {
  highContrast: boolean;
  largeFont: boolean;
  sound: boolean;
  setHighContrast: (value: boolean) => void;
  setLargeFont: (value: boolean) => void;
  setSound: (value: boolean) => void;
};

const A11yContext = createContext<A11yPrefs | null>(null);

function stored(key: string, fallback = false) {
  return window.localStorage.getItem(key) === "1" || fallback;
}

export function AccessibilityProvider({ children }: { children: React.ReactNode }) {
  const [highContrast, setHighContrast] = useState(() => stored("circuitsage:contrast"));
  const [largeFont, setLargeFont] = useState(() => stored("circuitsage:large-font"));
  const [sound, setSound] = useState(() => window.localStorage.getItem("circuitsage:sound") !== "0");

  useEffect(() => {
    document.documentElement.dataset.contrast = highContrast ? "high" : "normal";
    document.documentElement.dataset.font = largeFont ? "large" : "normal";
    window.localStorage.setItem("circuitsage:contrast", highContrast ? "1" : "0");
    window.localStorage.setItem("circuitsage:large-font", largeFont ? "1" : "0");
    window.localStorage.setItem("circuitsage:sound", sound ? "1" : "0");
  }, [highContrast, largeFont, sound]);

  const value = useMemo(
    () => ({ highContrast, largeFont, sound, setHighContrast, setLargeFont, setSound }),
    [highContrast, largeFont, sound],
  );
  return <A11yContext.Provider value={value}>{children}</A11yContext.Provider>;
}

export function useA11yPrefs() {
  const context = useContext(A11yContext);
  if (!context) throw new Error("useA11yPrefs must be used inside AccessibilityProvider");
  return context;
}
