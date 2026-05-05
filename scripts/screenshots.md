# Screenshot Capture Script

Use this checklist after `make demo-seed` and `bash scripts/demo_smoke.sh`.

Save all final images under `media/screenshots/`.

## 1. Studio

1. Open `/`.
2. Click `Load Op-Amp Demo`.
3. Wait for the diagnosis card and tool calls.
4. Capture `media/screenshots/01-studio.png`.
5. Include artifacts, evidence strip, diagnosis, and tool timeline.

## 2. Bench

1. From the same session, click `Start Bench`.
2. Open the Bench URL or QR route on a narrow viewport.
3. Show measurement entry for `V_noninv`.
4. Capture `media/screenshots/02-bench.png`.
5. Keep the session title visible.

## 3. Companion

1. Open `/companion`.
2. Start screen sharing if browser permissions are available.
3. Put an LTspice, Tinkercad, MATLAB, or waveform window behind it.
4. Ask a short prompt.
5. Capture `media/screenshots/03-companion.png`.

## 4. Educator

1. Run `make demo-seed`.
2. Open `/educator`.
3. Confirm sessions, safety refusals, common faults, and stalled measurements are non-empty.
4. Capture `media/screenshots/04-educator.png`.

## 5. Faults

1. Open `/faults`.
2. Scroll to show at least two topology groups.
3. Capture `media/screenshots/05-faults.png`.
4. Make sure a `Try this fault` button is visible.

## 6. Uncertainty

1. Open `/uncertainty`.
2. Confirm eight uncertainty cards render.
3. Capture `media/screenshots/06-uncertainty.png`.
4. Include at least one card showing `confidence: low`.

## 7. PDF Report

1. Return to the op-amp demo session.
2. Generate the report.
3. Open `/api/sessions/<id>/report.pdf`.
4. Capture `media/screenshots/07-report-pdf.png`.
5. Show the diagnosis or evidence section.

## 8. On-Device iOS

1. Install the iOS development client on a physical iPhone.
2. Provision the local Gemma model bundle.
3. Open the session from Bench Mode.
4. Turn on airplane mode.
5. Ask the op-amp question by voice.
6. Capture `media/screenshots/08-ios-airplane.png`.
7. The airplane-mode icon and CircuitSage answer must both be visible.
