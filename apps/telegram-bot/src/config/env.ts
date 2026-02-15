import dotenv from "dotenv";

dotenv.config({ path: "/Users/alex/Documents/tts-trying/.env" });

type Env = {
  token: string;
  webhookDomain: string;
  webhookPort: number;
  webhookPath: string;
  webhookSecret: string;
  ttsServiceBaseUrl: string;
  botDbPath: string;
};

const required = (value: string | undefined, key: string): string => {
  if (!value || !value.trim()) {
    throw new Error(`Missing required env var: ${key}`);
  }
  return value;
};

export const env: Env = {
  token: required(process.env.TELEGRAM_BOT_TOKEN, "TELEGRAM_BOT_TOKEN"),
  webhookDomain: required(process.env.TELEGRAM_WEBHOOK_DOMAIN, "TELEGRAM_WEBHOOK_DOMAIN"),
  webhookPort: Number(process.env.TELEGRAM_WEBHOOK_PORT ?? 3000),
  webhookPath: process.env.TELEGRAM_WEBHOOK_PATH ?? "/telegram/webhook",
  webhookSecret: process.env.TELEGRAM_WEBHOOK_SECRET ?? "",
  ttsServiceBaseUrl: process.env.TTS_SERVICE_BASE_URL ?? "http://127.0.0.1:8000",
  botDbPath: process.env.BOT_DB_PATH ?? "/Users/alex/Documents/tts-trying/apps/telegram-bot/data/bot.db"
};
