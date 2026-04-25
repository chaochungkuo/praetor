# praetor-execd 規格 v0.1

狀態：設計稿

這份文件定義 `praetor-execd` 的完整規格。

`praetor-execd` 是 Praetor 在 **subscription executor mode** 下使用的宿主機 bridge。
它負責在 **不把 Codex / Claude Code 重裝進 Docker** 的前提下，讓 Docker 內的 Praetor worker 能受控地呼叫宿主機上已安裝、已登入的 executors。

---

## 1. 一句話定義

`praetor-execd` 是一個 **只在宿主機本地監聽、只接受受限任務規格、只允許已註冊 executors、只在 allowlisted workspace 內執行** 的本機 executor bridge。

它不是：

- 通用 shell server
- 遠端 agent runtime
- 任意命令代理
- 替代 Praetor orchestration 的系統

---

## 2. 設計目標

`praetor-execd` 要同時滿足：

1. 讓 Praetor 使用宿主機既有的 Codex / Claude Code
2. 不要求在 Docker 內重裝或重新登入 CLI
3. 讓 Praetor 維持自己的治理與 checkpoint 模型
4. 將底層 CLI 的互動性標準化為 Praetor 可理解的狀態
5. 在安全邊界上嚴格限制 scope、路徑、executor 類型與請求來源
6. 對失敗、取消、超時、auth 過期、approval 要有一致行為

---

## 3. 非目標

v0.1 的 `praetor-execd` 不應承擔：

- 多租戶 user management
- 公網 exposed API
- 任意 shell 命令執行
- 通用 job queue 系統
- 跨多台 host 的分散式協調
- 細粒度 RBAC
- 取代 Praetor worker 的 mission orchestration

---

## 4. 角色分工

### 4.1 Praetor worker 負責

- 讀取 mission context
- 產生 task spec
- 決定使用哪個 role / executor
- 決定 checkpoint / approval 邏輯
- 追蹤 mission lifecycle
- 更新 UI 與狀態

### 4.2 praetor-execd 負責

- 驗證 request token
- 驗證 executor 是否允許
- 驗證工作目錄是否在 allowlist
- 驗證 container path 與 host path 映射
- 啟動 executor 子程序
- 蒐集 stdout / stderr / exit code / timing
- 標準化底層結果
- 提供 run status 與事件流

### 4.3 底層 executor 負責

- 在指定工作目錄內執行實際任務
- 讀寫檔案
- 回應登入狀態、命令執行狀態與工具本身的錯誤

---

## 5. 信任邊界

### 5.1 邊界總覽

```txt
Owner
  ↓
Praetor Web / Mobile / Telegram
  ↓
Praetor API / Worker (Docker)
  ↓
praetor-execd (Host, loopback only)
  ↓
Codex / Claude Code (Host process)
  ↓
Host workspace
```

### 5.2 基本原則

- Praetor 與 `praetor-execd` 是不同 trust zone
- `praetor-execd` 不應信任來自 Docker 的任意請求
- executor 本身也不應被完全信任
- workspace scope 必須在 bridge 再檢查一次

---

## 6. 支援矩陣

v0.1 正式支援：

- `codex`
- `claude_code`

可預留但不在 v0.1 正式支援：

- `openclaw`
- `custom_executor`

每個 executor 都應註冊為明確類型，不接受任意 binary 路徑。

---

## 7. 部署與程序模型

### 7.1 執行位置

`praetor-execd` 必須跑在 Praetor host 上，而不是 Docker stack 內。

### 7.2 監聽方式

v0.1 建議：

- `127.0.0.1:<port>`

不建議 v0.1：

- `0.0.0.0`
- Unix socket only
- public ingress

說明：
- `127.0.0.1` 比較容易跨平台
- Docker 內可透過 `host.docker.internal` 或等價 host-gateway 存取

### 7.3 單機常駐進程

`praetor-execd` 應該是單一常駐 process，內部可管理多個 child process。

它需要：

- in-memory run registry
- persistence-backed run metadata
- stdout / stderr log capture
- cancellation registry

---

## 8. 設定檔模型

建議使用：

- `config.yaml`
- 或 `config.toml`

範例：

```yaml
server:
  host: 127.0.0.1
  port: 9417
  auth_token: env:PRAETOR_EXECUTOR_BRIDGE_TOKEN

paths:
  host_workspace_root: /absolute/path/to/workspace
  allowed_roots:
    - /absolute/path/to/workspace
  deny_roots:
    - /absolute/path/to/workspace/Archive
    - /absolute/path/to/workspace/.praetor/secrets

executors:
  codex:
    enabled: true
    command: codex
    args: []
    healthcheck: ["codex", "--version"]
    requires_login: true
    supports_noninteractive_batch: true
    supports_cancel: true

  claude_code:
    enabled: true
    command: claude
    args: []
    healthcheck: ["claude", "--version"]
    requires_login: true
    supports_noninteractive_batch: true
    supports_cancel: true

runtime:
  max_concurrent_runs: 2
  default_timeout_seconds: 1800
  max_event_buffer: 5000
  persist_run_logs: true
  log_dir: /absolute/path/to/workspace/.praetor/bridge-logs
```

### 8.1 必要欄位

- `server.host`
- `server.port`
- `server.auth_token`
- `paths.host_workspace_root`
- `executors.<name>.enabled`
- `executors.<name>.command`
- `runtime.max_concurrent_runs`

### 8.2 環境變數覆蓋

至少支援：

- `PRAETOR_EXECUTOR_BRIDGE_TOKEN`
- `PRAETOR_EXECUTOR_BRIDGE_PORT`
- `PRAETOR_EXECUTOR_BRIDGE_LOG_DIR`

---

## 9. Path Mapping 模型

Praetor 在容器內看到的是 container path，`praetor-execd` 在 host 上看到的是 host path。

因此 request 必須帶上：

```yaml
path_mapping:
  container_workspace_root: /app/workspace
  host_workspace_root: /absolute/path/to/workspace
  target_workdir: /app/workspace/Projects/Website
```

bridge 在執行前應：

1. 驗證 `target_workdir` 以 `container_workspace_root` 開頭
2. 將其轉換到 `host_workspace_root`
3. 做 `realpath` normalization
4. 驗證結果仍落在 allowlist 內
5. 驗證不在 denylist 內

若任一步驟失敗，直接回 `permission_error`

---

## 10. Request / Response 原則

### 10.1 認證

所有 API 都要求：

- `Authorization: Bearer <token>`

token 不通過時：

- 回 `401`

### 10.2 Content Type

統一使用：

- `application/json`

### 10.3 Response envelope

建議統一格式：

```json
{
  "ok": true,
  "data": {},
  "error": null
}
```

錯誤時：

```json
{
  "ok": false,
  "data": null,
  "error": {
    "code": "permission_error",
    "message": "Target path is outside allowed roots."
  }
}
```

---

## 11. API Surface

v0.1 正式 API：

- `GET /health`
- `GET /executors`
- `POST /runs`
- `GET /runs/{id}`
- `GET /runs/{id}/events`
- `POST /runs/{id}/cancel`

可選：

- `GET /runs/{id}/artifacts`
- `DELETE /runs/{id}`

### 11.1 `GET /health`

用途：
- 確認 bridge 活著
- 確認配置已載入

回傳：

```json
{
  "ok": true,
  "data": {
    "status": "healthy",
    "version": "0.1.0",
    "uptime_seconds": 1024,
    "configured_executors": ["codex", "claude_code"]
  },
  "error": null
}
```

### 11.2 `GET /executors`

用途：
- 提供 onboarding 與 runtime health 檢查

回傳欄位建議：

- `name`
- `enabled`
- `binary_found`
- `login_state`
- `supports_noninteractive_batch`
- `supports_cancel`
- `last_healthcheck_at`

範例：

```json
{
  "ok": true,
  "data": {
    "executors": [
      {
        "name": "codex",
        "enabled": true,
        "binary_found": true,
        "login_state": "authenticated",
        "supports_noninteractive_batch": true,
        "supports_cancel": true
      }
    ]
  },
  "error": null
}
```

### 11.3 `POST /runs`

用途：
- 建立一個新的 batch run

最小 request：

```json
{
  "request_id": "req_123",
  "mission_id": "mission_build_site",
  "task_id": "task_generate_homepage",
  "executor": "codex",
  "timeout_seconds": 1800,
  "path_mapping": {
    "container_workspace_root": "/app/workspace",
    "host_workspace_root": "/absolute/path/to/workspace",
    "target_workdir": "/app/workspace/Projects/Website"
  },
  "task_spec": {
    "title": "Generate homepage draft",
    "instructions": "Work only in the target folder. Do not delete files.",
    "input_files": [
      "/app/workspace/Projects/Website/PROJECT.md"
    ],
    "expected_outputs": [
      "/app/workspace/Projects/Website/homepage.md"
    ],
    "approval_policy": {
      "allow_destructive_write": false,
      "allow_shell": false
    }
  }
}
```

立即回應：

```json
{
  "ok": true,
  "data": {
    "run_id": "run_abc",
    "status": "accepted",
    "executor": "codex"
  },
  "error": null
}
```

### 11.4 `GET /runs/{id}`

用途：
- 查詢目前狀態

回傳欄位建議：

- `run_id`
- `mission_id`
- `task_id`
- `executor`
- `status`
- `normalized_status`
- `started_at`
- `finished_at`
- `exit_code`
- `requires_owner_action`
- `pause_reason`
- `usage`
- `changed_files`

### 11.5 `GET /runs/{id}/events`

用途：
- 給 Praetor worker 或 UI 讀事件流

v0.1 可以先用：

- polling JSON list

v0.2 可升級：

- SSE

事件範例：

```json
{
  "ok": true,
  "data": {
    "events": [
      {
        "seq": 1,
        "type": "run_started",
        "ts": "2026-04-24T12:00:00Z"
      },
      {
        "seq": 2,
        "type": "stdout",
        "ts": "2026-04-24T12:00:05Z",
        "data": "Reading project files..."
      },
      {
        "seq": 3,
        "type": "normalized_status",
        "ts": "2026-04-24T12:00:40Z",
        "data": {
          "status": "completed"
        }
      }
    ],
    "next_seq": 4
  },
  "error": null
}
```

### 11.6 `POST /runs/{id}/cancel`

用途：
- 要求終止目前執行中的 child process

回傳：

- `accepted`
- `already_finished`
- `not_cancellable`

---

## 12. Run State Machine

### 12.1 Internal state

```txt
accepted
→ validating
→ queued
→ starting
→ running
→ collecting
→ normalizing
→ completed
```

失敗分支：

```txt
accepted
→ validating
→ rejected
```

```txt
running
→ cancelling
→ cancelled
```

```txt
running
→ failed_transient
```

```txt
running
→ failed_permanent
```

### 12.2 Normalized status

Praetor 真正該讀的是 normalized status，而不是 child process 細節。

正式狀態：

- `completed`
- `paused_budget`
- `paused_decision`
- `paused_risk`
- `auth_required`
- `interactive_approval_required`
- `cancelled`
- `failed_transient`
- `failed_permanent`

---

## 13. Event Model

### 13.1 事件類型

建議至少支援：

- `run_accepted`
- `run_started`
- `stdout`
- `stderr`
- `heartbeat`
- `artifact_detected`
- `usage_detected`
- `normalized_status`
- `run_finished`
- `run_cancelled`
- `run_failed`

### 13.2 Event 字段

每個事件至少包含：

- `seq`
- `type`
- `ts`
- `run_id`
- `data`

### 13.3 Event 保留策略

v0.1 建議：

- in-memory buffer + optional file persistence
- 每個 run 至少保留最近 `N` 條事件
- 完成後可歸檔到 `.praetor/bridge-logs/`

---

## 14. Child Process Model

### 14.1 啟動原則

bridge 不應直接用 shell 拼字串。

應使用：

- 明確的 command array
- 明確的 working directory
- 明確的 env allowlist

### 14.2 Environment allowlist

只應傳入必要環境變數，例如：

- `PATH`
- `HOME`
- executor 自己需要的最少登入相關變數
- Praetor run metadata

不應把整個 Docker app 環境原樣轉發。

### 14.3 Working directory

每次 run 必須綁定單一 `host target_workdir`。

如果 task spec 需要跨多個資料夾：

- 也必須都落在 allowlisted workspace root 內
- 建議由 Praetor 先收斂成 mission-scoped root

---

## 15. Non-interactive Batch 策略

這一節是 `praetor-execd` 最關鍵的部分。

### 15.1 原則

Praetor 的產品目標是：

- AI 先做一批
- 到 checkpoint 再停

因此 bridge 需要優先選擇 executor 的非互動執行方式。

### 15.2 若 executor 支援原生非互動模式

bridge 應：

- 使用非互動模式啟動
- 關閉多餘 confirmation prompt
- 把結果轉換成 normalized status

### 15.3 若 executor 不完全支援非互動模式

bridge 仍應：

- 偵測卡住、等待輸入、auth 過期、approval prompt
- 不直接把 prompt 傳給 owner
- 結束該次 run 並回傳：
  - `auth_required`
  - `interactive_approval_required`
  - 或其他對應 normalized status

### 15.4 v0.1 判斷原則

v0.1 不追求完美模擬所有 CLI 行為。

重點是：

- 不讓底層 CLI 互動直接污染 Praetor UX
- 寧可早停並標準化，也不要卡死整個 mission

---

## 16. Artifact / Change Detection

bridge 應協助 Praetor 收集：

- 變更過的檔案路徑
- 新建檔案
- 刪除檔案
- 最後修改時間

v0.1 可用：

- run 前後對 target scope 做快照 diff

不要求 v0.1：

- AST-level diff
- semantic diff

---

## 17. Usage 與成本資料

bridge 若能從 executor 取得 usage，應回傳：

- `input_tokens`
- `output_tokens`
- `estimated_cost`
- `duration_ms`

若取不到，也至少回傳：

- `duration_ms`
- `usage_available: false`

不要因為抓不到 token 就讓 run 失敗。

---

## 18. Error Normalization

bridge 必須把底層錯誤統一成可被 Praetor 使用的錯誤類型。

建議至少分類：

- `auth_error`
- `permission_error`
- `config_error`
- `path_mapping_error`
- `executor_not_found`
- `executor_unhealthy`
- `executor_interactive_block`
- `timeout_error`
- `cancelled`
- `temporary_runtime_error`
- `permanent_runtime_error`

每種錯誤都應帶：

- `retryable`
- `owner_action_required`
- `suggested_next_step`

---

## 19. Healthcheck 模型

### 19.1 Bridge health

Bridge health 應檢查：

- server running
- config loaded
- log dir writable
- event buffer working

### 19.2 Executor health

每個 executor health 應檢查：

- binary exists
- command runnable
- login state detectable
- minimal no-op / version command 正常

### 19.3 Health 狀態分級

- `healthy`
- `degraded`
- `unavailable`

---

## 20. Concurrency 與排程

### 20.1 基本原則

v0.1 不應允許無限制平行 runs。

建議：

- 全域 `max_concurrent_runs`
- 每個 executor 類型可有自己的 concurrency limit

### 20.2 為什麼要保守

因為 subscription executors 常受：

- 本機資源
- CLI 限制
- 登入 session
- TTY / lock 行為

影響。

保守一點比「理論上能多開」更穩。

---

## 21. 安全規則

### 21.1 絕對規則

bridge 不應：

- 接受任意 shell 字串
- 接受任意 binary path
- 接受超出 workspace 的 workdir
- 對公網監聽
- 回傳敏感環境變數
- 讓前端直接呼叫

### 21.2 Host 路徑規則

bridge 必須做：

- `realpath` normalization
- symlink 防逃逸檢查
- denylist 檢查
- allowlist 檢查

### 21.3 Token 規則

- token 為單一 bridge 專用
- 不與 session secret 共用
- 不與 Telegram token 共用
- 應可輪換

---

## 22. Run Logs 與可追溯性

每個 run 至少應保存：

- request payload 摘要
- executor 類型
- host workdir
- start / end time
- normalized status
- child exit code
- stdout/stderr 摘要
- changed files
- usage

建議儲存在：

- `workspace/.praetor/bridge-logs/<run_id>.json`
- `workspace/.praetor/bridge-logs/<run_id>.events.jsonl`

---

## 23. 與 Praetor Onboarding 的整合

當使用者在 onboarding 選擇 `subscription_executor` 時：

1. Praetor 先打 `GET /health`
2. 再打 `GET /executors`
3. 檢查：
   - bridge reachable
   - target executor enabled
   - binary found
   - login_state 可接受
4. 成功才允許完成 runtime 選擇

若失敗，UI 應明確提示：

- bridge not running
- executor not installed
- login expired
- path mapping not configured

---

## 24. 與 Praetor Worker 的整合

Worker 對 bridge 的最小流程：

1. 建立 task spec
2. 呼叫 `POST /runs`
3. 輪詢 `GET /runs/{id}` 或 `GET /runs/{id}/events`
4. 收到 normalized status
5. 將結果映射到 mission state

對應關係建議：

| Bridge normalized status | Praetor mission handling |
|---|---|
| `completed` | 進入 review 或完成 |
| `paused_budget` | waiting approval / budget extension |
| `paused_decision` | waiting owner decision |
| `paused_risk` | risk checkpoint |
| `auth_required` | settings / executor reconnect |
| `interactive_approval_required` | checkpoint requiring owner review |
| `failed_transient` | 可重試 |
| `failed_permanent` | 轉人工介入 |

---

## 25. 實作建議

### 25.1 技術選擇

建議：

- Python
- FastAPI 或輕量 HTTP server
- subprocess child management
- JSON file persistence

理由：

- 與 Praetor backend 同語言
- 好處理 path / process / logs
- 實作成本最低

### 25.2 v0.1 實作順序

1. config loader
2. auth middleware
3. `GET /health`
4. `GET /executors`
5. `POST /runs`
6. child process capture
7. `GET /runs/{id}`
8. `GET /runs/{id}/events`
9. `POST /runs/{id}/cancel`
10. artifact diff
11. normalized status mapping

---

## 26. v0.1 仍可接受的限制

v0.1 可以接受：

- 用 polling 而不是 SSE
- 用簡單檔案快照 diff
- login state 只做到 best-effort detection
- executor support 只先做 `codex` / `claude_code`
- child process metadata 先存在本機 JSON / JSONL

v0.1 不應接受：

- 無 path scope enforcement
- 無 auth token
- 直接接 shell string
- 把 CLI 互動原樣丟給 owner

---

## 27. 最後結論

`praetor-execd` 的本質不是「幫 Praetor 開 shell」。

它是：

**一個把宿主機 subscription executors 安全地包裝成可治理、可追蹤、可非互動批次執行的本機 bridge。**

只要這層做對：

- Praetor 就能沿用使用者既有的 Codex / Claude Code 訂閱
- 不需要在 Docker 裡重裝
- 不需要重新設計整個產品的治理模型
- 也不會讓底層 CLI 的互動習慣直接破壞 Praetor 的 UX
