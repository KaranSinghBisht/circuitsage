# CircuitSage Spec

CircuitSage is a local-first AI lab partner for electronics students.

The MVP implements a persistent lab workflow:

1. Pre-Lab: create or seed an inverting op-amp amplifier session.
2. Studio: upload a lab manual, netlist, waveform CSV, notes, and bench images.
3. Bench Mode: open a mobile-friendly session from a QR code, capture images, and enter measurements.
4. Diagnosis: run deterministic circuit tools plus optional Gemma via Ollama.
5. Reflection: generate a post-lab learning report.

The hero demo diagnoses an inverting op-amp amplifier where the simulation expects gain -4.7 but the bench output is stuck near +12 V. CircuitSage asks for the non-inverting input voltage, identifies a floating reference input, and explains the fix.

Safety policy: CircuitSage is for low-voltage educational circuits only. It refuses detailed live debugging for mains, high-voltage, SMPS primary, CRT/flyback, EV battery, microwave, or large capacitor-bank scenarios.

