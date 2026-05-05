from __future__ import annotations

from html import escape
from typing import Any


def render_schematic_svg(parsed_netlist: dict[str, Any] | None) -> str:
    parsed_netlist = parsed_netlist or {}
    topology = parsed_netlist.get("detected_topology", "unknown")
    computed = parsed_netlist.get("computed", {})
    title = topology.replace("_", " ").title()
    gain = computed.get("gain")
    subtitle = f"Gain {gain}" if gain is not None else "CircuitSage inferred schematic"

    if topology in {"op_amp_inverting", "op_amp_noninverting"}:
        return f"""<svg xmlns="http://www.w3.org/2000/svg" width="640" height="320" viewBox="0 0 640 320">
  <rect width="640" height="320" fill="#ffffff"/>
  <text x="28" y="36" font-size="24" font-family="Helvetica" fill="#111">{escape(title)}</text>
  <text x="28" y="62" font-size="14" font-family="Helvetica" fill="#555">{escape(str(subtitle))}</text>
  <line x1="70" y1="180" x2="190" y2="180" stroke="#111" stroke-width="3"/>
  <path d="M190 170 h22 l10 -16 l20 32 l20 -32 l20 32 l20 -32 l10 16 h48" fill="none" stroke="#111" stroke-width="3"/>
  <text x="210" y="146" font-size="16" font-family="Helvetica">Rin</text>
  <line x1="360" y1="180" x2="430" y2="180" stroke="#111" stroke-width="3"/>
  <polygon points="430,112 430,248 555,180" fill="#f2f7f4" stroke="#111" stroke-width="3"/>
  <text x="447" y="162" font-size="20" font-family="Helvetica">-</text>
  <text x="447" y="214" font-size="20" font-family="Helvetica">+</text>
  <line x1="555" y1="180" x2="600" y2="180" stroke="#111" stroke-width="3"/>
  <line x1="360" y1="180" x2="360" y2="88" stroke="#111" stroke-width="3"/>
  <path d="M360 88 h34 l10 -16 l20 32 l20 -32 l20 32 l20 -32 l10 16 h60" fill="none" stroke="#111" stroke-width="3"/>
  <line x1="554" y1="88" x2="554" y2="180" stroke="#111" stroke-width="3"/>
  <text x="430" y="66" font-size="16" font-family="Helvetica">Rf</text>
  <line x1="430" y1="218" x2="390" y2="218" stroke="#111" stroke-width="3"/>
  <line x1="390" y1="218" x2="390" y2="260" stroke="#111" stroke-width="3"/>
  <line x1="368" y1="260" x2="412" y2="260" stroke="#111" stroke-width="3"/>
  <line x1="376" y1="272" x2="404" y2="272" stroke="#111" stroke-width="3"/>
  <line x1="384" y1="284" x2="396" y2="284" stroke="#111" stroke-width="3"/>
  <text x="44" y="174" font-size="16" font-family="Helvetica">Vin</text>
  <text x="565" y="174" font-size="16" font-family="Helvetica">Vout</text>
</svg>"""

    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="640" height="260" viewBox="0 0 640 260">
  <rect width="640" height="260" fill="#ffffff"/>
  <text x="28" y="38" font-size="24" font-family="Helvetica" fill="#111">{escape(title)}</text>
  <text x="28" y="66" font-size="14" font-family="Helvetica" fill="#555">Parsed nodes: {len(parsed_netlist.get("nodes", []))}</text>
  <line x1="70" y1="140" x2="570" y2="140" stroke="#111" stroke-width="3"/>
  <circle cx="120" cy="140" r="18" fill="#f2f7f4" stroke="#111" stroke-width="3"/>
  <rect x="210" y="118" width="90" height="44" fill="#f2f7f4" stroke="#111" stroke-width="3"/>
  <path d="M380 118 v44 M405 118 v44" stroke="#111" stroke-width="3"/>
  <circle cx="520" cy="140" r="18" fill="#f2f7f4" stroke="#111" stroke-width="3"/>
</svg>"""
