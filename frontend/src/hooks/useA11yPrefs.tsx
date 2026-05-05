import React, { createContext, useContext, useEffect, useMemo, useState } from "react";

type A11yPrefs = {
  highContrast: boolean;
  largeFont: boolean;
  sound: boolean;
  theme: "dark" | "light";
  setHighContrast: (value: boolean) => void;
  setLargeFont: (value: boolean) => void;
  setSound: (value: boolean) => void;
  setTheme: (value: "dark" | "light") => void;
};

const A11yContext = createContext<A11yPrefs | null>(null);

function stored(key: string, fallback = false) {
  return window.localStorage.getItem(key) === "1" || fallback;
}

function initialTheme(): "dark" | "light" {
  const saved = window.localStorage.getItem("circuitsage:theme");
  if (saved === "dark" || saved === "light") return saved;
  return window.matchMedia("(prefers-color-scheme: light)").matches ? "light" : "dark";
}

export function AccessibilityProvider({ children }: { children: React.ReactNode }) {
  const [highContrast, setHighContrast] = useState(() => stored("circuitsage:contrast"));
  const [largeFont, setLargeFont] = useState(() => stored("circuitsage:large-font"));
  const [sound, setSound] = useState(() => window.localStorage.getItem("circuitsage:sound") !== "0");
  const [theme, setTheme] = useState<"dark" | "light">(initialTheme);

  useEffect(() => {
    document.documentElement.dataset.theme = theme;
    document.documentElement.dataset.contrast = highContrast ? "high" : "normal";
    document.documentElement.dataset.font = largeFont ? "large" : "normal";
    window.localStorage.setItem("circuitsage:theme", theme);
    window.localStorage.setItem("circuitsage:contrast", highContrast ? "1" : "0");
    window.localStorage.setItem("circuitsage:large-font", largeFont ? "1" : "0");
    window.localStorage.setItem("circuitsage:sound", sound ? "1" : "0");
  }, [theme, highContrast, largeFont, sound]);

  const value = useMemo(
    () => ({ highContrast, largeFont, sound, theme, setHighContrast, setLargeFont, setSound, setTheme }),
    [highContrast, largeFont, sound, theme],
  );
  return <A11yContext.Provider value={value}>{children}</A11yContext.Provider>;
}

export function useA11yPrefs() {
  const context = useContext(A11yContext);
  if (!context) throw new Error("useA11yPrefs must be used inside AccessibilityProvider");
  return context;
}
