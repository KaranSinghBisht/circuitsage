from __future__ import annotations

from typing import Any


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

