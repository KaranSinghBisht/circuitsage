import { useA11yPrefs } from "../hooks/useA11yPrefs";
import { type Locale, useI18n } from "../hooks/useI18n";

const locales: Array<{ id: Locale; label: string }> = [
  { id: "en", label: "EN" },
  { id: "hi", label: "HI" },
  { id: "es", label: "ES" },
  { id: "pt", label: "PT" },
];

export function LanguageSwitcher() {
  const { locale, setLocale, t } = useI18n();
  const { highContrast, largeFont, sound, setHighContrast, setLargeFont, setSound } = useA11yPrefs();
  return (
    <div className="accessibility-bar" aria-label="Accessibility settings">
      <label>
        <span>{t.language}</span>
        <select value={locale} onChange={(event) => setLocale(event.target.value as Locale)}>
          {locales.map((item) => <option value={item.id} key={item.id}>{item.label}</option>)}
        </select>
      </label>
      <label><input type="checkbox" checked={highContrast} onChange={(event) => setHighContrast(event.target.checked)} /> {t.highContrast}</label>
      <label><input type="checkbox" checked={largeFont} onChange={(event) => setLargeFont(event.target.checked)} /> {t.largeFont}</label>
      <label><input type="checkbox" checked={sound} onChange={(event) => setSound(event.target.checked)} /> {t.sound}</label>
    </div>
  );
}
