from __future__ import annotations

from io import BytesIO, StringIO
from typing import Any

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
from svglib.svglib import svg2rlg

from .schematic_renderer import render_schematic_svg


def generate_report(session: dict[str, Any], diagnosis: dict[str, Any] | None, measurements: list[dict[str, Any]]) -> str:
    diagnosis = diagnosis or {}
    expected = diagnosis.get("expected_behavior", {})
    observed = diagnosis.get("observed_behavior", {})
    likely_faults = diagnosis.get("likely_faults", [])
    top_fault = likely_faults[0]["fault"] if likely_faults else "Evidence is still incomplete"
    measurement_lines = "\n".join(
        f"- {m['label']}: {m['value']} {m['unit']} {m['mode']} ({m.get('context') or m.get('source')})"
        for m in measurements
    ) or "- No bench measurements recorded yet."

    return f"""# Lab Reflection: {session['title']}

## Aim of Experiment
Verify the behavior of an inverting op-amp amplifier and compare simulation with bench measurements.

## Expected Behavior
{expected.get('output', 'For Rin = 10 kOhm and Rf = 47 kOhm, Vout should be an inverted sine wave with gain near -4.7.')}

## Observed Issue
{observed.get('summary', 'The bench behavior did not yet match the expected linear amplifier response.')}

## Measurements Used
{measurement_lines}

## Diagnosis
Most likely issue: **{top_fault}**.

{diagnosis.get('student_explanation', 'CircuitSage needs one more targeted measurement before making a stronger diagnosis.')}

## Corrected Concept
The gain formula only applies when the op-amp has a stable reference and negative feedback. In an inverting amplifier, the non-inverting input must be tied to circuit ground so the inverting node can act as a virtual ground.

## Simulation vs Hardware
The simulation confirms the ideal gain path. The hardware failure points to wiring, reference, supply, or feedback conditions that are not captured by the ideal equation alone.

## Personal Mistake Memory
Before changing resistor values, verify supply rails, common ground, non-inverting input reference, and feedback continuity.

## Viva Questions
1. Why is the gain negative?  
   Because the input is applied to the inverting terminal, causing a 180-degree phase shift.
2. What sets the ideal gain?  
   The resistor ratio, Vout/Vin = -Rf/Rin.
3. What is virtual ground?  
   With negative feedback, the inverting input is held near the grounded non-inverting input without being physically shorted to ground.
4. Why can an op-amp saturate?  
   Missing feedback, floating inputs, rail/reference problems, or excessive input amplitude can drive the output to a supply rail.
5. What should be checked before replacing parts?  
   Supply rails, common ground, input reference, and feedback wiring.
"""


def generate_report_pdf(
    session: dict[str, Any],
    diagnosis: dict[str, Any] | None,
    measurements: list[dict[str, Any]],
    parsed_netlist: dict[str, Any] | None = None,
    artifacts: list[dict[str, Any]] | None = None,
) -> bytes:
    diagnosis = diagnosis or {}
    artifacts = artifacts or []
    expected = diagnosis.get("expected_behavior", {})
    observed = diagnosis.get("observed_behavior", {})
    top_fault = (diagnosis.get("likely_faults") or [{"fault": "Evidence incomplete", "why": ""}])[0]
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, title=f"CircuitSage Report - {session['title']}")
    styles = getSampleStyleSheet()
    story: list[Any] = []

    story.extend([
        Paragraph("CircuitSage Lab Report", styles["Title"]),
        Paragraph(session["title"], styles["Heading2"]),
        Paragraph(f"Student level: {session.get('student_level', 'unknown')}", styles["Normal"]),
        Paragraph(f"Experiment: {session.get('experiment_type', 'unknown').replace('_', ' ')}", styles["Normal"]),
        Spacer(1, 18),
        Paragraph("Aim", styles["Heading2"]),
        Paragraph("Compare the expected circuit behavior with bench evidence and record the next debugging step.", styles["BodyText"]),
        Paragraph("Expected Behavior", styles["Heading2"]),
        Paragraph(str(expected.get("output") or expected.get("summary") or expected), styles["BodyText"]),
        Paragraph("Observed Behavior", styles["Heading2"]),
        Paragraph(str(observed.get("summary", "No observed behavior recorded.")), styles["BodyText"]),
    ])

    rows = [["Label", "Value", "Mode", "Context"]]
    rows.extend([[m["label"], f"{m['value']} {m['unit']}", m["mode"], m.get("context", "")] for m in measurements])
    table = Table(rows, repeatRows=1)
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#dfeee4")),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#809086")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ]))
    story.extend([Paragraph("Measurements", styles["Heading2"]), table, PageBreak()])

    story.extend([
        Paragraph("Diagnosis", styles["Heading2"]),
        Paragraph(f"Top fault: {top_fault.get('fault') or top_fault.get('name')}", styles["Heading3"]),
        Paragraph(str(top_fault.get("why", "")), styles["BodyText"]),
        Paragraph(str(diagnosis.get("student_explanation", "")), styles["BodyText"]),
        Paragraph("Verification Test", styles["Heading2"]),
        Paragraph(str(top_fault.get("verification_test") or diagnosis.get("next_measurement", {}).get("instruction", "")), styles["BodyText"]),
        Paragraph("Corrected Concept", styles["Heading2"]),
        Paragraph("The equation only applies after the circuit reference, rails, and feedback path match the schematic.", styles["BodyText"]),
        Spacer(1, 14),
        Paragraph("Schematic", styles["Heading2"]),
    ])
    drawing = svg2rlg(StringIO(render_schematic_svg(parsed_netlist)))
    if drawing:
        drawing.width = 420
        drawing.height = 210
        story.append(drawing)

    thumbs = [artifact["filename"] for artifact in artifacts if artifact["kind"] in {"oscilloscope", "breadboard", "image"}]
    story.extend([
        PageBreak(),
        Paragraph("Simulation vs Hardware", styles["Heading2"]),
        Paragraph("Use the same input amplitude, reference node, and probe label in simulation and on the bench.", styles["BodyText"]),
        Paragraph("Scope / Bench Thumbnails", styles["Heading2"]),
        Paragraph(", ".join(thumbs) if thumbs else "No image thumbnails attached.", styles["BodyText"]),
        Paragraph("Viva Questions", styles["Heading2"]),
        Paragraph("1. What is the expected transfer function? 2. Which node proves the suspected fault? 3. How would the waveform change after the fix?", styles["BodyText"]),
    ])

    doc.build(story)
    return buffer.getvalue()
