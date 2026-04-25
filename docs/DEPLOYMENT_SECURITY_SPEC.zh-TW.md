# Praetor 部署與安全規格 v0.1

狀態：設計稿

這份文件定義 Praetor 的部署模式、容器拓樸、網路安全邊界、資料持久化、備份還原、secrets 管理，以及如何在 **不把 Codex / Claude Code 再裝進 Docker** 的前提下，讓 Praetor 使用宿主機已登入的 coding executors。

## 1. 設計目標

Praetor 的部署層要同時滿足：

1. 一鍵部署容易
2. 本機模式安全且可直接使用
3. 遠端模式有清楚的網路與登入邊界
4. 重要資料可持久化、可備份、可還原
5. subscription executor mode 可使用宿主機既有工具
6. 不把高風險能力直接暴露到 Docker 內部或公網

## 2. 支援的部署模式

Praetor 應官方支援三種模式：

| 模式 | 適用場景 | 預設暴露面 | 推薦程度 |
|---|---|---|---|
| Local-only | 個人電腦、單機、自用 | `127.0.0.1:3000` | 最高 |
| Remote private | VPS / NAS / home server，限本人或內網 | `443` 經反向代理 | 高 |
| Remote public | 對外公開網域 | `443` 經反向代理 | 進階 |

### 2.1 Local-only

這是 Praetor v1 的預設模式。

特性：
- 只綁定 `127.0.0.1`
- 不必先處理複雜的公網暴露問題
- 最適合 subscription executor mode
- 最容易支援 host-installed Codex / Claude Code

### 2.2 Remote private

特性：
- 部署在自己控制的主機
- 透過 HTTPS、登入、反向代理存取
- 可以從外部瀏覽器使用，但不應裸露內部服務

### 2.3 Remote public

特性：
- 可以對外提供穩定入口
- 必須補齊完整安全措施
- 不應作為 MVP 預設

## 2.4 v1 正式支援矩陣

Praetor v1 建議把支援範圍直接寫死：

| Deployment mode | API mode | Local model mode | Subscription executor mode |
|---|---|---|---|
| Local-only | 正式支援 | 正式支援 | 正式支援 |
| Remote private | 正式支援 | 條件支援 | 條件支援 |
| Remote public | 正式支援 | 進階支援 | 不列為正式支援 |

說明：
- `Remote private` 的 `subscription_executor` 僅限 owner 自己控制主機、能自行登入並維護 CLI
- `Remote public + subscription_executor` 不應作為 v1 官方主打路線

## 2.5 官方安裝路線

### Quick Start

目標：
- 最低摩擦啟動
- 使用者先體驗 Praetor 本體

建議：
- 純 Docker
- 預設使用 `api` 或 `local_model`

### Bring Your Own Subscription

目標：
- 沿用使用者已登入的 Codex / Claude Code

建議：
- Docker 跑 Praetor
- 宿主機額外跑 `praetor-execd`
- 僅作為 `Local-only` 或 owner-controlled `Remote private` 正式路線

## 3. 容器拓樸

Praetor 建議至少拆成三個容器服務：

- `web`
- `api`
- `worker`

生產模式再加：

- `proxy`

可選：

- `ollama`

重要的是：

- 只有 `web` 或 `proxy` 可以對外暴露
- `api` 不直接 publish port
- `worker` 不直接 publish port
- subscription executor 不應直接跑在容器裡

### 3.1 推薦拓樸

```txt
Browser / Mobile / Telegram
        ↓
      proxy (prod only)
        ↓
        web
        ↓
        api
        ↓
      worker
        ↓
workspace / config / data
        ↓
host executor bridge (outside Docker)
        ↓
Codex / Claude Code on host
```

## 4. 資料持久化與目錄策略

Praetor 的重要資料不應放在容器可寫層。

應至少拆成三類：

- `workspace/`
- `config/`
- `data/`

### 4.1 `workspace/`

用途：
- Wiki
- Projects
- Missions
- Decisions
- Inbox
- Deliverables

建議：
- 使用 bind mount
- 讓使用者可直接看見檔案
- 作為最優先備份目標

### 4.2 `config/`

用途：
- app settings
- governance settings
- executor configuration
- deployment-specific config

建議：
- 使用 bind mount
- 不把真正 secrets 明文長期放在這裡

### 4.3 `data/`

用途：
- SQLite
- session state
- run state
- usage metrics
- structured logs
- audit traces

建議：
- 可用 bind mount 或 named volume
- 若要簡單備份與人工檢查，優先 bind mount

## 5. 網路安全邊界

Praetor 的網路安全原則很簡單：

**只有入口服務可以對外，其他服務全部留在 Docker 內部網路。**

### 5.1 Local-only 模式

建議：

- `web` 綁 `127.0.0.1:3000`
- `api` 僅 `expose`
- `worker` 不開 port

### 5.2 Remote 模式

建議：

- 用 `proxy` 對外提供 `80/443`
- `web` 仍只在 Docker 內部網路可見，或只綁主機 localhost
- `api` / `worker` 一律不對外

### 5.3 絕對不應做的事

- 不要直接把 `api` 公開到網路
- 不要直接把 `worker` 公開到網路
- 不要把 Docker socket 掛進 Praetor 容器
- 不要讓 executor bridge 對外監聽公網介面

## 6. 認證、登入與 session

### 6.1 Local-only

Local-only 可支援較輕的 owner 體驗，但仍建議至少保留：

- owner account
- session 管理
- logout

建議流程：
- 第一次打開時先 bootstrap owner account
- 之後仍走正常 session
- trusted local device 可以降低重複登入摩擦，但不是完全無登入

### 6.2 Remote private / public

必須有：

- login
- secure session cookie
- session expiry
- rate limiting
- HTTPS only

建議：

- 預留 2FA 擴充空間
- Telegram 只做通知與低風險回覆

## 7. Secrets 管理

### 7.1 Local dev / prototype

可以接受：

- `.env`

但要清楚標示：

- 僅適合本機與測試
- 不應進版本控制

### 7.2 生產模式

建議：

- Docker Compose secrets
- 或外部 secret manager 注入環境變數

敏感項目至少包含：

- session secret
- Telegram bot token
- OpenAI API key
- Anthropic API key
- executor bridge auth token

### 7.3 基本規則

- 每個 token 單獨用途
- 定期輪換
- 不回顯到前端
- 不寫進 workspace

## 8. 備份與還原

Praetor 要備份的是「狀態」，不是容器本身。

### 8.1 必備份項目

- `workspace/`
- `config/`
- `data/`

### 8.2 不需要重點備份的項目

- image layers
- container filesystem
- build cache
- temp files

### 8.3 建議策略

- 每日增量備份
- 每週完整備份
- 備份加密
- 至少一份異地副本
- 每月做 restore drill

### 8.4 還原順序

1. 還原 `config/`
2. 還原 `workspace/`
3. 還原 `data/`
4. 重新啟動 compose
5. 執行 integrity check
6. 檢查 mission resume / executor connectivity / approvals

## 9. 更新與回滾策略

建議：

- image 使用明確 tag，不要永遠 `latest`
- 更新前先備份 `data/` 與 `workspace/`
- 資料庫 migration 必須可回滾
- executor bridge 升級要和主系統分開

Praetor 不應假設：

- executor 一定永遠可用
- 主系統升級後舊的 run state 一定能直接續跑

因此：

- mission pause/resume 必須顯式設計
- migration 前要先把 running mission 轉進 safe pause 狀態

## 10. Subscription Executor Mode 的正式設計

這一節專門處理你現在最在意的問題：

**Praetor 要如何使用已安裝在宿主機上的 Codex 或 Claude Code，而不是在 Docker 裡再裝一次。**

### 10.1 設計結論

**不要把宿主機二進位直接 mount 進容器。**

**也不要要求使用者在 Docker 裡重裝一次 Codex / Claude Code。**

推薦方案是：

**host executor bridge**

也就是：

- Praetor 本體跑在 Docker
- Codex / Claude Code 跑在宿主機
- 中間透過一個很小的宿主機 bridge 進行受控呼叫

### 10.2 為什麼不用「直接在容器裡呼叫 host binary」

因為這樣通常會帶來：

- 平台相依
- 路徑相依
- runtime 相依
- 權限邊界不清
- macOS / Linux / Windows 行為不一致

也會讓部署文件變得極難 support。

### 10.3 正確抽象：Host Executor Bridge

推薦新增一個宿主機常駐進程：

- 名稱暫定：`praetor-execd`

它不屬於 Docker stack。

它的責任只有：

- 驗證請求
- 驗證工作目錄是否在 allowlist 內
- 呼叫宿主機已安裝且已登入的 `codex` 或 `claude`
- 回傳執行狀態、stdout/stderr、exit code、變更摘要

它**不是**通用 shell API。

### 10.4 Bridge 的最小職責

必須提供：

- `GET /health`
- `GET /executors`
- `POST /runs`
- `GET /runs/{id}`
- `POST /runs/{id}/cancel`
- `GET /runs/{id}/events`

### 10.5 Bridge 的安全規則

必須：

- 只監聽 `127.0.0.1`
- 使用獨立 auth token
- 僅接受 allowlisted workspace root
- 僅允許已註冊 executors
- 僅允許 Praetor 定義的 run contract

不應：

- 接受任意 shell command
- 接受任意工作目錄
- 接受來自公網的連線

### 10.5.1 非互動執行原則

bridge 的責任不是把 CLI 的互動提示直接傳給瀏覽器。

它應：
- 優先以非互動 batch 模式執行 executor
- 將底層互動需求標準化成狀態事件
- 讓 Praetor 以自己的 checkpoint / approval UX 接手

標準化事件至少要包含：
- `completed`
- `paused_budget`
- `paused_decision`
- `paused_risk`
- `auth_required`
- `interactive_approval_required`
- `cancelled`
- `failed_transient`
- `failed_permanent`

### 10.6 路徑映射

Docker 內部與宿主機的 workspace 路徑可能不同。

因此 Praetor 要顯式保存：

```yaml
path_mapping:
  container_workspace_root: /app/workspace
  host_workspace_root: /absolute/path/to/workspace
```

worker 在容器內生成任務規格時，使用 container path。

bridge 接到任務時，先把 container path 轉成 host path，再在宿主機上啟動 executor。

### 10.7 執行流程

標準流程建議如下：

1. owner 在 Web / Mobile / Telegram 提出任務
2. Praetor / worker 生成 mission 和 task spec
3. worker 將 task spec 寫入 `workspace/.praetor/runs/...`
4. worker 呼叫 host executor bridge
5. bridge 驗證 token、workspace root、executor type
6. bridge 在宿主機上用已登入的 `codex` 或 `claude` 執行
7. executor 在 host workspace 內讀寫檔案
8. bridge 將執行結果、事件、exit code 回傳給 worker
9. worker 更新 mission state、activity log、review queue

### 10.8 這樣做的好處

- 使用者只登入一次 Codex / Claude Code
- 不需要在 Docker 裡重裝
- subscription mode 與 Docker app 解耦
- 對 OpenAI / Anthropic 的 CLI 升級較不敏感
- 權限邊界比較清楚

### 10.9 這樣做的代價

- 需要多一個宿主機小程式
- 需要處理 host/container 路徑映射
- 遠端部署時，需要在遠端主機上也安裝並登入 executor

### 10.10 部署建議

最適合 subscription executor mode 的是：

- Local-only
- Remote private 且主機由 owner 自己控制

對 Remote public：

- 可以支援，但運維與登入狀態管理較麻煩
- 更適合 API mode 或 local model mode

## 11. 不同 executor 模式的推薦

| 模式 | 適合什麼部署 | 優點 | 風險 |
|---|---|---|---|
| API mode | local / remote / public | 穩定、易於服務化 | 有 API 成本 |
| Local model mode | local / private | 隱私較好 | 品質與資源要求不穩 |
| Subscription executor mode | local / private | 可用既有訂閱、體驗最貼近個人使用 | 需要 host bridge 與登入維護 |

## 12. 推薦預設

Praetor v1 建議預設：

- 部署模式：`Local-only`
- Quick Start runtime mode：`api`
- Bring Your Own Subscription：`subscription_executor`
- 對外入口：`127.0.0.1:3000`
- storage：bind mounts
- secrets：`.env` for local, secret manager for production
- backup：daily incremental + weekly full

## 13. 外部參考

- [Docker Compose production](https://docs.docker.com/compose/how-tos/production/)
- [Docker rootless mode](https://docs.docker.com/engine/security/rootless/)
- [Docker secrets in Compose](https://docs.docker.com/compose/how-tos/use-secrets/)
- [Docker storage overview](https://docs.docker.com/engine/storage/)
- [Docker volumes](https://docs.docker.com/engine/storage/volumes/)
- [Docker publishing ports](https://docs.docker.com/get-started/docker-concepts/running-containers/publishing-ports/)
- [Docker backup and restore](https://docs.docker.com/desktop/settings-and-maintenance/backup-and-restore/)
- [Using Codex with your ChatGPT plan](https://help.openai.com/en/articles/11369540-using-codex-with-chatgpt)
- [Codex CLI](https://developers.openai.com/codex/cli)
- [Claude Code overview](https://code.claude.com/docs/en/overview)
