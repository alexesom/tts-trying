import axios, { type AxiosInstance } from "axios";

import type { LmModelDescriptor, TtsModelDescriptor } from "../../domain/types";

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
}
