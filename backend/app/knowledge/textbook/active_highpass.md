# Active High-Pass Filter Lab Notes

## Scope
- Topology: active_highpass_filter.
- Circuit family: op-amp first-order high-pass filter.
- Typical lab goal: pass frequencies above cutoff while rejecting slow drift and DC.
- Typical symptom: output is too small at the intended passband.
- Typical symptom: output saturates even with a small AC input.
- Typical symptom: cutoff appears a decade away from the design value.
- Relevant catalog fault: input_cap_wrong_value.
- Relevant catalog fault: bias_return_missing.
- Relevant catalog fault: feedback_resistor_open.
- These notes assume low-voltage instructional circuits only.
- Always confirm the op-amp supply rails before interpreting AC gain.
- Always confirm the function generator ground is common with circuit ground.

## Core Theory
- A high-pass filter attenuates DC and slow changes.
- A first-order high-pass filter has one capacitor and one effective resistance setting cutoff.
- The cutoff formula is fc = 1 / (2*pi*R*C).
- The capacitor impedance falls as frequency rises.
- Below cutoff, the capacitor blocks most of the input signal.
- Above cutoff, the capacitor behaves closer to a short for AC.
- At cutoff, an ideal first-order response is about -3 dB from passband.
- Phase lead is large below cutoff and approaches zero in the passband.
- In an active version, the op-amp also sets gain and buffering.
- The op-amp cannot recover a missing bias path.
- A capacitor-coupled op-amp input still needs a DC reference.
- The non-inverting input usually needs a resistor to ground or mid-supply.
- A single-supply design often biases the signal around mid-rail.
- A dual-supply design often biases the non-inverting input at ground.
- The output common-mode range must be compatible with the chosen bias.
- The input capacitor must be rated for the expected DC voltage.
- Electrolytic capacitors must be oriented correctly if polarized.
- Ceramic capacitors may have tolerance and voltage coefficient errors.
- Large capacitor tolerances can move cutoff substantially.
- Op-amp input bias current creates offsets through bias resistors.
- Bias current matters more with large resistor values.
- High resistor values also raise thermal noise.
- Low resistor values load the source.
- The source impedance participates in the effective high-pass resistance.
- The function generator output impedance is commonly 50 ohms.
- In many student labs, source impedance is small compared with 10 k or 100 k.
- If source impedance is not small, include it in the cutoff calculation.
- Closed-loop op-amp bandwidth limits the upper passband.
- Slew rate can distort large high-frequency signals.
- A high-pass response is not proof that the op-amp wiring is correct.
- DC operating point must be checked before AC response.

## Transfer Function
- For a simple RC high-pass, H(s) = sRC / (1 + sRC).
- The magnitude is |H(jw)| = wRC / sqrt(1 + (wRC)^2).
- The phase is +atan(1 / wRC) for the simple passive form.
- For an inverting active form, include the sign inversion.
- The passband gain may be set by feedback and input resistors.
- If the active stage gain is -Rf/Rin, multiply the high-pass term by that gain.
- For non-inverting high-pass forms, the gain may be 1 + Rf/Rg.
- The cutoff frequency is still governed by the capacitor and its effective resistance.
- Use radians per second for w in formula work.
- Use hertz for lab instruments.
- Convert using w = 2*pi*f.
- At f = fc, the high-pass term magnitude is about 0.707.
- At f = fc/10, the magnitude is about 0.1.
- At f = 10*fc, the magnitude is about 0.995.
- A decade error in C produces a decade error in fc.
- A decade error in R produces a decade error in fc.
- A swapped nF/uF capacitor can shift the response by 1000x.
- A measured passband gain lower than design may indicate feedback damage.
- A measured cutoff with correct gain may indicate only the RC values are wrong.
- A flat zero output can indicate no input coupling, no bias path, or no rails.

## Expected Behavior
- With zero input, output should sit near the chosen bias/reference.
- With a very low frequency sine, output should be strongly attenuated.
- With a sine at cutoff, output should be about 70.7 percent of passband gain.
- With a sine well above cutoff, output should match the designed gain.
- With a square wave below cutoff, output may show narrow edge pulses.
- With a square wave above cutoff, output should look closer to amplified square wave.
- With a DC step, output jumps and then decays back to bias.
- The decay time constant is approximately R*C.
- The measured time constant should agree with 1/(2*pi*fc).
- Passband waveform should not clip at normal test amplitude.
- Output should not rail when the input is centered correctly.
- Output noise may increase with high gain and high resistor values.
- Phase should lead near cutoff in a passive high-pass section.
- Inverting active forms add 180 degrees of inversion.
- The output DC level should not wander when the input lead is touched.
- If the input lead touch changes output wildly, suspect missing bias return.
- If output is always zero, check capacitor continuity and input source.
- If output is always saturated, check reference node and feedback.
- If cutoff is too high, C or R may be too small.
- If cutoff is too low, C or R may be too large.

## Common Fault: input_cap_wrong_value
- Fault id: input_cap_wrong_value.
- Meaning: input capacitor value is not the design value.
- Symptom: measured cutoff shifts away from calculated fc.
- A 10 nF part installed for 100 nF moves cutoff up by 10x.
- A 1 uF part installed for 100 nF moves cutoff down by 10x.
- Multilayer capacitors can have unclear markings.
- Breadboard bins often mix nF and uF values.
- Students often read 104 as 104 nF instead of 100 nF.
- Students may read 103 as 100 nF, but it is 10 nF.
- A polarized capacitor installed backward may leak or distort.
- Leakage can corrupt the DC bias node.
- The first measurement is the output amplitude at a known test frequency.
- The second measurement is output amplitude one decade below expected cutoff.
- The third measurement is output amplitude one decade above expected cutoff.
- If the passband gain is correct but cutoff moved, suspect RC value.
- If both gain and cutoff are wrong, check active feedback too.
- Record the actual capacitor marking in the session evidence.
- Replace the capacitor only after confirming the measured response.

## Common Fault: bias_return_missing
- Fault id: bias_return_missing.
- Meaning: the op-amp input has no DC path to its reference.
- Symptom: output drifts or rails despite correct AC coupling.
- The coupling capacitor blocks DC, so the input node can float.
- A floating high-impedance input collects charge and noise.
- The op-amp input bias current needs a return path.
- A missing bias return can look like a bad op-amp.
- It is usually a wiring problem, not a silicon failure.
- Measure the non-inverting input DC voltage first.
- In a dual-supply lab, it should be near ground.
- In a single-supply lab, it should be near mid-rail.
- If it wanders when touched, the bias return is missing or too large.
- Check that the bias resistor actually reaches the reference node.
- Check the reference node itself has low impedance.
- Check the breadboard rail is continuous across the center break.
- Check that generator ground is not being used as the only DC return.
- Adding the correct bias resistor should bring output off the rail.
- After repair, re-check cutoff because the bias resistor may set R.

## Common Fault: feedback_resistor_open
- Fault id: feedback_resistor_open.
- Meaning: feedback path around the op-amp is broken.
- Symptom: op-amp behaves open-loop and saturates.
- Symptom: passband gain is much larger than expected until clipping.
- Symptom: output polarity may appear meaningless because it is railed.
- The feedback resistor may be in the wrong breadboard row.
- One resistor lead may be floating beside the op-amp pin.
- The op-amp output pin may be misidentified.
- The inverting input pin may be misidentified.
- A jumper may connect to an adjacent unused row.
- Use continuity mode with power off to verify feedback.
- Measure resistance from output node to inverting input node.
- The measured value should match Rf within tolerance.
- If the DMM reads open, repair feedback before AC testing.
- If feedback is open, changing input capacitor will not fix the rail.
- Feedback repairs should make the DC operating point stable.

## Measurement Plan
- Step 1: record supply rails at op-amp pins.
- Step 2: record the reference node DC voltage.
- Step 3: record non-inverting input DC voltage.
- Step 4: record inverting input DC voltage.
- Step 5: record output DC voltage with input connected.
- Step 6: record input sine amplitude at the circuit input node.
- Step 7: record output sine amplitude one decade below cutoff.
- Step 8: record output sine amplitude at cutoff.
- Step 9: record output sine amplitude one decade above cutoff.
- Step 10: compute output/input gain at each frequency.
- Step 11: compare passband gain with design.
- Step 12: compare cutoff with 1/(2*pi*R*C).
- Step 13: if output rails, stop AC sweep and debug DC first.
- Step 14: if DC is stable, debug capacitor/resistor values.
- Step 15: if passband gain is wrong, debug feedback network.
- Step 16: if only cutoff is wrong, debug RC network.
- Step 17: save a waveform CSV when possible.
- Step 18: save a photo of the capacitor marking.
- Step 19: save a close photo of the op-amp feedback rows.
- Step 20: rerun diagnosis after each repair.

## Node Checklist
- Node vin should show the generator signal.
- Node cap_out or n_input should be centered around the bias point.
- Node n_noninv should have a DC reference.
- Node n_inv should not float.
- Node vout should not sit at a rail in normal operation.
- Node vcc should match the positive rail.
- Node vee should match the negative rail or ground in single-supply designs.
- Node gnd should be common to generator ground.
- The capacitor input side may carry source DC.
- The capacitor output side should carry the op-amp input bias.
- A DMM can measure DC bias but not high-frequency gain accurately.
- An oscilloscope is preferred for cutoff work.
- Use AC coupling on the oscilloscope only after recording DC bias.
- Do not hide a DC rail problem with scope AC coupling.
- Probe ground clips must attach to circuit ground.
- Two grounded instruments can create unintended shorts.
- Keep input amplitude small enough to avoid clipping.
- Increase frequency only after confirming bias.
- Use logarithmic frequency steps for cutoff sweeps.
- At each frequency, wait for the display to settle.

## Debug Reasoning
- If rails are wrong, fix power first.
- If output rails and input bias floats, prioritize bias_return_missing.
- If output rails and feedback is open, prioritize feedback_resistor_open.
- If DC is stable and cutoff shifted, prioritize input_cap_wrong_value.
- If DC is stable and passband gain is wrong, inspect feedback ratio.
- If response is noisy, inspect resistor values and breadboard contact.
- If response changes when touching the capacitor, suspect floating nodes.
- If output phase seems inverted, identify the active topology before judging.
- If the function generator output amplitude is set in high-Z mode, actual load voltage may differ.
- If a 50 ohm source setting is wrong, measured gain can appear off by 2x.
- If a single-supply op-amp cannot swing to ground, a small signal around 0 V may clip.
- If a rail-to-rail assumption is false, output headroom may be the real fault.
- If the op-amp GBW is too low, high-frequency passband can roll off.
- If slew rate is exceeded, sine waves become triangular or distorted.
- If the capacitor is microphonic, tapping can inject noise.
- If breadboard capacitance matters, the designed cutoff may be too high for a breadboard.
- If the input capacitor is missing, the circuit may pass no AC.
- If the input capacitor is shorted, the circuit may pass DC and lose high-pass behavior.
- If the bias resistor is too small, it can load the source.
- If the bias resistor is too large, it can create drift.

## Student Explanation Prompts
- Ask what frequency was tested.
- Ask what amplitude was used.
- Ask whether the scope was AC-coupled.
- Ask whether input and output were measured at the same time.
- Ask for the capacitor marking.
- Ask for the intended cutoff frequency.
- Ask for the actual resistor value measured out of circuit.
- Ask whether the op-amp uses single or dual supply.
- Ask whether the reference is ground or mid-rail.
- Ask whether the output clips before reaching passband gain.
- Ask for a photo of the input capacitor rows.
- Ask for a photo of the feedback resistor rows.
- Ask for a waveform one decade above cutoff.
- Ask for a waveform one decade below cutoff.
- Ask for the DC output voltage with no input.

## Repair Confirmation
- After replacing the capacitor, measure cutoff again.
- After adding a bias return, measure input DC again.
- After repairing feedback, measure resistance from output to inverting input.
- After any wiring fix, re-check rail voltages.
- The repaired circuit should have stable DC output.
- The repaired circuit should attenuate low frequencies.
- The repaired circuit should pass high frequencies at designed gain.
- The repaired circuit should not rail under normal test amplitude.
- The repaired circuit should produce repeatable measurements.
- Record before and after waveforms for the lab report.
- Write the corrected concept in one sentence.
- Example correction: a coupling capacitor does not provide a DC input reference.
- Example correction: cutoff follows R*C, so a decade capacitor error creates a decade frequency error.
- Example correction: open feedback makes an op-amp act like a comparator.
- End of active high-pass notes.
