# Praetor 使用者資料與隱私邊界

日期：2026-04-25

這份文件用來向使用者說清楚 Praetor 會碰哪些資料、資料存在哪裡、哪些情況會離開本機，以及使用者應該如何降低風險。

## 資料存放位置

Praetor 主要使用三類目錄：

- `workspace/`：Wiki、Projects、Missions、Decisions、Meetings、任務輸出。
- `data/`：app state、SQLite index、owner auth hash、audit log、runtime 狀態。
- `config/`：部署設定、executor bridge 設定。

使用 Docker 時，這些目錄通常由 compose bind mount 到主機。使用者可以自行備份、檢查與刪除。

## Praetor 會讀什麼

Praetor 會讀：

- onboarding 時使用者指定的 workspace root。
- `workspace/` 內由 Praetor 建立或任務需要的檔案。
- app state 與 mission/task/run 記錄。
- executor bridge 設定允許的工作目錄。

Praetor 不應讀：

- 使用者整台電腦。
- home directory 中未被指定為 workspace 或 allowed root 的資料。
- denied root 內的資料。

subscription executor mode 需要額外注意：Codex / Claude Code 是宿主機上的外部工具，實際檔案存取能力取決於該工具與 bridge allowed roots 的設定。

## 什麼情況資料會離開本機

資料可能離開本機的情況：

- 使用 `api` mode 並設定 `OPENAI_API_KEY` 或 `ANTHROPIC_API_KEY`。
- 使用者設定外部 API-compatible base URL。
- Host executor 本身會連線到其服務 provider。
- 使用者未來啟用 Telegram、email 或其他 integration。

Praetor 不會在沒有 provider key 或 bridge 設定的情況下，自行把 workspace 上傳到外部服務。

## Secrets

敏感值包括：

- `PRAETOR_SESSION_SECRET`
- `PRAETOR_SETUP_TOKEN`
- `PRAETOR_BRIDGE_TOKEN`
- `OPENAI_API_KEY`
- `ANTHROPIC_API_KEY`
- Telegram token 或其他 integration token

Production 建議使用 Docker secrets 或 `_FILE` 形式注入，不要把真實 secret commit 到 Git。

## 使用者如何刪除資料

停止服務後刪除以下目錄即可移除本機 Praetor 狀態：

```bash
rm -rf ./workspace ./data ./config
```

若使用 Docker secrets，也一併刪除：

```bash
rm -rf ./secrets
```

刪除前請先確認是否需要備份 `workspace/`。

## 建議安全設定

- 本機使用時維持 bind host 為 `127.0.0.1`。
- Production/remote 使用 HTTPS 與 `PRAETOR_SECURE_COOKIE=true`。
- 產生長且隨機的 session/setup/bridge token。
- 不把 executor bridge 綁到公網介面。
- 不把整個 home directory 設成 executor allowed root。
- 定期備份 `workspace/` 和 `data/`。

