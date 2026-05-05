<p align="center">
  <img src="./branding/praetor-logo-dark.png" alt="Praetor logo" width="360" />
</p>

# Praetor

[![CI](https://github.com/chaochungkuo/praetor/actions/workflows/ci.yml/badge.svg)](https://github.com/chaochungkuo/praetor/actions/workflows/ci.yml)
[![Docker Build](https://github.com/chaochungkuo/praetor/actions/workflows/docker-build.yml/badge.svg)](https://github.com/chaochungkuo/praetor/actions/workflows/docker-build.yml)
[![CodeQL](https://github.com/chaochungkuo/praetor/actions/workflows/codeql.yml/badge.svg)](https://github.com/chaochungkuo/praetor/actions/workflows/codeql.yml)
[![Pages](https://github.com/chaochungkuo/praetor/actions/workflows/pages.yml/badge.svg)](https://chaochungkuo.github.io/praetor/)
[![OpenSSF Scorecard](https://api.securityscorecards.dev/projects/github.com/chaochungkuo/praetor/badge)](https://securityscorecards.dev/viewer/?uri=github.com/chaochungkuo/praetor)

Praetor is a local-first AI company operating system for solo founders. You talk to an AI CEO, set approval boundaries, and let Praetor organize missions, company memory, AI roles, delegation, review, and escalation.

## Quick Install

Install and start Praetor locally with one command:

```bash
curl -fsSL https://raw.githubusercontent.com/chaochungkuo/praetor/main/scripts/install.sh | bash
```

Then open the setup URL printed in your terminal. The installer creates:

- a private app state folder at `~/.praetor/data`
- a private workspace at `~/praetor-workspace`
- a local Docker app at `http://127.0.0.1:9741`
- a one-time setup token for first-run onboarding

On first launch, Praetor guides you through owner account creation, optional API key setup, workspace selection, and approval rules. If you do not have an API key ready, skip it and add it later from **Models & API**.

## Optional: Use Local Codex Instead of an API Key

If you already use Codex CLI with your ChatGPT subscription, connect it with:

```bash
~/.praetor/praetor/scripts/configure-codex-executor.sh
```

Then open **Models & API**, choose **Local subscription tool**, select **Codex CLI**, and click **Test connection**. This keeps ChatGPT authentication inside Codex CLI; Praetor only talks to a local `praetor-execd` bridge.

## Safer Manual Install

If you prefer to inspect the installer before running it:

```bash
curl -fsSLO https://raw.githubusercontent.com/chaochungkuo/praetor/main/scripts/install.sh
less install.sh
bash install.sh
```

## Update

```bash
~/.praetor/praetor/scripts/update.sh
```

## Uninstall

Remove the app but keep your data and workspace:

```bash
~/.praetor/praetor/scripts/uninstall.sh
```

Remove the app, local state, and workspace:

```bash
~/.praetor/praetor/scripts/uninstall.sh --purge
```

## Requirements

- Docker Desktop or Docker Engine
- Git
- macOS, Linux, or Windows with WSL 2

Praetor runs locally by default. It does not expose the app publicly unless you change the bind host or deploy it yourself.

## Optional Telegram CEO Access

Praetor can connect a Telegram bot as an owner-only mobile channel for CEO chat, briefings, and approval notifications. Configure it from **Settings -> Telegram CEO access** after first-run onboarding.

Short version:

1. Create a Telegram bot with `@BotFather`.
2. Paste the bot token and a long webhook secret into Praetor Settings.
3. Expose Praetor over HTTPS and set Telegram's webhook to `https://YOUR_DOMAIN/integrations/telegram/webhook`.
4. Generate a pairing code in Praetor and send `/link CODE` to your bot from your Telegram account.

See [docs/TELEGRAM_SETUP.md](docs/TELEGRAM_SETUP.md) for the exact commands and safety notes.

## For Developers

Developer setup, Pixi commands, smoke tests, bridge development, and source workflows live in:

- [docs/DEVELOPER_SETUP.md](docs/DEVELOPER_SETUP.md)
- [docs/ADVANCED_DEPLOYMENT.md](docs/ADVANCED_DEPLOYMENT.md)
- [docs/INSTALL_CHECKLIST.md](docs/INSTALL_CHECKLIST.md)

## Documentation

- [GitHub Pages documentation site](https://chaochungkuo.github.io/praetor/)
- [Public security review](docs/PRAETOR_PUBLIC_SECURITY_REVIEW.zh-TW.md)
- [Privacy boundaries](docs/PRAETOR_PRIVACY_BOUNDARIES.zh-TW.md)
- [Backup and restore](docs/PRAETOR_BACKUP_RESTORE.md)
- [Roadmap](ROADMAP.md)

## Current Status

Praetor is still an active build-stage repo, not a finished consumer release. The one-line installer is intended to make local evaluation simple while keeping advanced deployment and development details out of the first-run path.
