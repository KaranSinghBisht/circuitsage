# CircuitSage Accessibility Notes

Repo-side implementation:

- Keyboard focus rings are visible on links, buttons, inputs, textareas, and selects.
- Studio, Bench, Companion, Faults, and Educator routes use native controls in document order.
- `GemmaStatusBanner` uses `role="status"` and `aria-live="polite"` for model-status changes.
- QR images and screen snapshots have descriptive alt text.
- Status chips include text labels and colors; they do not rely on red/green alone.
- High-contrast, large-font, sound, and language controls are available from the home screen and persist in `localStorage`.
- Reduced-motion users get animation and transition durations reduced through `prefers-reduced-motion`.

Manual walkthrough checklist for submission:

1. Open `/`, tab through language, high-contrast, large-font, sound, companion, demo, create-session, and demo tiles.
2. Load the op-amp demo and confirm the screen reader announces the session title, status, fallback banner when Ollama is down, artifact controls, measurement form labels, prompt field, and diagnosis card.
3. Toggle Hindi and confirm labels render without clipping on desktop and mobile widths.
4. Toggle high contrast and large font, then rerun the Studio tab order.
5. Open Bench Mode from the QR link and confirm capture, measurement, and chat controls are reachable by keyboard.

Physical screen-reader validation remains a USER ACTION before final submission.
