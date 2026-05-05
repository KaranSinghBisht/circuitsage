# CircuitSage: Stack Traces for Circuits

CircuitSage is an offline Gemma-powered lab partner that follows electronics students from simulation to oscilloscope.

Software students get stack traces. Electronics students get silence. A broken circuit often gives a flat oscilloscope trace, a saturated output, heat, smoke, or no signal at all. In crowded labs, one instructor cannot mentor every student at the exact moment their hardware fails.

CircuitSage turns that silent failure into a structured debugging path. The PC Studio stores the lab manual, netlist, waveform data, and diagnosis timeline. Mobile Bench Mode lets a student upload oscilloscope or breadboard photos and enter multimeter readings from the lab bench.

The demo uses an inverting op-amp amplifier. The simulation expects gain -4.7, but the bench output is saturated near +12 V. CircuitSage parses the netlist, analyzes the observed waveform, checks safety, retrieves the lab manual reminder that the non-inverting input must be grounded, and asks for the next measurement. When the student enters `V_noninv = 2.8 V`, CircuitSage identifies the floating reference input and explains why the gain formula was not the real problem.

Gemma is used locally through Ollama for natural-language reasoning and structured diagnosis. Deterministic tools provide grounding: netlist parsing, waveform analysis, expected-vs-observed comparison, safety refusal, manual retrieval, and report generation. If Ollama is unavailable, the deterministic fallback still demonstrates the workflow.

The impact is practical engineering education. Hardware skills are needed for energy, robotics, medical devices, climate sensors, infrastructure, and repair economies, but bench mentorship is scarce. CircuitSage helps students learn the debugging process, not just the final answer.

Safety and trust are built into the product. CircuitSage is limited to low-voltage educational circuits and refuses live mains or high-voltage debugging. It shows evidence, admits uncertainty, and asks for measurements before making strong claims.

Future work includes more circuit types, stronger image understanding, real LTspice/MATLAB integrations, mobile on-device inference with Cactus or LiteRT, and fine-tuned fault diagnosis.

