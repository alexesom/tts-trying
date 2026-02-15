import { mkdtempSync, rmSync } from "node:fs";
import { join } from "node:path";
import { tmpdir } from "node:os";

import { describe, expect, it } from "vitest";

import { SqliteRepository } from "../src/infrastructure/db/sqliteRepository";

describe("SqliteRepository", () => {
  it("upserts and reads settings", () => {
    const dir = mkdtempSync(join(tmpdir(), "bot-db-"));
    const dbPath = join(dir, "test.db");

    const repo = new SqliteRepository(dbPath);
    repo.upsertSettings({
      chatId: "123",
      ttsModel: "m1",
      voice: "v1",
      speed: 1.0,
      lmSummaryModel: "lm1",
      lmFilenameModel: "lm2"
    });

    const row = repo.getSettings("123");
    expect(row?.ttsModel).toBe("m1");
    expect(row?.voice).toBe("v1");

    rmSync(dir, { recursive: true, force: true });
  });
});
