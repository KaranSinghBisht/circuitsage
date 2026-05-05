# CircuitSage On-Device Models

The iOS app is wired for a local Gemma 4 E2B path, but the model binary is intentionally not committed.

Verified bridge packages:

- `cactus-react-native@1.13.1`
- `expo-llm-mediapipe@0.6.0`

User action before a physical airplane-mode demo:

1. Download or export a Gemma 4 E2B instruction model for the selected bridge.
2. For Cactus, provision `gemma-4-E2B-it` through the Cactus model registry or a local `.gguf` path supported by the bridge.
3. For MediaPipe, add `gemma-4-E2B-it.task` to the native bundle or download it once before airplane mode.
4. Build a development client; Expo Go cannot load arbitrary native inference bridges.
5. Open the app, enable `Local model (offline)`, switch the phone to airplane mode, and ask the op-amp demo question.

The app does not silently fall back to the LAN backend when local mode is enabled. If the bridge or model is missing, it reports that the local model is not ready.
