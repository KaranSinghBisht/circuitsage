import type { Artifact } from "../lib/types";

export function SchematicPreview({ artifacts }: { artifacts: Artifact[] }) {
  const netlist = artifacts.find((artifact) => artifact.kind === "netlist");
  return (
    <div className="schematic-preview">
      <span>Schematic / netlist</span>
      <pre>{netlist?.text_excerpt || "Upload or recognize a schematic to preview the circuit here."}</pre>
    </div>
  );
}
