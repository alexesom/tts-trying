import Database from "better-sqlite3";

import type { PendingJob, UserSettings } from "../../domain/types";

export class SqliteRepository {
  private readonly db: Database.Database;

  public constructor(path: string) {
    this.db = new Database(path);
    this.initSchema();
  }

  private initSchema(): void {
    this.db.exec(`
      CREATE TABLE IF NOT EXISTS user_settings (
        chat_id TEXT PRIMARY KEY,
        tts_model TEXT NOT NULL,
        voice TEXT NOT NULL,
        speed REAL NOT NULL,
        lm_summary_model TEXT NOT NULL,
        lm_filename_model TEXT NOT NULL,
        updated_at TEXT NOT NULL
      );

      CREATE TABLE IF NOT EXISTS pending_jobs (
        job_id TEXT PRIMARY KEY,
        chat_id TEXT NOT NULL,
        status TEXT NOT NULL,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL
      );
    `);
  }

  public getSettings(chatId: string): UserSettings | undefined {
    const row = this.db
      .prepare(
        `
        SELECT
          chat_id as chatId,
          tts_model as ttsModel,
          voice,
          speed,
          lm_summary_model as lmSummaryModel,
          lm_filename_model as lmFilenameModel,
          updated_at as updatedAt
        FROM user_settings
        WHERE chat_id = ?
        `
      )
      .get(chatId) as UserSettings | undefined;
    return row;
  }

  public upsertSettings(settings: Omit<UserSettings, "updatedAt">): void {
    const now = new Date().toISOString();
    this.db
      .prepare(
        `
        INSERT INTO user_settings (
          chat_id,
          tts_model,
          voice,
          speed,
          lm_summary_model,
          lm_filename_model,
          updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(chat_id) DO UPDATE SET
          tts_model=excluded.tts_model,
          voice=excluded.voice,
          speed=excluded.speed,
          lm_summary_model=excluded.lm_summary_model,
          lm_filename_model=excluded.lm_filename_model,
          updated_at=excluded.updated_at
        `
      )
      .run(
        settings.chatId,
        settings.ttsModel,
        settings.voice,
        settings.speed,
        settings.lmSummaryModel,
        settings.lmFilenameModel,
        now
      );
  }

  public upsertPendingJob(job: Omit<PendingJob, "createdAt" | "updatedAt">): void {
    const now = new Date().toISOString();
    this.db
      .prepare(
        `
        INSERT INTO pending_jobs (job_id, chat_id, status, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(job_id) DO UPDATE SET
          status=excluded.status,
          updated_at=excluded.updated_at
        `
      )
      .run(job.jobId, job.chatId, job.status, now, now);
  }

  public deletePendingJob(jobId: string): void {
    this.db.prepare(`DELETE FROM pending_jobs WHERE job_id = ?`).run(jobId);
  }
}
