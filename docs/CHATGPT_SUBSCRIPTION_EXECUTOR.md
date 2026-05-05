# ChatGPT Subscription Executor

Praetor supports ChatGPT subscription-based execution through the official Codex CLI and the host-side `praetor-execd` bridge.

This is different from API mode:

- API mode uses provider API keys.
- Subscription executor mode uses a local Codex CLI login tied to the user's ChatGPT account.
- Praetor does not store a ChatGPT password or browser session.

## Setup Flow

1. Install the official Codex CLI on the host machine.
2. Run:

   ```bash
   codex login
   ```

3. Choose **Sign in with ChatGPT** in the Codex CLI flow.
4. Start `praetor-execd` on the host with:

   - a strong bridge token
   - `host_workspace_root` pointing to the Praetor workspace
   - `codex` enabled in the bridge config

5. In Praetor, open **Models & API**.
6. Select **Subscription executor**.
7. Set executor to `codex`.
8. Click **Test connection**.

## Current Product Boundary

Praetor does not directly complete the ChatGPT browser login inside the web app. The authentication happens in Codex CLI on the host, then Praetor detects the result through the executor bridge.

This keeps ChatGPT credentials outside Praetor and avoids storing browser tokens in the app state.

Reference: [Using Codex with your ChatGPT plan](https://help.openai.com/en/articles/11369540).
