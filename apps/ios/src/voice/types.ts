export type SpeechRecorderOptions = {
  offline: boolean;
  lang?: string;
};

export type VoiceArtifact = {
  uri: string;
  transcript?: string;
};
