# N-MOSFET Low-Side Switch Lab Notes

## Scope
- Topology: nmos_low_side_switch.
- Circuit family: N-channel MOSFET used as a low-side switch.
- Typical load: LED string, relay coil, motor, lamp, or resistor.
- MOSFET source is normally tied to ground.
- Load sits between supply and drain.
- Gate drive controls conduction.
- Relevant catalog fault: gate_not_driven.
- Relevant catalog fault: source_not_grounded.
- Relevant catalog fault: flyback_missing.
- These notes assume low-voltage classroom loads.
- Inductive loads require extra safety care even at low voltage.
- Always know load current before choosing a MOSFET.

## Core Theory
- An N-MOSFET turns on when Vgs exceeds its needed gate drive.
- Vgs means gate voltage minus source voltage.
- In a low-side switch, source should be near ground when wired correctly.
- If source is grounded, gate voltage is easy to interpret.
- A microcontroller output of 5 V gives about Vgs = 5 V if source is grounded.
- A 3.3 V output gives about Vgs = 3.3 V if source is grounded.
- Logic-level MOSFETs are intended to conduct well at low Vgs.
- Threshold voltage is not the same as full-on gate voltage.
- Vth is where the device barely starts conducting.
- Rds(on) is specified at a particular Vgs.
- Use Rds(on) at the actual gate drive voltage.
- Drain current causes voltage drop across Rds(on).
- Power dissipation is approximately I^2*Rds(on).
- Heat rises with current and on-resistance.
- The body diode is inherent in MOSFET structure.
- In a low-side NMOS, body diode orientation does not replace correct switching.
- Gate is insulated and has high DC impedance.
- A floating gate can turn on unpredictably.
- A gate pulldown resistor defines off state.
- A series gate resistor can reduce ringing and microcontroller stress.
- A flyback diode protects the MOSFET from inductive voltage spikes.
- A motor or relay stores energy in its magnetic field.
- When current is interrupted, the inductor forces voltage to rise.
- The flyback diode gives that current a safe path.
- Without flyback, drain voltage can exceed MOSFET rating.
- PWM switching adds dynamic losses.
- Slow gate edges increase switching loss.
- Breadboard contacts can limit current.
- Ground routing matters for high load current.

## Formula Reference
- Vgs = Vgate - Vsource.
- Vds = Vdrain - Vsource.
- On-state dissipation: P = Iload^2 * Rds(on).
- Resistive load current: I = Vsupply / Rload approximately when MOSFET is on.
- LED load current needs current-limiting resistor.
- Gate charge determines how fast the driver can switch.
- Switching time rises with gate charge and weak driver current.
- Pulldown resistor current is Vgate/Rpulldown when gate is high.
- A 100 k pulldown is common for logic gates.
- A 10 k pulldown is stronger but wastes more drive current.
- Flyback diode reverse voltage rating must exceed supply.
- Flyback diode forward current rating must handle coil current.
- Drain voltage spike without diode can be much larger than supply.
- Logic high voltage must be compared with MOSFET Rds(on) spec.
- A MOSFET rated at Vgs = 10 V may be poor at 3.3 V.
- Vth can be 2 V while Rds(on) is still high at 3.3 V.
- If source rises due to wiring resistance, Vgs falls.
- If source is not grounded, gate drive may be ineffective.
- If drain and source are swapped, conduction may occur through body diode.
- If load current is too high, MOSFET heats even when correctly driven.

## Expected Behavior
- With gate low, load should be off.
- With gate high, load should be on.
- With gate high, source should remain near ground.
- With gate high, drain voltage should drop near ground for a low-side switch.
- With gate low, drain voltage should rise toward load supply through the load.
- Gate voltage should be a clean logic level.
- Vgs should match the intended drive.
- Vds(on) should be small when the MOSFET is fully on.
- Load current should match supply and load design.
- MOSFET should not overheat at expected current.
- Inductive load should not create large drain spikes.
- Flyback diode should be reverse-biased during normal on state.
- Flyback diode should conduct when the switch turns off.
- PWM output should show clean drain transitions.
- A slow drain fall can indicate weak gate drive.
- A slow drain rise can indicate inductive load or snubber behavior.
- A load that is dim or weak can indicate high Rds(on).
- A load that never turns off can indicate floating gate or body-diode path.
- A load that never turns on can indicate gate_not_driven or source_not_grounded.
- A device that fails after switching a relay likely lacked flyback protection.

## Common Fault: gate_not_driven
- Fault id: gate_not_driven.
- Meaning: gate voltage is missing, too low, floating, or not referenced to source.
- Symptom: load stays off or only partially turns on.
- Symptom: MOSFET heats because it is in linear region.
- Symptom: gate reads 0 V when control signal should be high.
- Symptom: gate waveform exists at microcontroller pin but not at MOSFET gate.
- A jumper may be in the wrong row.
- A resistor may be connected to drain instead of gate.
- A pulldown may be present but no drive path exists.
- A 3.3 V drive may be insufficient for a non-logic MOSFET.
- Measure gate-to-ground first.
- Measure source-to-ground next.
- Compute Vgs from those readings.
- If source is at ground and gate is high enough, gate drive is probably present.
- If gate is high but load weak, inspect MOSFET selection and current.
- If gate floats, add or repair pulldown.
- If gate is stuck low, trace the control signal.
- If gate has PWM, verify duty cycle and amplitude.
- After repair, Vgs should match control high level.

## Common Fault: source_not_grounded
- Fault id: source_not_grounded.
- Meaning: source is not tied to circuit ground.
- Symptom: Vgs is smaller than expected or undefined.
- Symptom: load may not turn on despite gate voltage measured to ground.
- Symptom: source node moves with load current.
- Low-side switch source must return to the same ground as the driver.
- A missing ground connection breaks the gate reference.
- A breadboard ground rail split can isolate the source.
- A high-current ground path can lift source voltage.
- Measure source voltage relative to driver ground.
- If source is not near 0 V when on, inspect ground path.
- Measure Vgs directly between gate and source.
- Do not rely only on gate-to-ground measurement.
- Check continuity from source pin to ground with power off.
- Check MOSFET pinout; source and drain can be swapped.
- After repair, source should stay near ground under load.
- After repair, drain should pull low when gate is high.

## Common Fault: flyback_missing
- Fault id: flyback_missing.
- Meaning: inductive load lacks a flyback diode or clamp path.
- Symptom: MOSFET resets, overheats, or fails after switching coil.
- Symptom: drain voltage spikes high when turning off.
- Symptom: microcontroller resets due to supply disturbance.
- Relay coils and motors are inductive loads.
- Inductor current cannot stop instantly.
- The diode should be reverse-biased during normal operation.
- For a relay to positive supply, diode cathode usually goes to supply.
- Diode anode usually goes to MOSFET drain/load low side.
- Wrong diode orientation shorts supply when MOSFET turns on.
- Missing diode may not show in slow DC tests.
- Use a scope rated for the expected spike.
- Prefer safe low-voltage demonstration loads.
- Inspect diode placement before repetitive switching.
- After repair, turn-off spike should be clamped.
- After repair, resets and MOSFET stress should reduce.

## Measurement Plan
- Step 1: identify MOSFET part number.
- Step 2: verify MOSFET pinout.
- Step 3: measure supply voltage.
- Step 4: measure gate voltage with command off.
- Step 5: measure gate voltage with command on.
- Step 6: measure source voltage with command on.
- Step 7: calculate Vgs.
- Step 8: measure drain voltage with command off.
- Step 9: measure drain voltage with command on.
- Step 10: calculate Vds(on).
- Step 11: measure load current if safe.
- Step 12: estimate MOSFET dissipation.
- Step 13: inspect pulldown resistor.
- Step 14: inspect gate series resistor if present.
- Step 15: inspect flyback diode for inductive loads.
- Step 16: capture drain waveform during turn-off.
- Step 17: reduce switching rate if device heats.
- Step 18: compare actual Vgs with datasheet Rds(on) condition.
- Step 19: save a photo of load and diode wiring.
- Step 20: rerun diagnosis after wiring correction.

## Node Checklist
- Node gate should be driven by controller or signal source.
- Node source should be ground in low-side configuration.
- Node drain should connect to load low side.
- Node load_high should connect to supply.
- Node ground_driver should connect to source ground.
- Node flyback_cathode should connect to positive supply for relay coil.
- Node flyback_anode should connect to drain side of coil.
- Gate pulldown should connect gate to source/ground.
- Gate resistor should be in series with drive if used.
- Load current should not flow through signal ground traces.
- Scope ground should be circuit ground.
- Use differential probing if measuring spikes beyond safe ground reference.
- Do not short the load with a probe ground clip.
- Check breadboard rail continuity.
- Check controller and load supply share reference.
- Check MOSFET tab connection if using a power package.
- Check heat sink isolation if applicable.
- Check load polarity for diodes and motors.
- Check that LED loads include current limiting.
- Check that relay coil voltage matches supply.

## Debug Reasoning
- If load never turns on, measure Vgs directly.
- If Vgs is low, suspect gate_not_driven.
- If source is not at ground, suspect source_not_grounded.
- If Vgs is adequate but drain remains high, suspect MOSFET pinout or damaged device.
- If load is weak, inspect Rds(on) at available gate drive.
- If MOSFET heats, calculate dissipation.
- If microcontroller resets on turn-off, inspect flyback_missing.
- If output pin is damaged, gate may have been overvoltage or spike-coupled.
- If load never turns off, inspect floating gate and body diode path.
- If drain is low even when off, drain-source may be shorted.
- If diode heats immediately, it may be reversed.
- If relay releases slowly, flyback diode is working but clamp is slow.
- If fast release is required, a zener clamp may be used in advanced designs.
- If PWM causes heating, inspect gate drive strength and frequency.
- If source bounce appears, improve ground routing.
- If drain spikes exceed ratings, stop repeated switching.
- If load supply is separate, tie grounds correctly for low-side switching.
- If the controller is 3.3 V, select a MOSFET specified at 2.5 V or 3.3 V.
- Do not judge MOSFET by threshold voltage alone.
- Do not omit a flyback path on inductive loads.

## Student Explanation Prompts
- Ask for MOSFET part number.
- Ask for load type and current.
- Ask for gate voltage on and off.
- Ask for source voltage on and off.
- Ask for measured Vgs.
- Ask for drain voltage on and off.
- Ask whether the load is inductive.
- Ask whether a flyback diode is installed.
- Ask for diode orientation photo.
- Ask whether the controller ground and load ground are common.
- Ask for MOSFET pinout source.
- Ask whether the MOSFET gets warm.
- Ask for PWM frequency and duty cycle if used.
- Ask whether the load turns partly on.
- Ask whether the microcontroller resets.

## Repair Confirmation
- After gate repair, Vgs should match control high voltage.
- After source repair, source should be near ground under load.
- After flyback repair, drain spike should be clamped.
- Load should turn fully on when gate is high.
- Load should turn fully off when gate is low.
- MOSFET temperature should remain reasonable.
- Controller should not reset during switching.
- Drain waveform should match expected low-side switching.
- The repaired report should include Vgs and Vds(on).
- The repaired report should mention threshold voltage is not full-on voltage.
- Corrected concept: MOSFETs are controlled by gate-to-source voltage.
- Corrected concept: source ground is part of the gate-drive loop.
- Corrected concept: inductive loads need a current path when switched off.
- Corrected concept: logic-level specification must match actual controller voltage.
- Corrected concept: drain voltage confirms whether the load path is actually switching.
- End of N-MOSFET low-side switch notes.
