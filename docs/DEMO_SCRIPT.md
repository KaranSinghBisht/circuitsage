# CircuitSage Demo Script v2

Target cut: 3:00 maximum.

Format: screen capture plus phone camera inserts plus a few bench closeups.

Primary promise: CircuitSage turns circuit debugging into a structured evidence loop.

Closing line: CircuitSage. Stack traces for circuits.

## Production Rules

Every filming step below is a `USER ACTION`.

Codex prepares the script, data, routes, and smoke checks.

The human operator records the video, voiceover, bench clips, and phone clips.

Do not fake the on-device airplane-mode scene.

If the local model bundle is unavailable, film the UI path and label the model bundle as pending.

Keep the final video under 3 minutes.

Run `bash scripts/demo_smoke.sh` before every serious take.

Run `make demo-seed` before filming the Educator dashboard.

Keep the browser zoom at 100 percent.

Use a clean desktop with only CircuitSage, LTspice/Tinkercad/MATLAB, and the terminal visible.

Use one visible cursor style for the whole screen capture.

Avoid fast mouse circles.

Leave each overlay readable for at least 1.5 seconds.

Use the same session throughout the main op-amp story.

## Per-Beat Table

| Beat | Time | Scene | Camera angle | Overlay text | Voiceover line | Required proof |
|---|---:|---|---|---|---|---|
| 1 | 0:00-0:18 | Hook | Bench closeup, silent scope | Software has stack traces. Circuits do not. | Software students get stack traces. Electronics students get silence. | Show failed waveform or flat output. |
| 2 | 0:18-0:38 | Studio tour | Screen capture | Evidence in one session | I load the op-amp demo: manual, netlist, waveform, measurements, and tool calls. | Show artifacts, parsed netlist, and deterministic tools. |
| **3** | **0:38-1:10** | **Companion + LTspice (HERO)** | **Screen capture, LTspice + overlay** | **Multimodal + native tools** | **The student presses Cmd+Shift+Space inside LTspice. Gemma sees the schematic, names the topology, and runs the deterministic SPICE catalog.** | **Show overlay → topology detected → click-to-act buttons → datasheet brief inline.** |
| 4 | 1:10-1:35 | Airplane-mode scene (optional) | Phone camera, status bar visible | On-device Gemma, no internet | The same loop runs locally on the phone in airplane mode. | Show airplane mode + structured diagnosis. **Skip if iOS bundle pending.** |
| 5 | 1:35-2:10 | Fix and retest | Bench closeup plus scope screen | Ground the reference input | The fault is not magic: the non-inverting input is floating. Ground it and retest. | Show jumper fix and waveform recovery. |
| 6 | 2:10-2:30 | Report | Screen capture | Lab report generated | CircuitSage turns the session into a report students can submit and instructors can review. | Show PDF pages. |
| 7 | 2:30-2:55 | Educator dashboard | Screen capture | Class-wide misconceptions | Across demo sessions, the dashboard surfaces repeated faults and stalled measurements. | Show non-empty metrics and common faults. |
| 8 | 2:55-3:00 | Closing card | Static screen | CircuitSage | CircuitSage. Stack traces for circuits. | Show repo-ready app name and tagline. |

> **Cut order if shoot runs long:** drop Beat 4 (airplane-mode) first, then Beat 6 (report), then compress Beat 7 (educator) to a single screen. Beat 3 (Companion + LTspice) is the hero — never cut it.

> **Why Beat 3 is the hero:** the hackathon banner names *multimodal* + *native function calling* as the Gemma 4 differentiators. Beat 3 demonstrates both in one screen capture: vision call describes the LTspice canvas, then the deterministic SPICE catalog (`score_faults`) and the datasheet retriever (`lookup_datasheet`) run as click-to-act buttons. Competing entries in this hackathon are mostly study-companion chatbots; nothing else integrates with a real desktop EDA tool.

## Beat 1 - Hook

Timebox: 0:00-0:18.

Purpose: make the problem obvious before explaining the product.

`USER ACTION`: film a real bench or a staged low-voltage bench.

Camera angle: tight shot of scope or multimeter, then a hand hovering over a breadboard.

Screen source: none unless a simulator window is visible in the background.

On-screen overlay: Software has stack traces. Circuits do not.

Voiceover: Software students get stack traces. Electronics students get silence.

Action 1: show an output stuck near a rail or a flat waveform.

Action 2: pause on the student not knowing which node to measure next.

Action 3: cut before any product UI appears.

Audio: keep bench room noise low; do not use dramatic music.

B-roll option: flat oscilloscope trace.

B-roll option: multimeter reading near +12 V.

B-roll option: simulator window with expected sine wave in background.

Retake if the display is unreadable.

Retake if the camera shakes during the first 3 seconds.

Retake if any mains-powered exposed circuit is visible.

Retake if the shot implies CircuitSage is for high-voltage debugging.

Continuity note: the failed circuit should match the op-amp story used later.

Continuity note: use low-voltage rails only.

Cut point: first visible product UI starts the next beat.

## Beat 2 - Studio Tour

Timebox: 0:18-0:42.

Purpose: show CircuitSage as a real working tool, not a chatbot.

`USER ACTION`: screen-record the browser.

Camera angle: screen capture only.

Screen source: `http://localhost:5173`.

On-screen overlay: Evidence in one session.

Voiceover: I load the op-amp demo: manual, netlist, waveform, measurements, and the tools CircuitSage ran.

Action 1: click Load Op-Amp Demo.

Action 2: show the session title.

Action 3: show the artifacts panel.

Action 4: show the parsed schematic/netlist preview.

Action 5: show the evidence strip.

Action 6: run diagnosis if the seed did not already show it.

Action 7: pause on tool calls.

Tool call to highlight: safety_check.

Tool call to highlight: parse_netlist.

Tool call to highlight: compare_expected_vs_observed.

Tool call to highlight: retrieve.

Narrative point: the system reasons over evidence.

Narrative point: the answer includes next measurement, not only a fault guess.

B-roll option: zoomed crop of the diagnosis card.

B-roll option: cursor hovering over the waveform plot.

B-roll option: datasheet badge if visible.

Retake if the app is in a loading state for more than 2 seconds.

Retake if the browser console is visible.

Retake if the demo seed returns a different primary fault.

Retake if the tool call list is empty.

Continuity note: expected fault is floating_noninv_input.

Continuity note: status can be deterministic fallback if Ollama is down.

Cut point: QR code or Bench Mode button appears.

## Beat 3 - Companion + LTspice (HERO)

Timebox: 0:38-1:10.

Purpose: the centerpiece. Show the real "I'm in LTspice, ask Gemma what's wrong" loop with multimodal vision and click-to-act deterministic tools.

`USER ACTION`: screen-record macOS with LTspice in the foreground and the CircuitSage Companion as a small floating overlay.

Camera angle: full-screen capture of macOS desktop (LTspice + overlay).

Screen source: LTspice with the canonical inverting op-amp `.asc` open; CircuitSage Companion overlay docked top-right.

On-screen overlay text: "Multimodal + native tools".

Voiceover: "Inside LTspice, the student presses Cmd+Shift+Space. Gemma sees the schematic in one vision call, names the topology, and runs the deterministic SPICE catalog as named tools. No tab switching, no manual upload."

Action 1: LTspice is in focus with the broken inverting op-amp `.asc` (V+ floating, deliberate). Mouse hovers, no progress.

Action 2: press `Cmd+Shift+Space`. Companion overlay appears top-right (always-on-top, < 420 px wide).

Action 3: type into the overlay: "Why is the output saturating?"

Action 4: click "Analyze Current Screen". The overlay shows a brief progress dot (5-10 s on `gemma3:4b`).

Action 5: **DIP-Sage (the desktop pet) reacts on screen as the answer arrives** — eyes flip from idle green to *blue + pulsing aura* during the call, then bounce + green aura when the high-confidence diagnosis returns. Speech bubble shows "op amp inverting · high". This single beat is the strongest visual proof of the multimodal loop running locally.

Action 5b: result panel renders:
- Header: `ollama_gemma_vision · medium confidence · 7820 ms`.
- Workspace title: `ltspice · op_amp_inverting`.
- `visible_context`: short factual sentence ("inverting op-amp configuration with TL081-style ref U1, output stuck near +Vcc").
- `answer`: composed text including the catalog top match ("Top catalog match: Floating non-inverting input ...").
- `suspected_faults`: bullet list (1-2 items).
- Three click-to-act buttons rendered inline.

Action 6: click button "Score op_amp_inverting fault catalog". Result block expands inline showing ranked faults: floating_noninv_input (0.58), missing_feedback (0.55), rail_imbalance (0.35). 1 ms. Pause 2 seconds on this — judges need to see the deterministic catalog grounded the model output.

Action 7: click button "Look up TL081 datasheet". Result block expands inline showing the TL081 brief. 1 ms. Pause 1 second.

Action 8: click button "Capture again after grounding V+". (Optional — saves time if you skip and let the next beat show the fix.)

Action 9 (optional B-roll): demonstrate the **highlight crop** by pressing `Cmd+Shift+X`, dragging a tight rectangle around just the op-amp triangle in the schematic, releasing — the overlay fades, the companion window pops with that crop pre-filled, and the auto-prompt fires after 700 ms. Use this as alternate hero footage if the full-window vision call looks muddled.

Required proof: hotkey shortcut visible (overlay text "Cmd+Shift+Space" near the icon).

Required proof: overlay shows `mode: ollama_gemma_vision` in the header (not deterministic_fallback). If Ollama is down at shoot time, retake after `ollama serve && ollama pull gemma3:4b`.

Required proof: at least one click-to-act button is clicked and the inline tool result is visible for ≥ 2 s.

Required proof: header shows non-zero `duration_ms` (proves single-call vision, not staged).

Native-function-calling beat: the click-to-act buttons are exactly the "tool calls" judges expect when the banner says "native function calling". Make this visible in the overlay narration.

Continuity note: this is the same op-amp fault as Beat 1 hook and Beat 5 fix.

Continuity note: if `gemma3:4b` is not loaded, the header reads `deterministic_fallback` — RETAKE.

B-roll option: tighter crop on the overlay header showing `ollama_gemma_vision`.

B-roll option: tighter crop on the inline ranked-faults result.

B-roll option: the typed actions row before any click.

Retake if the overlay covers the LTspice schematic.

Retake if the result panel shows `gemma_text_unparsed` (model returned prose; re-prompt and re-shoot).

Retake if no click-to-act button is rendered (means topology detection failed — re-prompt with sharper question).

Retake if the duration exceeds 25 seconds (model is too slow; verify `OLLAMA_VISION_MODEL=gemma3:4b`, not `gemma4:e4b`).

Cut point: just after the inline tool result is visible, before fixing the circuit.

## Beat 4 - Bench Handoff (cut if time)

Optional beat — only film if total runtime would be under 3:00 with it. Hero is now Beat 3.

Timebox: 0:42-1:05.

Purpose: prove the workflow follows the student from laptop to bench.

`USER ACTION`: film phone and screen together.

Camera angle: over-the-shoulder phone shot with laptop in frame.

Screen source: Studio or Bench QR panel.

On-screen overlay: Pair the phone.

Voiceover: The same session moves to the bench phone with a QR code.

Action 1: click Start Bench.

Action 2: show the QR code.

Action 3: open the phone camera or scanner.

Action 4: open Bench Mode on the phone.

Action 5: show the same session context on phone.

Action 6: enter or prepare to enter `V_noninv`.

Measurement to enter: `V_noninv = 2.8 V DC`.

Keep the phone brightness high.

Keep the laptop brightness lower to reduce glare.

B-roll option: close crop of QR code.

B-roll option: phone loading Bench Mode.

B-roll option: thumb entering the measurement.

Retake if the QR code is out of focus.

Retake if the phone URL is not visible long enough to understand.

Retake if Bench Mode opens a stale session.

Retake if the phone keyboard covers the measurement label.

Continuity note: do not change the session between beats.

Continuity note: the measurement should match the diagnosis request.

Cut point: phone is ready for local/offline mode.

## Beat 4 - Airplane-Mode Scene

Timebox: 1:05-1:35.

Purpose: show the Digital Equity story: useful help without internet.

`USER ACTION`: film the physical iPhone.

Camera angle: phone closeup, status bar visible.

Screen source: iOS app or mobile Bench route.

On-screen overlay: On-device Gemma. No internet.

Voiceover: Now the phone is in airplane mode and still answers from the local model.

Action 1: open Control Center.

Action 2: toggle airplane mode on.

Action 3: confirm Wi-Fi and cellular are off.

Action 4: return to CircuitSage.

Action 5: ask by voice: My inverting op-amp is stuck near +12 V. What should I check?

Action 6: show the local model toggle if present.

Action 7: wait for the answer.

Action 8: show next measurement and likely fault.

Required visible proof: airplane mode icon in status bar.

Required visible proof: CircuitSage answer appears after airplane mode is enabled.

Required visible proof: answer names the reference input or next measurement.

Do not hide latency with a jump cut unless the overlay says elapsed time.

If the model takes 20 seconds, keep a tasteful speed ramp but preserve the start and finish.

If the local bundle is unavailable, mark the shot as `USER ACTION pending` in blockers.

B-roll option: phone status bar crop.

B-roll option: local model chip.

B-roll option: waveform or breadboard visible behind the phone.

Retake if airplane mode is not visible.

Retake if the answer comes from a cloud endpoint.

Retake if the answer claims certainty without the `V_noninv` evidence.

Retake if voice recognition mishears the question.

Continuity note: this is the airplane-mode scene referenced in the writeup.

Continuity note: never imply live mains debugging is supported.

Cut point: fault identified, before the fix.

## Beat 5 - Fix And Retest

Timebox: 1:35-2:10.

Purpose: close the loop from diagnosis to physical repair.

`USER ACTION`: film the bench.

Camera angle: breadboard closeup plus scope insert.

Screen source: live scope panel or oscilloscope.

On-screen overlay: Ground the reference input.

Voiceover: The fault is not magic. The non-inverting input is floating, so the op-amp saturates. Ground it and retest.

Action 1: power off the low-voltage circuit.

Action 2: add the jumper from non-inverting input to circuit ground.

Action 3: power on.

Action 4: show Vout no longer pinned to +12 V.

Action 5: show live scope or waveform returning toward expected behavior.

Action 6: return to CircuitSage and show confidence/diagnosis improved if available.

Safety overlay: Power off before rewiring.

Measurement overlay: `V_noninv -> 0 V`.

B-roll option: hand placing jumper.

B-roll option: multimeter reading near 0 V at reference input.

B-roll option: before/after waveform split.

B-roll option: diagnosis card with fix recipe.

Retake if the jumper action is blocked by the hand.

Retake if the circuit remains visibly broken after the fix.

Retake if the scope timebase changes between before and after without explanation.

Retake if the bench shot includes unsafe wiring.

Continuity note: same breadboard as Beat 1.

Continuity note: same fault as Studio diagnosis.

Cut point: waveform is visibly corrected.

## Beat 6 - Lab Report PDF

Timebox: 2:10-2:35.

Purpose: show the student and instructor artifact at the end of the loop.

`USER ACTION`: screen-record the report.

Camera angle: screen capture.

Screen source: Studio report panel and PDF viewer.

On-screen overlay: Lab report generated.

Voiceover: CircuitSage turns the debug trail into a lab report with evidence, tools, diagnosis, and next steps.

Action 1: click Report.

Action 2: show generated markdown or report preview.

Action 3: click PDF.

Action 4: show the PDF header.

Action 5: scroll once through the key sections.

Action 6: stop on the diagnosis section.

Required proof: report includes session context.

Required proof: report includes measurements.

Required proof: report includes diagnosis and safety notes.

B-roll option: PDF title page.

B-roll option: schematic render.

B-roll option: evidence table.

Retake if the PDF opens blank.

Retake if the PDF downloads but is not shown.

Retake if text is too small to read.

Retake if private local paths are visible in the PDF viewer.

Continuity note: do not switch sessions.

Cut point: transition to educator dashboard.

## Beat 7 - Educator Dashboard

Timebox: 2:35-2:55.

Purpose: prove classroom-level value.

`USER ACTION`: screen-record the dashboard.

Camera angle: screen capture.

Screen source: `/educator`.

On-screen overlay: Class-wide misconceptions.

Voiceover: Instructors see patterns too: repeated faults, safety refusals, and measurements where students stall.

Action 1: run `make demo-seed` before filming.

Action 2: open `/educator`.

Action 3: show Sessions.

Action 4: show Safety refusals.

Action 5: show Common faults.

Action 6: show Stalled measurements.

Action 7: briefly open `/uncertainty` if time allows.

Required proof: dashboard is not empty.

Required proof: common faults list is populated.

Required proof: stalled measurements list is populated.

B-roll option: uncertainty gallery cards.

B-roll option: fault gallery cards.

B-roll option: seeded sessions list.

Retake if metrics read zero.

Retake if the dashboard is still loading.

Retake if seeded data is duplicated from repeated test runs.

Retake if the route is shown before `make demo-seed`.

Continuity note: educator view is a product feature, not a marketing slide.

Cut point: closing card.

## Beat 8 - Closing Card

Timebox: 2:55-3:00.

Purpose: land the name and memory hook.

`USER ACTION`: capture or render a clean closing card.

Camera angle: static screen.

Screen source: homepage or press route.

On-screen overlay: CircuitSage.

Voiceover: CircuitSage. Stack traces for circuits.

Action 1: show the homepage tagline.

Action 2: show repo-ready app name.

Action 3: cut exactly at or before 3:00.

B-roll option: homepage hero.

B-roll option: animated press kit loop.

B-roll option: app icon or cover image.

Retake if the video exceeds 3:00.

Retake if the final text is cropped.

Retake if the closing card uses a different tagline.

Continuity note: end on the same visual system as the app.

## B-Roll Library

Capture these clips after the main take.

`USER ACTION`: record every B-roll clip listed here if time allows.

Clip 1: failed oscilloscope trace before fix.

Clip 2: corrected oscilloscope trace after fix.

Clip 3: breadboard closeup with reference input jumper.

Clip 4: multimeter at `V_noninv`.

Clip 5: Studio artifacts panel.

Clip 6: tool call timeline.

Clip 7: schematic/netlist preview.

Clip 8: QR code handoff.

Clip 9: phone in airplane mode.

Clip 10: local model chip or offline toggle.

Clip 11: PDF report scroll.

Clip 12: Educator common faults.

Clip 13: Uncertainty gallery.

Clip 14: Fault gallery.

Clip 15: Companion watching LTspice/Tinkercad/MATLAB screen.

Clip 16: terminal running `bash scripts/demo_smoke.sh`.

Clip 17: dataset validation output.

Clip 18: eval harness placeholder or last-run metrics.

Clip 19: safety refusal response.

Clip 20: hosted demo route if available.

## Retake Guidance

Retake the full video if the main story exceeds 3:00.

Retake the full video if the op-amp fault changes.

Retake the full video if the airplane-mode scene is missing.

Retake the full video if Bench Mode cannot be paired.

Retake the full video if the PDF fails to open.

Retake the full video if the educator dashboard is empty.

Retake only Beat 1 if the scope shot is blurry.

Retake only Beat 2 if tool calls are not visible.

Retake only Beat 3 if QR pairing is unclear.

Retake only Beat 4 if the phone status bar is cropped.

Retake only Beat 5 if the fix action is hidden.

Retake only Beat 6 if PDF text is unreadable.

Retake only Beat 7 if metrics are stale.

Retake only Beat 8 if the final card runs too long.

Use the animated press route as fallback B-roll if a bench clip fails.

Use screen capture over handheld footage whenever text matters.

Do not use a take that shows unsafe probing.

Do not use a take where CircuitSage appears to debug mains or high voltage.

Do not use a take that hides whether the model is local or cloud.

Do not use a take with unrelated browser tabs visible.

## Pre-Shoot Checklist

Run `git status --short`.

Run `make demo-seed`.

Run `bash scripts/demo_smoke.sh`.

Open `/`.

Open `/faults`.

Open `/uncertainty`.

Open `/educator`.

Load the op-amp demo.

Confirm `floating_noninv_input` appears.

Confirm PDF opens.

Confirm phone can reach Bench Mode.

Confirm local model bundle status.

Confirm airplane-mode behavior.

Confirm microphone permissions.

Confirm screen recording permissions.

Confirm no secret tokens are visible.

Confirm desktop notifications are muted.

Confirm the bench circuit is low voltage.

Confirm the voiceover microphone level.

Confirm camera focus on the phone.

Confirm all overlays are spelled correctly.

## Voiceover Full Read

Software students get stack traces.

Electronics students get silence.

Here is a real op-amp lab failure.

The simulator expects an inverting gain of about minus 4.7.

The bench output is stuck near the positive rail.

CircuitSage keeps the evidence in one session.

It has the lab manual, netlist, waveform, measurements, and a tool trace.

It does not just guess.

It asks for the next useful measurement.

Now the same session moves to the bench phone.

The student pairs with a QR code and records the measurement at the circuit.

This is the Digital Equity moment.

The phone is in airplane mode.

The local Gemma model still answers.

The diagnosis points to the non-inverting input reference.

Power off before rewiring.

Ground the reference input.

Retest the output.

The waveform comes back.

CircuitSage then produces a report with the evidence, tools, diagnosis, and safety notes.

For instructors, the educator dashboard shows repeated faults and stalled measurements across sessions.

It also includes uncertainty cases where the system asks for more evidence instead of pretending.

CircuitSage.

Stack traces for circuits.
