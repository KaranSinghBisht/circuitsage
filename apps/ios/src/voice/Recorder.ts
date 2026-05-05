import { ExpoSpeechRecognitionModule } from "expo-speech-recognition";
import type { SpeechRecorderOptions } from "./types";

const CONTEXTUAL_STRINGS = [
  "op amp",
  "inverting amplifier",
  "non-inverting input",
  "LTspice",
  "Tinkercad",
  "MATLAB",
  "oscilloscope",
  "multimeter",
  "voltage divider",
  "collector voltage",
];

export async function startSpeechRecognition(options: SpeechRecorderOptions) {
  const permissions = await ExpoSpeechRecognitionModule.requestPermissionsAsync();
  if (!permissions.granted) {
    throw new Error("Microphone and speech-recognition permissions are required.");
  }
  ExpoSpeechRecognitionModule.start({
    lang: options.lang ?? "en-US",
    interimResults: true,
    maxAlternatives: 1,
    addsPunctuation: true,
    continuous: false,
    requiresOnDeviceRecognition: options.offline,
    contextualStrings: CONTEXTUAL_STRINGS,
    recordingOptions: {
      persist: true,
      outputFileName: `circuitsage_voice_${Date.now()}.caf`,
      outputSampleRate: 16000,
      outputEncoding: "pcmFormatInt16",
    },
  });
}

export function stopSpeechRecognition() {
  ExpoSpeechRecognitionModule.stop();
}

export function abortSpeechRecognition() {
  ExpoSpeechRecognitionModule.abort();
}
