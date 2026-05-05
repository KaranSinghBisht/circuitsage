import type React from "react";

export function PanelTitle({ icon, title, detail }: { icon: React.ReactNode; title: string; detail: string }) {
  return (
    <div className="panel-title">
      {icon}
      <div>
        <h2>{title}</h2>
        <p>{detail}</p>
      </div>
    </div>
  );
}
