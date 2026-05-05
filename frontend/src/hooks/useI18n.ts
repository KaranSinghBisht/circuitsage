import { useMemo, useState } from "react";
import { en } from "../i18n/en";
import { es } from "../i18n/es";
import { hi } from "../i18n/hi";
import { pt } from "../i18n/pt";

const dictionaries = { en, hi, es, pt };
export type Locale = keyof typeof dictionaries;

function defaultLocale(): Locale {
  const saved = window.localStorage.getItem("circuitsage:locale") as Locale | null;
  if (saved && saved in dictionaries) return saved;
  const lang = navigator.language.slice(0, 2) as Locale;
  return lang in dictionaries ? lang : "en";
}

export function useI18n() {
  const [locale, setLocaleState] = useState<Locale>(defaultLocale);
  const t = useMemo(() => dictionaries[locale], [locale]);
  function setLocale(next: Locale) {
    window.localStorage.setItem("circuitsage:locale", next);
    setLocaleState(next);
  }
  return { locale, setLocale, t };
}
