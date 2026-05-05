import * as Speech from "expo-speech";
import type { CompanionAnalysis } from "../types";

export function speakText(text: string) {
  Speech.stop();
  Speech.speak(text.slice(0, Speech.maxSpeechInputLength), {
    rate: 0.96,
    pitch: 1.0,
  });
}

export function speakAnalysis(analysis: CompanionAnalysis | null) {
  if (!analysis) {
    speakText("No diagnosis is available yet.");
    return;
  }
  const next = analysis.next_actions?.[0] ? ` Next: ${analysis.next_actions[0]}` : "";
  speakText(`${analysis.answer}${next}`);
}

export function stopSpeaking() {
  return Speech.stop();
}
