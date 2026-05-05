# CircuitSage iOS Bench Companion

Pinned runtime:

- Expo: `~55.0.23`
- React Native: `0.83.6`
- Cactus bridge: `cactus-react-native@1.13.1`
- MediaPipe bridge fallback: `expo-llm-mediapipe@0.6.0`
- Voice input: `expo-speech-recognition@3.1.3`
- Voice output: `expo-speech@55.0.13`

Verification:

```bash
npm view react-native@0.83.6 version
npx expo install --check
npm --prefix apps/ios install
npm --prefix apps/ios run check
```

`react-native@0.83.6` is published on npm and is the Expo SDK 55-compatible pin used by this workspace.

## On-Device Model

The bench app has a `Local model (offline)` mode that targets Gemma 4 E2B on device. The actual model bundle is a user action and is not committed. See [assets/models/README.md](assets/models/README.md).

Physical demo steps:

1. Build a development client with the native bridge installed.
2. Provision `gemma-4-E2B-it` through Cactus or add `gemma-4-E2B-it.task` for MediaPipe.
3. Launch the app once with the model available.
4. Enable `Local model (offline)`, switch the iPhone to airplane mode, ask: `My inverting op-amp is stuck near +12 V. What should I check?`

If the model is missing, the app reports that local inference is not ready instead of using the server path silently.

## Voice

Hold the mic button to dictate a question. The app uses system speech recognition first and saves the persisted recording as an `audio` artifact when a LAN session id is selected. Answers are spoken back with Expo Speech. Long-press the mic or tap `Narrate` to read the latest diagnosis aloud.

Physical validation is required on an iPhone development client because Expo Go cannot load every native bridge used here.
