import { Loader2 } from "lucide-react";
import { useI18n } from "../hooks/useI18n";

export function LoadingScreen() {
  const { t } = useI18n();
  return <main className="loading"><Loader2 className="spin" /> {t.loadingCircuitSage}</main>;
}
