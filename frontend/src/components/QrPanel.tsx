import { useI18n } from "../hooks/useI18n";

export function QrPanel({ qr }: { qr: { url: string; data_url: string } }) {
  const { t } = useI18n();
  return (
    <div className="qr-panel">
      <img src={qr.data_url} alt={t.qrBenchAlt} />
      <a href={qr.url} target="_blank" rel="noreferrer">{qr.url}</a>
    </div>
  );
}
