import { Ionicons } from "@expo/vector-icons";
import * as ImagePicker from "expo-image-picker";
import { StatusBar } from "expo-status-bar";
import { useSpeechRecognitionEvent } from "expo-speech-recognition";
import React, { useEffect, useMemo, useState } from "react";
import {
  ActivityIndicator,
  Image,
  KeyboardAvoidingView,
  Platform,
  Pressable,
  SafeAreaView,
  ScrollView,
  StyleSheet,
  Switch,
  Text,
  TextInput,
  View,
} from "react-native";
import type { CompanionAnalysis } from "./src/types";
import { createOnDeviceEngine } from "./src/onDevice/Engine";
import type { StructuredDiagnosis } from "./src/onDevice/types";
import { abortSpeechRecognition, startSpeechRecognition, stopSpeechRecognition } from "./src/voice/Recorder";
import { speakAnalysis, stopSpeaking } from "./src/voice/Player";

const DEFAULT_API_URL = "http://127.0.0.1:8000";

async function analyzeWithBackend(params: {
  apiUrl: string;
  question: string;
  imageDataUrl?: string;
  appHint: string;
  sessionId?: string;
  saveSnapshot: boolean;
}): Promise<CompanionAnalysis> {
  const response = await fetch(`${params.apiUrl.replace(/\/$/, "")}/api/companion/analyze`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      question: params.question,
      image_data_url: params.imageDataUrl,
      app_hint: params.appHint,
      session_id: params.sessionId || null,
      save_snapshot: params.saveSnapshot,
    }),
  });
  if (!response.ok) {
    throw new Error(await response.text());
  }
  return response.json();
}

function dataUrlToBase64(dataUrl: string) {
  return dataUrl.includes(",") ? dataUrl.split(",", 2)[1] : dataUrl;
}

function structuredToCompanion(diagnosis: StructuredDiagnosis): CompanionAnalysis {
  const topFault = diagnosis.likely_faults[0];
  return {
    mode: diagnosis.gemma_status ?? "on_device_gemma",
    workspace: diagnosis.experiment_type,
    visible_context: diagnosis.observed_behavior.summary,
    answer: diagnosis.student_explanation,
    next_actions: [
      diagnosis.next_measurement.instruction,
      topFault?.verification_test,
      topFault?.fix_recipe,
    ].filter(Boolean) as string[],
    can_click: false,
    safety: diagnosis.safety,
    confidence: diagnosis.confidence,
  };
}

async function uploadVoiceArtifact(apiUrl: string, sessionId: string, uri: string) {
  if (!sessionId || !uri) return;
  const body = new FormData();
  body.append("kind", "audio");
  body.append("file", {
    uri,
    name: `voice-${Date.now()}.caf`,
    type: "audio/x-caf",
  } as unknown as Blob);
  const response = await fetch(`${apiUrl.replace(/\/$/, "")}/api/sessions/${sessionId}/artifacts`, {
    method: "POST",
    body,
  });
  if (!response.ok) throw new Error(await response.text());
}

export default function App() {
  const localEngine = useMemo(() => createOnDeviceEngine("cactus"), []);
  const [apiUrl, setApiUrl] = useState(DEFAULT_API_URL);
  const [question, setQuestion] = useState("Look at this bench photo and tell me what to check next.");
  const [appHint, setAppHint] = useState("electronics_workspace");
  const [sessionId, setSessionId] = useState("");
  const [saveSnapshot, setSaveSnapshot] = useState(true);
  const [localMode, setLocalMode] = useState(false);
  const [localReady, setLocalReady] = useState(false);
  const [localInfo, setLocalInfo] = useState("Gemma 4 E2B local model not checked");
  const [imageDataUrl, setImageDataUrl] = useState<string>("");
  const [imageUri, setImageUri] = useState<string>("");
  const [analysis, setAnalysis] = useState<CompanionAnalysis | null>(null);
  const [busy, setBusy] = useState(false);
  const [recording, setRecording] = useState(false);
  const [voiceUri, setVoiceUri] = useState("");
  const [error, setError] = useState("");

  useEffect(() => {
    let cancelled = false;
    async function refreshLocalModel() {
      try {
        const [ready, info] = await Promise.all([localEngine.ready(), localEngine.modelInfo()]);
        if (!cancelled) {
          setLocalReady(ready);
          setLocalInfo(`${info.name} · ${info.quant}${info.sizeMB ? ` · ${info.sizeMB} MB` : ""}`);
        }
      } catch {
        if (!cancelled) {
          setLocalReady(false);
          setLocalInfo("Gemma 4 E2B bridge or model is not ready");
        }
      }
    }
    if (localMode) {
      refreshLocalModel();
    }
    return () => {
      cancelled = true;
    };
  }, [localEngine, localMode]);

  useSpeechRecognitionEvent("audiostart", (event) => {
    if (event.uri) setVoiceUri(event.uri);
  });

  useSpeechRecognitionEvent("audioend", (event) => {
    setRecording(false);
    const uri = event.uri ?? voiceUri;
    if (uri && sessionId && !localMode) {
      uploadVoiceArtifact(apiUrl, sessionId, uri).catch((exc) => {
        setError(exc instanceof Error ? exc.message : "Voice artifact upload failed.");
      });
    }
  });

  useSpeechRecognitionEvent("result", (event) => {
    const transcript = event.results[0]?.transcript?.trim();
    if (transcript) setQuestion(transcript);
    if (event.isFinal) setRecording(false);
  });

  useSpeechRecognitionEvent("error", (event) => {
    setRecording(false);
    setError(`${event.error}: ${event.message}`);
  });

  async function pickImage(source: "camera" | "library") {
    setError("");
    const permission =
      source === "camera"
        ? await ImagePicker.requestCameraPermissionsAsync()
        : await ImagePicker.requestMediaLibraryPermissionsAsync();
    if (!permission.granted) {
      setError("Permission is required to attach bench evidence.");
      return;
    }
    const result =
      source === "camera"
        ? await ImagePicker.launchCameraAsync({ base64: true, quality: 0.72 })
        : await ImagePicker.launchImageLibraryAsync({ base64: true, quality: 0.72 });
    if (result.canceled || !result.assets[0]) return;
    const asset = result.assets[0];
    setImageUri(asset.uri);
    setImageDataUrl(`data:image/jpeg;base64,${asset.base64 ?? ""}`);
  }

  async function analyze() {
    setBusy(true);
    setError("");
    try {
      const result = localMode
        ? structuredToCompanion(await localEngine.diagnose({
          question,
          measurements: [],
          image_b64: imageDataUrl ? dataUrlToBase64(imageDataUrl) : undefined,
        }))
        : await analyzeWithBackend({
          apiUrl,
          question,
          imageDataUrl,
          appHint,
          sessionId,
          saveSnapshot,
        });
      setAnalysis(result);
      speakAnalysis(result);
    } catch (exc) {
      setError(exc instanceof Error ? exc.message : "Analysis failed.");
    } finally {
      setBusy(false);
    }
  }

  async function startVoice() {
    setError("");
    setRecording(true);
    try {
      await startSpeechRecognition({ offline: localMode });
    } catch (exc) {
      setRecording(false);
      setError(exc instanceof Error ? exc.message : "Voice recording failed.");
    }
  }

  function stopVoice() {
    try {
      stopSpeechRecognition();
    } finally {
      setRecording(false);
    }
  }

  return (
    <SafeAreaView style={styles.safe}>
      <StatusBar style="light" />
      <KeyboardAvoidingView behavior={Platform.OS === "ios" ? "padding" : undefined} style={styles.flex}>
        <ScrollView contentContainerStyle={styles.shell}>
          <View style={styles.header}>
            <View style={styles.pet}>
              <Ionicons name="scan" size={30} color="#07110b" />
            </View>
            <View style={styles.flex}>
              <Text style={styles.eyebrow}>iOS bench buddy</Text>
              <Text style={styles.title}>CircuitSage</Text>
            </View>
          </View>

          <View style={styles.card}>
            <Text style={styles.label}>Laptop backend URL</Text>
            <TextInput value={apiUrl} onChangeText={setApiUrl} style={styles.input} autoCapitalize="none" />
            <Text style={styles.hint}>Use your Mac LAN IP when testing on a physical iPhone.</Text>
            <View style={styles.switchRow}>
              <View style={styles.flex}>
                <Text style={styles.muted}>Local model (offline)</Text>
                <Text style={localReady ? styles.ready : styles.hint}>{localInfo}</Text>
              </View>
              <Switch value={localMode} onValueChange={setLocalMode} trackColor={{ true: "#67f2a9" }} />
            </View>
          </View>

          <View style={styles.card}>
            <Text style={styles.label}>Bench evidence</Text>
            {imageUri ? <Image source={{ uri: imageUri }} style={styles.image} /> : <View style={styles.emptyImage}><Text style={styles.muted}>No photo attached</Text></View>}
            <View style={styles.row}>
              <Pressable style={styles.button} onPress={() => pickImage("camera")}>
                <Ionicons name="camera" size={18} color="#edf7ee" />
                <Text style={styles.buttonText}>Camera</Text>
              </Pressable>
              <Pressable style={styles.button} onPress={() => pickImage("library")}>
                <Ionicons name="images" size={18} color="#edf7ee" />
                <Text style={styles.buttonText}>Library</Text>
              </Pressable>
            </View>
          </View>

          <View style={styles.card}>
            <Text style={styles.label}>Question</Text>
            <TextInput value={question} onChangeText={setQuestion} style={[styles.input, styles.textArea]} multiline />
            <Text style={styles.label}>Workspace hint</Text>
            <TextInput value={appHint} onChangeText={setAppHint} style={styles.input} autoCapitalize="none" />
            <Text style={styles.label}>Session id</Text>
            <TextInput value={sessionId} onChangeText={setSessionId} style={styles.input} autoCapitalize="none" placeholder="optional" placeholderTextColor="#738176" />
            <View style={styles.switchRow}>
              <Text style={styles.muted}>Save snapshot to session</Text>
              <Switch value={saveSnapshot} onValueChange={setSaveSnapshot} trackColor={{ true: "#67f2a9" }} />
            </View>
            <View style={styles.row}>
              <Pressable
                style={[styles.button, recording && styles.recording]}
                onPressIn={startVoice}
                onPressOut={stopVoice}
                onLongPress={() => speakAnalysis(analysis)}
              >
                <Ionicons name={recording ? "mic" : "mic-outline"} size={18} color="#edf7ee" />
                <Text style={styles.buttonText}>{recording ? "Listening" : "Hold to Ask"}</Text>
              </Pressable>
              <Pressable style={styles.button} onPress={() => speakAnalysis(analysis)}>
                <Ionicons name="volume-high" size={18} color="#edf7ee" />
                <Text style={styles.buttonText}>Narrate</Text>
              </Pressable>
              <Pressable style={styles.buttonIcon} onPress={() => { abortSpeechRecognition(); stopSpeaking(); setRecording(false); }}>
                <Ionicons name="stop" size={18} color="#edf7ee" />
              </Pressable>
            </View>
            <Pressable style={[styles.primary, busy && styles.disabled]} onPress={analyze} disabled={busy}>
              {busy ? <ActivityIndicator color="#07110b" /> : <Ionicons name="sparkles" size={18} color="#07110b" />}
              <Text style={styles.primaryText}>{localMode ? "Ask Local Gemma" : "Analyze Bench Evidence"}</Text>
            </Pressable>
            {localMode && !localReady ? <Text style={styles.error}>Local mode is selected, but the native model is not ready. Add the model bundle or turn local mode off.</Text> : null}
            {error ? <Text style={styles.error}>{error}</Text> : null}
          </View>

          <View style={styles.card}>
            <Text style={styles.label}>CircuitSage answer</Text>
            {analysis ? (
              <View style={styles.result}>
                <Text style={styles.resultMeta}>{analysis.mode ?? "analysis"} · {analysis.confidence ?? "unknown"} confidence</Text>
                <Text style={styles.resultTitle}>{analysis.workspace}</Text>
                <Text style={styles.body}>{analysis.visible_context}</Text>
                <Text style={styles.answer}>{analysis.answer}</Text>
                {(analysis.next_actions ?? []).map((action) => <Text style={styles.step} key={action}>• {action}</Text>)}
              </View>
            ) : (
              <Text style={styles.muted}>Capture a photo, ask a question, and send it to your local Gemma backend.</Text>
            )}
          </View>
        </ScrollView>
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: "#0c100e" },
  flex: { flex: 1 },
  shell: { padding: 16, gap: 12 },
  header: { flexDirection: "row", gap: 12, alignItems: "center", marginBottom: 4 },
  pet: { width: 64, height: 64, borderRadius: 32, backgroundColor: "#67f2a9", alignItems: "center", justifyContent: "center" },
  eyebrow: { color: "#67f2a9", textTransform: "uppercase", fontSize: 12, fontWeight: "900" },
  title: { color: "#edf7ee", fontSize: 38, fontWeight: "800" },
  card: { borderWidth: 1, borderColor: "#344238", backgroundColor: "#18201c", padding: 14, gap: 10 },
  label: { color: "#98aa9e", textTransform: "uppercase", fontSize: 12, fontWeight: "900" },
  input: { borderWidth: 1, borderColor: "#344238", backgroundColor: "#0f1512", color: "#edf7ee", minHeight: 44, padding: 10 },
  textArea: { minHeight: 96, textAlignVertical: "top" },
  hint: { color: "#98aa9e", fontSize: 12, lineHeight: 17 },
  ready: { color: "#67f2a9", fontSize: 12, lineHeight: 17 },
  muted: { color: "#98aa9e", lineHeight: 20 },
  row: { flexDirection: "row", gap: 8 },
  button: { flex: 1, minHeight: 44, borderWidth: 1, borderColor: "#344238", flexDirection: "row", alignItems: "center", justifyContent: "center", gap: 8 },
  buttonIcon: { width: 48, minHeight: 44, borderWidth: 1, borderColor: "#344238", alignItems: "center", justifyContent: "center" },
  recording: { borderColor: "#ff5f56", backgroundColor: "#3a1f1d" },
  buttonText: { color: "#edf7ee", fontWeight: "800" },
  primary: { minHeight: 48, backgroundColor: "#67f2a9", flexDirection: "row", alignItems: "center", justifyContent: "center", gap: 8 },
  primaryText: { color: "#07110b", fontWeight: "900" },
  disabled: { opacity: 0.6 },
  image: { width: "100%", height: 240, resizeMode: "contain", backgroundColor: "#050706", borderWidth: 1, borderColor: "#26332c" },
  emptyImage: { height: 160, backgroundColor: "#0f1512", borderWidth: 1, borderColor: "#344238", alignItems: "center", justifyContent: "center" },
  switchRow: { flexDirection: "row", alignItems: "center", justifyContent: "space-between" },
  result: { gap: 8 },
  resultMeta: { color: "#ffbf57", textTransform: "uppercase", fontSize: 11, fontWeight: "900" },
  resultTitle: { color: "#edf7ee", fontSize: 24, fontWeight: "900" },
  body: { color: "#d7e3d8", lineHeight: 21 },
  answer: { color: "#67f2a9", lineHeight: 21, fontWeight: "800" },
  step: { color: "#edf7ee", lineHeight: 21 },
  error: { color: "#ff5f56", lineHeight: 20 },
});
