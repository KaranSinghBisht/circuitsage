import { Moon, Sun } from "lucide-react";
import { useA11yPrefs } from "../hooks/useA11yPrefs";
import { useI18n } from "../hooks/useI18n";

export function ThemeToggle() {
  const { theme, setTheme } = useA11yPrefs();
  const { t } = useI18n();
  const next = theme === "dark" ? "light" : "dark";
  return (
    <button
      className="theme-toggle"
      aria-label={t.themeToggle}
      title={theme === "dark" ? t.lightTheme : t.darkTheme}
      onClick={() => setTheme(next)}
    >
      {theme === "dark" ? <Sun size={18} /> : <Moon size={18} />}
    </button>
  );
}
