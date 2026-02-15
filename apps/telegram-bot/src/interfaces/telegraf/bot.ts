import { Telegraf } from "telegraf";

import { env } from "../../config/env";
import { SqliteRepository } from "../../infrastructure/db/sqliteRepository";

export const buildBot = (): Telegraf => {
  const repo = new SqliteRepository(env.botDbPath);
  const bot = new Telegraf(env.token);

  bot.on("text", async (ctx) => {
    const chatId = String(ctx.chat.id);
    const settings = repo.getSettings(chatId);

    if (!settings) {
      await ctx.reply(
        "Bot initialized. Settings are empty for this chat. Full button UI will be enabled in next step."
      );
      return;
    }

    await ctx.reply("Bot is running. Use the settings menu buttons.");
  });

  return bot;
};
