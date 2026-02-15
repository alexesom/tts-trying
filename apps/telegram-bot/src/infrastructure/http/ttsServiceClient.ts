import axios, { type AxiosInstance } from "axios";

import type { LmModelDescriptor, TtsModelDescriptor, UserSettings } from "../../domain/types";

export type JobItem = {
  item_id: string;
  url: string;
  status: string;
  summary?: string;
  filename?: string;
  artifact?: {
    kind: "voice" | "document";
    mime_type: string;
    size_bytes: number;
    download_url: string;
  };
  error?: string;
};

export type JobStatus = {
  job_id: string;
  status: string;
  error_message?: string;
  items: JobItem[];
};

export class TtsServiceClient {
  private readonly http: AxiosInstance;

  public constructor(baseUrl: string) {
    this.http = axios.create({
      baseURL: baseUrl,
      timeout: 30_000
    });
  }

  public async getTtsModels(): Promise<TtsModelDescriptor[]> {
    const response = await this.http.get<{ data: TtsModelDescriptor[] }>("/v1/tts/models");
    return response.data.data;
  }

  public async getLmModels(): Promise<LmModelDescriptor[]> {
    const response = await this.http.get<{ data: LmModelDescriptor[] }>("/v1/lm/models");
    return response.data.data;
  }

  public async validateLmModel(modelId: string): Promise<{ valid: boolean; reason?: string }> {
    const response = await this.http.post<{ valid: boolean; reason?: string }>(
      "/v1/lm/models/validate",
      { model_id: modelId }
    );
    return response.data;
  }

  public async createJob(chatId: string, urls: string[], settings: UserSettings): Promise<string> {
    const response = await this.http.post<{ job_id: string; status: string }>("/v1/jobs", {
      chat_id: chatId,
      urls,
      tts: {
        model_id: settings.ttsModel,
        voice: settings.voice,
        speed: settings.speed
      },
      lm: {
        summary_model_id: settings.lmSummaryModel,
        filename_model_id: settings.lmFilenameModel
      },
      delivery: {
        prefer: "voice",
        fallback: "document"
      }
    });

    return response.data.job_id;
  }

  public async getJob(jobId: string): Promise<JobStatus> {
    const response = await this.http.get<JobStatus>(`/v1/jobs/${jobId}`);
    return response.data;
  }

  public async downloadArtifact(jobId: string, itemId: string): Promise<{ data: Buffer; contentType: string }> {
    const response = await this.http.get<ArrayBuffer>(`/v1/jobs/${jobId}/items/${itemId}/artifact`, {
      responseType: "arraybuffer"
    });

    return {
      data: Buffer.from(response.data),
      contentType: response.headers["content-type"] ?? "application/octet-stream"
    };
  }

  public async acknowledgeSent(jobId: string, itemId: string): Promise<void> {
    await this.http.post(`/v1/jobs/${jobId}/items/${itemId}/ack-sent`);
  }
}
