# Telegram CEO Access

Praetor can use Telegram as a lightweight mobile channel for the owner. It is designed for CEO chat, briefings, mission drafts, and approval notifications. Full setup, API keys, workspace permissions, and high-risk review should stay in the Praetor web UI.

## What Telegram Can Do

- Send messages to the Praetor CEO.
- Run `/briefing`, `/missions`, and `/inbox`.
- Receive approval notifications.
- Reject approvals from Telegram.
- Approve only low-risk approvals when that option is enabled.

Telegram should not be used for API key management, workspace permission changes, or sensitive document review.

## 1. Create A Bot

1. Open Telegram.
2. Message `@BotFather`.
3. Run `/newbot`.
4. Copy the bot token.

Keep the token private. Anyone with the token can control the bot.

## 2. Configure Praetor

Open Praetor:

```text
Settings -> Telegram CEO access
```

Fill in:

- `Bot token`: the token from `@BotFather`.
- `Webhook secret`: a long random string.
- `Allowed Telegram user ID`: recommended. You can get it from `@userinfobot`.
- `Send approval notifications`: enabled if you want Telegram alerts.
- `Allow low-risk approve/reject buttons`: enabled if you want Telegram inline buttons for low-risk decisions.

Save the settings.

## 3. Expose Praetor Over HTTPS

Telegram webhooks require a public HTTPS URL. For local testing, use a tunnel such as Cloudflare Tunnel, ngrok, or another HTTPS reverse proxy.

Example public URL:

```text
https://praetor.example.com
```

Your webhook URL is:

```text
https://praetor.example.com/integrations/telegram/webhook
```

## 4. Set The Telegram Webhook

Replace the values below:

```bash
BOT_TOKEN="123456:replace_me"
WEBHOOK_SECRET="replace_with_the_same_secret_saved_in_praetor"
PRAETOR_URL="https://praetor.example.com"

curl -sS "https://api.telegram.org/bot${BOT_TOKEN}/setWebhook" \
  -H "Content-Type: application/json" \
  -d "{
    \"url\": \"${PRAETOR_URL}/integrations/telegram/webhook\",
    \"secret_token\": \"${WEBHOOK_SECRET}\",
    \"allowed_updates\": [\"message\", \"callback_query\"]
  }"
```

Check the webhook:

```bash
curl -sS "https://api.telegram.org/bot${BOT_TOKEN}/getWebhookInfo"
```

## 5. Pair Your Telegram Account

In Praetor Settings, click `Create pairing code`.

Then message your bot:

```text
/link ABCD1234
```

The pairing code expires after 15 minutes. If it expires, create a new one.

## Commands

```text
/help      Show available commands
/briefing  Show active missions, paused missions, and pending approvals
/missions  Show recent missions
/inbox     Show pending approvals
```

Any non-command message is sent to the Praetor CEO as a chairman instruction.

## Security Notes

- Use `Allowed Telegram user ID` for owner-only access.
- Use a long random webhook secret.
- Keep the bot token private.
- Do not paste API keys or private files into Telegram.
- Review high-risk approvals in the Praetor web UI.
- Telegram is a third-party service, so approval notifications are intentionally summarized.

