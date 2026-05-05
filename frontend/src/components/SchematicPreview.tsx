import type { Artifact } from "../lib/types";
import { api } from "../lib/api";

const PART_RE = /\b(TL081|TL072|LM741|LM358|NE5532|MCP6002|2N3904|2N2222|BC547|IRLZ44N|BS170|1N4148|1N4007|1N5819|7805|AMS1117|LM317|NE555|L293D|CD40106|CD4093)\b/gi;

export function SchematicPreview({ artifacts }: { artifacts: Artifact[] }) {
  const netlist = artifacts.find((artifact) => artifact.kind === "netlist");
  const parts = Array.from(new Set((netlist?.text_excerpt?.match(PART_RE) ?? []).map((part) => part.toUpperCase())));
  return (
    <div className="schematic-preview">
      <span>Schematic / netlist</span>
      <pre>{netlist?.text_excerpt || "Upload or recognize a schematic to preview the circuit here."}</pre>
      {parts.length > 0 && (
        <div className="datasheet-badges">
          {parts.map((part) => <a href={api.datasheetUrl(part)} target="_blank" rel="noreferrer" key={part}>{part} datasheet</a>)}
        </div>
      )}
    </div>
  );
}
