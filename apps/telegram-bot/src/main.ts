import { env } from "./config/env";
import { buildBot } from "./interfaces/telegraf/bot";

const bot = buildBot();

bot
  .launch({
    webhook: {
      domain: env.webhookDomain,
      port: env.webhookPort,
      path: env.webhookPath,
      secretToken: env.webhookSecret || undefined
    }
  })
  .then(() => {
    // eslint-disable-next-line no-console
    console.log(`Telegram bot started on webhook ${env.webhookDomain}${env.webhookPath}`);
  })
  .catch((error: unknown) => {
    // eslint-disable-next-line no-console
    console.error("Failed to start Telegram bot", error);
    process.exit(1);
  });

process.once("SIGINT", () => bot.stop("SIGINT"));
process.once("SIGTERM", () => bot.stop("SIGTERM"));
