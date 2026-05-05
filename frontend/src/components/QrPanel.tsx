export function QrPanel({ qr }: { qr: { url: string; data_url: string } }) {
  return (
    <div className="qr-panel">
      <img src={qr.data_url} alt="QR code for Bench Mode handoff" />
      <a href={qr.url} target="_blank" rel="noreferrer">{qr.url}</a>
    </div>
  );
}
