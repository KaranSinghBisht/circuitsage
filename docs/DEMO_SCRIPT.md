# CircuitSage Demo Script

## 0:00-0:20 Hook

When software fails, it gives you an error. When a circuit fails, it gives you silence.

Show CircuitSage loading the op-amp demo.

## 0:20-0:45 Problem

The LTspice-style simulation expects an inverting amplifier gain of -4.7. The physical circuit output is stuck near +12 V.

## 0:45-1:20 PC Studio

Show the lab manual, netlist, waveform CSV, and seeded measurements. Run diagnosis. CircuitSage computes gain, detects positive saturation, and asks for the non-inverting input voltage.

## 1:20-2:00 Bench Mode

Start Bench Mode, show the QR code, open the mobile route, and enter `V_noninv = 2.8 V DC`.

## 2:00-2:30 Diagnosis

Run diagnosis again. CircuitSage explains that the non-inverting input is not at the 0 V reference and recommends powering off, grounding the pin, and retesting.

## 2:30-3:00 Reflection

Generate the report. Close with: CircuitSage is not replacing teachers. It gives every student a patient lab partner.

