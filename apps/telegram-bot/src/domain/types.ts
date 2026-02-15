export type UserSettings = {
  chatId: string;
  ttsModel: string;
  voice: string;
  speed: number;
  lmSummaryModel: string;
  lmFilenameModel: string;
  updatedAt: string;
};

export type PendingJob = {
  jobId: string;
  chatId: string;
  status: string;
  createdAt: string;
  updatedAt: string;
};

export type TtsModelDescriptor = {
  id: string;
  label: string;
  languages: string[];
  voice_presets: string[];
  default_voice: string;
  speed_presets: number[];
};

export type LmModelDescriptor = {
  id: string;
};
