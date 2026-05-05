# CircuitSage Submission Checklist

Source: `docs/WINNING_FORWARD_PLAN.md` Section 9.

| Status | Item |
|---|---|
| [ ] | `make install && make demo` works on a fresh clone in < 5 min. |
| [ ] | All 12 topology seed endpoints (6 + 6 from K8) return non-canned diagnoses. |
| [ ] | Schematic-to-netlist (K1) recognizes the canonical op-amp photo within +/-1 component. |
| [ ] | iPhone in airplane mode answers a question via on-device Gemma 4 in <= 30 s. |
| [ ] | Voice in/out works on iOS (Phase 5). |
| [ ] | LoRA `circuitsage:latest` is loaded; `gemma_model` reports it. |
| [ ] | LoRA eval harness (Q3) reports schema-validity >= 95 %, top-1 fault-id >= 60 %. |
| [ ] | Hosted demo URL serves the op-amp seed in < 5 s. |
| [ ] | PDF lab report renders cleanly. |
| [ ] | Educator dashboard renders aggregates. |
| [ ] | Faults gallery shows >= 30 cards; uncertainty gallery shows >= 6 cases. |
| [ ] | Hindi, Spanish, Portuguese locales render without layout breakage. |
| [ ] | Accessibility audit passes (manual screen-reader walkthrough; high-contrast mode toggle works). |
| [ ] | CI green on the submission commit. |
| [ ] | Video script printed; bench BOM ready. |
| [ ] | Writeup <= 1500 words; cover image rendered. |
| [ ] | HF dataset card + model card uploaded (K9). |
| [ ] | No `console.log` / `print` debug statements; no hardcoded secrets. |
| [ ] | Tag: `git tag v1.0.0-submission && git push --tags`. |
| [ ] | Submitted on Kaggle with repo URL, video URL, writeup URL. |
| [ ] | Local deterministic fallback reports honest `gemma_status` when Ollama is down. |
| [ ] | Desktop Companion can be opened with the global shortcut and can analyze a selected screen/window. |
| [ ] | Bench Mode QR flow can attach measurements and media to an existing session. |
| [ ] | Dataset validation passes with balanced topology distribution and prompt de-duplication. |
| [ ] | Demo smoke script passes across topology seeds, educator overview, and PDF report. |

Last verified at HEAD: pending.
