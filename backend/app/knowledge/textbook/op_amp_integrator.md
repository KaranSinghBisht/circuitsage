# Op-Amp Integrator Lab Notes

## Scope
- Topology: op_amp_integrator.
- Circuit family: inverting op-amp with capacitor in feedback.
- Ideal function: output is proportional to the time integral of input.
- Lab use: ramp generation, waveform shaping, control-system examples.
- Practical use: filtered integration with a leak/reset resistor.
- Relevant catalog fault: feedback_cap_open.
- Relevant catalog fault: reset_resistor_missing.
- Relevant catalog fault: input_resistor_wrong.
- These notes assume low-voltage bench supplies.
- Do not debug high-voltage integrators with this guide.
- Always begin with DC operating point.
- Do not start with a long transient sweep before checking rails.

## Core Theory
- An ideal inverting integrator uses an input resistor and a feedback capacitor.
- Current through the input resistor charges the feedback capacitor.
- The inverting input is held near virtual ground when feedback is intact.
- The output moves to keep the inverting node near the reference.
- For a constant positive input, an inverting integrator ramps negative.
- For a constant negative input, it ramps positive.
- The ideal transfer function is Vout/Vin = -1/(s*Rin*Cfb).
- The ramp slope magnitude is |Vin|/(Rin*Cfb).
- Larger Rin gives a slower ramp.
- Larger Cfb gives a slower ramp.
- Smaller Rin gives a faster ramp.
- Smaller Cfb gives a faster ramp.
- A sine input is shifted by about -90 degrees in the ideal inverting form.
- Integration magnitude falls as input frequency rises.
- DC input causes unbounded ramp in the ideal model.
- Real op-amps saturate at the supply rails.
- Input offset voltage also integrates.
- Input bias current also integrates.
- A practical integrator needs a reset or leak path.
- A resistor in parallel with Cfb limits DC gain.
- That resistor creates a low-frequency pole/zero transition.
- Above the practical corner, the circuit behaves like an integrator.
- Below the practical corner, it behaves like a finite-gain inverting amplifier.
- Op-amp output swing limits maximum ramp amplitude.
- Slew rate limits maximum ramp slope.
- GBW limits high-frequency accuracy.
- Capacitor dielectric absorption can affect precision.
- Breadboard leakage can matter with very large resistors.
- A rail-to-rail op-amp is not always rail-to-rail under load.
- Saturation recovery can hide the original fault.

## Formula Reference
- Ideal transfer: H(s) = -1/(s*Rin*Cfb).
- Ramp slope: dVout/dt = -Vin/(Rin*Cfb).
- Practical leak corner: fleak = 1/(2*pi*Rleak*Cfb).
- Input current: Iin = Vin/Rin.
- Capacitor current: Ic = Cfb*dVc/dt.
- In the virtual-ground approximation, Iin roughly equals -Ic.
- For a square input, output should be triangular.
- For a sine input, output amplitude is Vin/(2*pi*f*Rin*Cfb).
- Doubling frequency halves ideal output amplitude.
- Doubling input amplitude doubles ramp slope.
- Doubling Cfb halves ramp slope.
- Doubling Rin halves ramp slope.
- The reset resistor should be high enough to not dominate intended integration.
- The reset resistor should be low enough to stop offset runaway.
- The virtual-ground node should not have large AC swing.
- Large inverting-node swing means feedback is not controlling the op-amp.
- A missing capacitor makes the feedback path open at DC and AC.
- A shorted capacitor makes feedback too strong at high frequency.
- An omitted reset resistor can look fine briefly and fail over time.
- A wrong input resistor changes slope without necessarily changing shape.

## Expected Behavior
- With input grounded, output should settle near reference, not rail instantly.
- With a DC step input, output should ramp at predictable slope.
- With a square input, output should form triangular ramps.
- With a sine input, output should lag/invert according to integrator phase.
- With the reset switch closed, output should return toward reference.
- With reset open, output should integrate again.
- In the useful range, the inverting node should be near virtual ground.
- Output should not rail during the planned observation window.
- Ramp should be linear before saturation.
- The positive and negative ramp slopes should be symmetric if input is symmetric.
- A single-supply integrator must use a mid-rail reference.
- A dual-supply integrator can use ground as reference.
- Input amplitude must be small enough for the planned ramp time.
- Long time-base measurements reveal offset drift.
- Short time-base measurements reveal whether integration starts correctly.
- A practical integrator should recover after overload.
- The reset/leak resistor should pull output back slowly, not instantly.
- A very fast return suggests reset resistor is too small.
- A rail after several seconds suggests leak path is missing or too large.
- A rail immediately suggests open feedback, wrong reference, or bad rails.

## Common Fault: feedback_cap_open
- Fault id: feedback_cap_open.
- Meaning: the feedback capacitor is not connected.
- Symptom: the op-amp saturates because feedback is effectively open.
- Symptom: inverting input may not stay near virtual ground.
- Symptom: output may jump to a rail instead of ramping.
- The capacitor lead may be one breadboard row off.
- The capacitor may be cracked or not inserted.
- A polarized capacitor may be installed incorrectly.
- A student may put the capacitor from output to ground instead of output to inverting node.
- With feedback cap open, changing input frequency will not restore integration.
- Power off before measuring continuity around the capacitor.
- Measure from op-amp output pin to capacitor output-side lead.
- Measure from capacitor input-side lead to inverting input pin.
- If either path is open, fix wiring first.
- After repair, the inverting node should move less.
- After repair, square input should make triangular output.
- If it still rails slowly, check reset_resistor_missing next.
- If slope is wrong but shape is triangular, check input_resistor_wrong.

## Common Fault: reset_resistor_missing
- Fault id: reset_resistor_missing.
- Meaning: no DC leak path exists across the feedback capacitor.
- Symptom: output drifts to a rail from tiny offsets.
- Symptom: circuit appears correct only for a short capture window.
- Symptom: repeated runs start from different output voltages.
- The ideal integrator has infinite DC gain.
- Infinite DC gain is not practical with real offset.
- A large resistor across Cfb creates finite DC gain.
- The resistor can also be a reset switch or analog switch path.
- If Rleak is omitted, output may rail even with input grounded.
- Measure output after grounding input for several seconds.
- If output keeps drifting, suspect missing leak path.
- Confirm whether the lab schematic includes Rleak.
- If the lab intentionally omits Rleak, use a reset procedure before each trial.
- Record the reset condition before diagnosing AC behavior.
- Add the correct resistor only if it is part of the intended circuit.
- A too-small leak resistor destroys low-frequency integration.
- A too-large leak resistor may not prevent drift.
- The repair is verified by repeatable starting output.

## Common Fault: input_resistor_wrong
- Fault id: input_resistor_wrong.
- Meaning: Rin is not the design value.
- Symptom: ramp slope is too steep or too shallow.
- Symptom: waveform shape is correct but timing is wrong.
- A decade error in Rin causes a decade error in slope.
- A 10 k/100 k mix-up is common.
- Color bands can be misread under poor lighting.
- Breadboard row placement can parallel two resistors unintentionally.
- Measure Rin with power off if uncertain.
- Compare measured ramp slope with Vin/(Rin*Cfb).
- If measured slope is 10x expected, Rin may be 10x smaller.
- If measured slope is 0.1x expected, Rin may be 10x larger.
- If slope is nonlinear, the circuit may be saturating or slew-limited.
- If slope differs only near rail, output swing limit is the issue.
- If slope differs for positive and negative input, check op-amp headroom.
- Correcting Rin should correct slope without changing basic shape.

## Measurement Plan
- Step 1: identify single-supply or dual-supply operation.
- Step 2: measure positive rail at the op-amp pin.
- Step 3: measure negative rail or ground rail at the op-amp pin.
- Step 4: measure reference node voltage.
- Step 5: ground the input and measure output drift.
- Step 6: measure inverting input DC voltage.
- Step 7: measure non-inverting reference voltage.
- Step 8: apply a small square wave.
- Step 9: measure input amplitude at the resistor side.
- Step 10: measure output ramp slope.
- Step 11: compute expected slope from Rin and Cfb.
- Step 12: compare measured and expected slope.
- Step 13: inspect whether output rails before the measurement window ends.
- Step 14: check capacitor continuity with power off.
- Step 15: check leak/reset resistor continuity with power off.
- Step 16: check input resistor value with power off.
- Step 17: repeat with half input amplitude.
- Step 18: repeat with double frequency.
- Step 19: confirm slope changes with amplitude, not with frequency for square input plateaus.
- Step 20: save before and after waveforms.

## Node Checklist
- Node vin should match function generator output.
- Node rin_in should receive the stimulus.
- Node n_inv should be near the reference in closed loop.
- Node n_noninv should equal ground or mid-rail reference.
- Node vout should ramp and not immediately rail.
- Node vcc should match supply.
- Node vee should match supply or ground.
- Node reset should connect only when intended.
- Node cfb_left should connect to inverting input.
- Node cfb_right should connect to output.
- The feedback capacitor must bridge output and inverting node.
- The input resistor must bridge source and inverting node.
- The leak resistor must parallel the capacitor if used.
- The scope probe ground must be circuit ground.
- Use DC coupling to see drift.
- Use cursors to measure slope.
- Record volts per division and seconds per division.
- Avoid clipping by reducing input amplitude.
- Avoid saturation by shortening the capture window.
- Use trigger settings that show the ramp start.

## Debug Reasoning
- If output rails instantly, suspect feedback_cap_open or wrong reference.
- If output drifts slowly with input grounded, suspect reset_resistor_missing.
- If output ramps with wrong slope, suspect input_resistor_wrong or capacitor value.
- If output does not reset, inspect reset switch path.
- If output resets too fast, Rleak may be too small.
- If output is noisy, inspect high-value resistors and breadboard leakage.
- If output shape is curved, inspect saturation and slew rate.
- If inverting node has large swing, feedback is not closing.
- If input node amplitude is wrong, fix source/load before integrator.
- If the op-amp saturates asymmetrically, check supply headroom.
- If square input is not centered, output ramp may drift.
- If a single-supply design uses ground reference, the output may clip.
- If output starts near a rail, reset before testing.
- If repeated trials differ, document initial condition.
- If expected and observed slopes disagree, recompute units.
- Farads, microfarads, nanofarads, and picofarads are easy to mix.
- Seconds and milliseconds are easy to mix.
- The slope formula is sensitive to both value and units.
- Fix wiring faults before substituting op-amps.
- Replace the op-amp only after rails, feedback, and values are verified.

## Student Explanation Prompts
- Ask for Rin marking and measured value.
- Ask for Cfb marking and measured value if available.
- Ask whether a reset/leak resistor is present.
- Ask what the output does with input grounded.
- Ask for the measured ramp slope.
- Ask for the input square-wave amplitude.
- Ask whether output rails before one period completes.
- Ask if the design is single-supply or dual-supply.
- Ask for the reference voltage.
- Ask for the inverting-node voltage.
- Ask for a photo of feedback capacitor rows.
- Ask for a photo of input resistor rows.
- Ask for a capture after reset.
- Ask for a capture several seconds after input grounded.
- Ask for the intended time constant.

## Repair Confirmation
- After repairing Cfb, square input should create a triangular output.
- After adding Rleak, input grounded should no longer rail quickly.
- After correcting Rin, slope should match calculation.
- After reset, the initial output should be repeatable.
- The inverting node should remain near reference.
- The output should remain within rails during the planned capture.
- The repaired waveform should match expected polarity.
- The repaired waveform should match expected slope.
- The repaired report should include slope calculation.
- The repaired report should mention practical integrators need DC control.
- Corrected concept: ideal integration amplifies DC errors without limit.
- Corrected concept: the feedback capacitor is the feedback path.
- Corrected concept: Rin and Cfb set slope together.
- Corrected concept: reset conditions are part of the experiment.
- End of op-amp integrator notes.
