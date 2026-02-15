import { Markup, Telegraf } from "telegraf";

import { env } from "../../config/env";
import { extractUrls } from "../../application/url";
import type { TtsModelDescriptor, UserSettings } from "../../domain/types";
import { SqliteRepository } from "../../infrastructure/db/sqliteRepository";
import { TtsServiceClient, type JobStatus } from "../../infrastructure/http/ttsServiceClient";

const MAIN_MENU = [
  ["Select TTS Model"],
  ["Select Voice"],
  ["Select Speed"],
  ["Select LM Summary Model"],
  ["Select LM Filename Model"],
  ["Show Current Settings"]
];

type MenuCache = {
  ttsModels: TtsModelDescriptor[];
  lmModels: string[];
};

const DEFAULT_SPEEDS = [0.8, 1.0, 1.2, 1.4] as const;
const TERMINAL_STATUSES = new Set(["completed", "partial_failed", "failed", "cancelled"]);

const sleep = async (ms: number): Promise<void> =>
  new Promise((resolve) => {
    setTimeout(resolve, ms);
  });

export const buildBot = (): Telegraf => {
  const repo = new SqliteRepository(env.botDbPath);
  const ttsService = new TtsServiceClient(env.ttsServiceBaseUrl);

  const bot = new Telegraf(env.token);
  const menuCache = new Map<string, MenuCache>();
  const awaitingCustomVoice = new Set<string>();

  const ensureSettings = async (chatId: string): Promise<UserSettings> => {
    const existing = repo.getSettings(chatId);
    if (existing) return existing;

    const [ttsModels, lmModels] = await Promise.all([ttsService.getTtsModels(), ttsService.getLmModels()]);
    if (!ttsModels.length) throw new Error("No TTS models available from API");
    if (!lmModels.length) throw new Error("No LM models available from API");

    const defaultModel = ttsModels[0];
    const settings: Omit<UserSettings, "updatedAt"> = {
      chatId,
      ttsModel: defaultModel.id,
      voice: defaultModel.default_voice,
      speed: 1.0,
      lmSummaryModel: lmModels[0].id,
      lmFilenameModel: lmModels[0].id
    };

    repo.upsertSettings(settings);
    return repo.getSettings(chatId)!;
  };

  const getCache = async (chatId: string): Promise<MenuCache> => {
    const cached = menuCache.get(chatId);
    if (cached) return cached;

    const [ttsModels, lmModels] = await Promise.all([ttsService.getTtsModels(), ttsService.getLmModels()]);
    const value: MenuCache = { ttsModels, lmModels: lmModels.map((item) => item.id) };
    menuCache.set(chatId, value);
    return value;
  };

  const menuKeyboard = Markup.keyboard(MAIN_MENU).resize();

  const deliverCompletedItems = async (
    chatId: string,
    jobId: string,
    status: JobStatus,
    delivered: Set<string>
  ): Promise<void> => {
    for (const item of status.items) {
      if (item.status !== "completed" || !item.artifact || delivered.has(item.item_id)) {
        continue;
      }

      const artifact = await ttsService.downloadArtifact(jobId, item.item_id);
      const summary = item.summary?.slice(0, 1024);
      const fileBase = item.filename || item.item_id;

      if (item.artifact.kind === "voice") {
        await bot.telegram.sendVoice(
          chatId,
          {
            source: artifact.data,
            filename: `${fileBase}.ogg`
          },
          {
            caption: summary
          }
        );
      } else {
        await bot.telegram.sendDocument(
          chatId,
          {
            source: artifact.data,
            filename: `${fileBase}.mp3`
          },
          {
            caption: summary
          }
        );
      }

      await ttsService.acknowledgeSent(jobId, item.item_id);
      delivered.add(item.item_id);
    }
  };

  const pollAndDeliver = async (chatId: string, jobId: string): Promise<void> => {
    const delivered = new Set<string>();
    let rounds = 0;

    while (rounds < 240) {
      const status = await ttsService.getJob(jobId);
      repo.upsertPendingJob({ jobId, chatId, status: status.status });

      await deliverCompletedItems(chatId, jobId, status, delivered);

      if (TERMINAL_STATUSES.has(status.status)) {
        const failed = status.items.filter((item) => item.status === "failed");
        if (failed.length) {
          const failedLines = failed
            .slice(0, 5)
            .map((item) => `- ${item.url}: ${item.error ?? "processing error"}`)
            .join("\n");
          await bot.telegram.sendMessage(chatId, `Some URLs failed:\n${failedLines}`);
        }

        if (!failed.length && status.status === "completed") {
          await bot.telegram.sendMessage(chatId, "All audio files were generated and sent.");
        }

        repo.deletePendingJob(jobId);
        return;
      }

      rounds += 1;
      await sleep(3_000);
    }

    repo.deletePendingJob(jobId);
    await bot.telegram.sendMessage(chatId, "Job timed out while polling status.");
  };

  bot.on("text", async (ctx) => {
    const chatId = String(ctx.chat.id);
    const text = (ctx.message.text ?? "").trim();

    try {
      const settings = await ensureSettings(chatId);

      if (awaitingCustomVoice.has(chatId)) {
        if (text.length < 1 || text.length > 120) {
          await ctx.reply("Custom voice must be 1..120 chars.", menuKeyboard);
          return;
        }

        repo.upsertSettings({
          chatId,
          ttsModel: settings.ttsModel,
          voice: text,
          speed: settings.speed,
          lmSummaryModel: settings.lmSummaryModel,
          lmFilenameModel: settings.lmFilenameModel
        });
        awaitingCustomVoice.delete(chatId);
        await ctx.reply(`Custom voice saved: ${text}`, menuKeyboard);
        return;
      }

      switch (text) {
        case "Select TTS Model": {
          const cache = await getCache(chatId);
          const rows = cache.ttsModels.map((model, index) => [
            Markup.button.callback(`${model.label} [${model.languages.join(",")}]`, `tts_model:${index}`)
          ]);
          await ctx.reply("Choose TTS model:", Markup.inlineKeyboard(rows));
          return;
        }
        case "Select Voice": {
          const cache = await getCache(chatId);
          const model = cache.ttsModels.find((item) => item.id === settings.ttsModel) ?? cache.ttsModels[0];
          const rows = model.voice_presets.map((voice) => [
            Markup.button.callback(voice, `voice_preset:${encodeURIComponent(voice)}`)
          ]);
          rows.push([Markup.button.callback("Custom voice", "voice_custom")]);
          await ctx.reply(`Choose voice for ${model.label}:`, Markup.inlineKeyboard(rows));
          return;
        }
        case "Select Speed": {
          const rows = DEFAULT_SPEEDS.map((speed) => [Markup.button.callback(String(speed), `speed:${speed}`)]);
          await ctx.reply("Choose speed:", Markup.inlineKeyboard(rows));
          return;
        }
        case "Select LM Summary Model": {
          const cache = await getCache(chatId);
          const rows = cache.lmModels.map((model, index) => [
            Markup.button.callback(model, `lm_summary:${index}`)
          ]);
          await ctx.reply("Choose LM summary model:", Markup.inlineKeyboard(rows));
          return;
        }
        case "Select LM Filename Model": {
          const cache = await getCache(chatId);
          const rows = cache.lmModels.map((model, index) => [
            Markup.button.callback(model, `lm_filename:${index}`)
          ]);
          await ctx.reply("Choose LM filename model:", Markup.inlineKeyboard(rows));
          return;
        }
        case "Show Current Settings": {
          await ctx.reply(
            [
              `TTS model: ${settings.ttsModel}`,
              `Voice: ${settings.voice}`,
              `Speed: ${settings.speed}`,
              `LM summary model: ${settings.lmSummaryModel}`,
              `LM filename model: ${settings.lmFilenameModel}`
            ].join("\n"),
            menuKeyboard
          );
          return;
        }
        default: {
          const urls = extractUrls(text);
          if (!urls.length) {
            await ctx.reply(
              "Send one or more URLs to start TTS generation, or use menu buttons to change settings.",
              menuKeyboard
            );
            return;
          }

          await ctx.reply(`Accepted ${urls.length} URL(s). Creating TTS job...`, menuKeyboard);
          const jobId = await ttsService.createJob(chatId, urls, settings);
          repo.upsertPendingJob({ jobId, chatId, status: "queued" });

          void pollAndDeliver(chatId, jobId).catch(async (error: unknown) => {
            repo.deletePendingJob(jobId);
            await bot.telegram.sendMessage(chatId, `Job failed: ${(error as Error).message}`);
          });
          return;
        }
      }
    } catch (error) {
      await ctx.reply(`Error: ${(error as Error).message}`, menuKeyboard);
    }
  });

  bot.action(/^tts_model:(\d+)$/, async (ctx) => {
    const chatId = String(ctx.chat?.id ?? "");
    const index = Number(ctx.match[1]);
    const cache = await getCache(chatId);
    const chosen = cache.ttsModels[index];
    if (!chosen) {
      await ctx.answerCbQuery("Model not found");
      return;
    }

    const settings = await ensureSettings(chatId);
    repo.upsertSettings({
      chatId,
      ttsModel: chosen.id,
      voice: chosen.default_voice,
      speed: settings.speed,
      lmSummaryModel: settings.lmSummaryModel,
      lmFilenameModel: settings.lmFilenameModel
    });

    await ctx.answerCbQuery("TTS model updated");
    await ctx.editMessageText(`TTS model set: ${chosen.label} [${chosen.languages.join(",")}]`);
  });

  bot.action(/^voice_preset:(.+)$/, async (ctx) => {
    const chatId = String(ctx.chat?.id ?? "");
    const voice = decodeURIComponent(ctx.match[1]);
    const settings = await ensureSettings(chatId);

    repo.upsertSettings({
      chatId,
      ttsModel: settings.ttsModel,
      voice,
      speed: settings.speed,
      lmSummaryModel: settings.lmSummaryModel,
      lmFilenameModel: settings.lmFilenameModel
    });

    awaitingCustomVoice.delete(chatId);
    await ctx.answerCbQuery("Voice updated");
    await ctx.editMessageText(`Voice set: ${voice}`);
  });

  bot.action("voice_custom", async (ctx) => {
    const chatId = String(ctx.chat?.id ?? "");
    awaitingCustomVoice.add(chatId);
    await ctx.answerCbQuery("Send custom voice text");
    await ctx.editMessageText("Send your custom voice value in the next message.");
  });

  bot.action(/^speed:(0\.8|1|1\.0|1\.2|1\.4)$/, async (ctx) => {
    const chatId = String(ctx.chat?.id ?? "");
    const speed = Number(ctx.match[1]);
    const settings = await ensureSettings(chatId);

    repo.upsertSettings({
      chatId,
      ttsModel: settings.ttsModel,
      voice: settings.voice,
      speed,
      lmSummaryModel: settings.lmSummaryModel,
      lmFilenameModel: settings.lmFilenameModel
    });

    await ctx.answerCbQuery("Speed updated");
    await ctx.editMessageText(`Speed set: ${speed}`);
  });

  bot.action(/^lm_summary:(\d+)$/, async (ctx) => {
    const chatId = String(ctx.chat?.id ?? "");
    const index = Number(ctx.match[1]);
    const cache = await getCache(chatId);
    const modelId = cache.lmModels[index];
    if (!modelId) {
      await ctx.answerCbQuery("Model not found");
      return;
    }

    const validation = await ttsService.validateLmModel(modelId);
    if (!validation.valid) {
      await ctx.answerCbQuery("Invalid model");
      await ctx.editMessageText(`Model rejected: ${modelId}\n${validation.reason ?? "Validation failed"}`);
      return;
    }

    const settings = await ensureSettings(chatId);
    repo.upsertSettings({
      chatId,
      ttsModel: settings.ttsModel,
      voice: settings.voice,
      speed: settings.speed,
      lmSummaryModel: modelId,
      lmFilenameModel: settings.lmFilenameModel
    });

    await ctx.answerCbQuery("Summary model updated");
    await ctx.editMessageText(`LM summary model set: ${modelId}`);
  });

  bot.action(/^lm_filename:(\d+)$/, async (ctx) => {
    const chatId = String(ctx.chat?.id ?? "");
    const index = Number(ctx.match[1]);
    const cache = await getCache(chatId);
    const modelId = cache.lmModels[index];
    if (!modelId) {
      await ctx.answerCbQuery("Model not found");
      return;
    }

    const validation = await ttsService.validateLmModel(modelId);
    if (!validation.valid) {
      await ctx.answerCbQuery("Invalid model");
      await ctx.editMessageText(`Model rejected: ${modelId}\n${validation.reason ?? "Validation failed"}`);
      return;
    }

    const settings = await ensureSettings(chatId);
    repo.upsertSettings({
      chatId,
      ttsModel: settings.ttsModel,
      voice: settings.voice,
      speed: settings.speed,
      lmSummaryModel: settings.lmSummaryModel,
      lmFilenameModel: modelId
    });

    await ctx.answerCbQuery("Filename model updated");
    await ctx.editMessageText(`LM filename model set: ${modelId}`);
  });

  bot.on("callback_query", async (ctx) => {
    await ctx.answerCbQuery();
  });

  return bot;
};
