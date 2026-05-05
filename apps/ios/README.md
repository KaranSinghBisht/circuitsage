# CircuitSage iOS Bench Companion

Pinned runtime:

- Expo: `~55.0.20`
- React Native: `0.83.6`

Verification:

```bash
npm view react-native@0.83.6 version
npx expo install --check
npm --prefix apps/ios install
npm --prefix apps/ios run check
```

`react-native@0.83.6` is published on npm and is the Expo SDK 55-compatible pin used by this workspace.
