# Praetor Repo / Runtime / 部署架構 v0.2

狀態：2026-05 更新，加上 as-built 對照。

這份文件有兩層：

- **設計層**（§1–2、§4 後半、§5–9）：repo 形態、模組切分、runtime 形態、部署的**設計目標**。這些目標仍有效。
- **as-built 層**（§3）：repo 實際長相，與 §4 的「理想模組切分」差距較大。第 v1 仍是一個比較扁平的 layout，未來搬進 packages 是 phase-2 工作。

衝突時：用 §3 描述當前狀態，§4 是未來方向。

## 1. 設計目標

Praetor 的工程架構要同時滿足：

1. 使用者一鍵部署容易
2. 前端體驗完整
3. 後端執行穩定
4. executor integration 可擴展
5. 安全邊界清楚
6. 後續不會因為 MVP 選錯架構而重寫

## 2. 技術選型建議

## 2.1 推薦主架構

前端：
- Next.js / React

後端：
- Python
- FastAPI

背景工作：
- Python worker process

持久層：
- filesystem
- SQLite
- JSONL / structured logs

原因：
- UI command center 用 React/Next.js 會比較自然
- Python 對 executor、filesystem、document 處理最順
- FastAPI 做 API 層乾淨
- SQLite 對單人 self-host 足夠
- 不必一開始引入 PostgreSQL / Redis 這種額外負擔

## 2.2 替代方案與取捨

### 全 Python + server-rendered UI

優點：
- 技術棧單純

缺點：
- 複雜 dashboard / streaming UX 較弱
- 後續互動體驗受限

判斷：
- 不推薦當主路線

### 全 Node / TypeScript

優點：
- 單語言

缺點：
- filesystem + agent runtime + document pipeline 未必更舒服
- coding executor 與 workflow orchestrator 的 Python 生態較實用

判斷：
- 可行，但不是目前最務實選擇

### 微服務一開始拆很細

優點：
- 邏輯純

缺點：
- deployment friction 高
- 對 MVP 完全不必要

判斷：
- 不建議

## 3. As-built repo 形態（2026-05）

實際 repo 與 v0.1 設計稿有偏差。以下為現況：

```txt
praetor/
├── apps/
│   ├── api/                    # FastAPI (praetor_api package)
│   ├── web/                    # Vite + React SPA proxy (praetor_web + frontend/)
│   └── worker/                 # FastAPI healthcheck (praetor_worker; runtime work
│                                 actually happens via mission_worker.py in praetor_api)
├── workers/
│   └── runtime/                # bridge_client lib (praetor_runtime)
├── bridges/
│   └── praetor-execd/          # host-side subscription executor bridge (FastAPI)
├── tools/                      # smoke + import-check scripts (pixi tasks point here)
├── docs/                       # specs (zh-TW + en mix)
├── branding/                   # logo assets
├── scripts/                    # install / update / uninstall
├── .github/                    # workflows
├── compose.yaml
├── compose.production.yaml
├── compose.app.yaml
├── compose.app.production.yaml
├── pixi.toml                   # repo-local Python env baseline
├── PRAETOR_PRODUCT_BRIEF.md
├── PRAETOR_PRODUCT_BRIEF.zh-TW.md
├── PRODUCT_INTAKE.md           # raw discussion material
├── ROADMAP.md
└── README.md
```

差異重點：

| v0.1 設計稿 | 實際 | 備註 |
|---|---|---|
| `apps/web/` = Next.js | Vite + React 19 | React Router v6 + TanStack Query (規劃中) |
| `packages/{docschemas,prompts,ui}` | 不存在 | schemas 在 `apps/api/praetor_api/schemas.py`；prompts 內嵌在 `service.py / planner.py`；UI primitives 待 Codex 重建時建立 |
| `infra/` | 不存在 | docker compose 檔案直接放 repo root；`scripts/` 是 shell installer，不是 docker config |
| `workspace.example/` | 不存在 | workspace bootstrap 由 `apps/api/praetor_api/workspace.py` 動態建立 |
| `tests/` | 名為 `tools/` | smoke tests + import checks，命名沿用 |

API 內部仍是**單一 Python package（`praetor_api`）的扁平 layout**：

```txt
apps/api/praetor_api/
├── __init__.py
├── main.py                 # FastAPI app, lifespan, top-level routes
├── ui.py                   # Jinja UI routes + templates wrapper (約 1,500 行；UI 重建後會壓到 < 600 行)
├── _translations.py        # Jinja-side i18n tables (zh-TW + en)
├── service.py              # PraetorService god object (約 2,700 行；未來切分)
├── service_agents.py       # AgentsMixin
├── service_skills.py       # SkillsMixin
├── storage.py              # SQLiteIndex + AppStorage facade
├── _filesystem_store.py    # FilesystemStore + helpers (workspace markdown 寫入)
├── models.py               # Pydantic models
├── schemas.py              # JSON schema export
├── planner.py              # CEO planner (LLM + offline test variant)
├── runtime.py              # MissionRuntime (subscription_executor / api 兩條路)
├── mission_worker.py       # background MissionWorker (mission_jobs queue 消費者)
├── providers.py            # OpenAI / Anthropic SDK 包裝
├── safety_policy.py        # prompt-time safety policy 組裝
├── recommendations.py      # onboarding preview + mission complexity assessment
├── run_registry.py         # in-memory async run register
├── config.py               # env vars
├── auth.py                 # owner password / bcrypt
├── security.py             # CSRF + rate limit + setup token
├── telegram.py             # Telegram bot integration
├── workspace.py            # bootstrap_workspace
├── templates/              # Jinja templates (UI 重建後會清掉大部分)
└── static/                 # praetor.css + 圖片 (UI 重建後會大量縮減)
```

下一輪 refactor（**已知 backlog，不在 v1 阻擋路徑上**）：

1. 把 `service.py` 拆成 `service_mission.py / service_governance.py / service_conversation.py / service_knowledge.py` 等 mixin（同 §4 規劃，但搬進 mixin 而非獨立 package）。
2. 把 `storage.py` 拆成 `storage/{missions,governance,knowledge,organization}.py` repos。
3. 視 UI 重建後的維護摩擦決定要不要拉 `packages/ui` 共用層（v1 不做）。

## 4. 邏輯模組切分（未來方向，非 as-built）

後端內部建議切成：

```txt
apps/api/app/
├── api/
├── auth/
├── governance/
├── roles/
├── runtime/
├── missions/
├── memory/
├── executors/
├── models/
├── usage/
├── storage/
└── settings/
```

作用如下：

- `api/`
  - HTTP / WebSocket interfaces

- `auth/`
  - local-only / remote mode
  - owner login

- `governance/`
  - approval policy
  - checkpoint policy
  - never-allow policy

- `roles/`
  - role schema
  - role evolution
  - role-to-agent mapping

- `runtime/`
  - core orchestration loop
  - run budgets
  - pause / resume

- `missions/`
  - mission lifecycle
  - task state machine

- `memory/`
  - wiki
  - retrieval
  - mission context

- `executors/`
  - Codex / Claude / OpenClaw / API adapters

- `models/`
  - provider abstraction
  - fallback logic

- `usage/`
  - token stats
  - cost stats
  - per-model usage

- `storage/`
  - filesystem
  - SQLite
  - audit logs

- `settings/`
  - user-configurable policies

## 5. Runtime 形態

Praetor 不是單純 request-response app。

它有三種主要 runtime 路徑：

1. synchronous UI/API requests
2. background mission execution
3. streaming or polling updates to UI

### 5.1 API Process

API process 負責：
- auth
- UI data retrieval
- mission creation
- approval actions
- settings updates
- lightweight orchestration triggers

### 5.2 Worker Process

Worker process 負責：
- 執行 mission batch
- 呼叫 executors
- 更新 mission state
- 產生 logs
- 套用 checkpoint policy

### 5.3 為什麼要獨立 worker

優點：
- API 不會被長任務卡住
- executor timeout 不直接拖垮 UI
- failure isolation 更好

缺點：
- 架構稍微複雜一點

判斷：
- 值得，因為這是穩定性的核心

## 6. 部署架構建議

### 6.1 使用者體驗目標

使用者應該只需要：

```bash
docker compose up -d
```

然後打開：

`http://localhost:3000`

但這裡要明確區分兩條安裝路線：

- `Quick Start`
  - 對應 `api` 或 `local_model`
  - 純 Docker 路線

- `Bring Your Own Subscription`
  - 對應 `subscription_executor`
  - Docker + host executor bridge
  - 不應假裝成純 Docker 即可完成

### 6.2 MVP Compose 建議

雖然使用者只要一個命令，但 compose 可以是多服務。

建議：

```txt
services:
  web:
    - Next.js app
  api:
    - FastAPI app
  worker:
    - background runtime worker
```

可選：
- `ollama`
- `reverse-proxy`

不需要：
- PostgreSQL
- Redis

除非後續 scale 真的需要。

### 6.3 為什麼不是單一超大 container

單一 container 的優點是簡單，但缺點是：
- API / worker failure isolation 差
- logs 混在一起
- health check 顆粒太粗

因此建議：
- 對使用者維持單一啟動命令
- 對系統內部維持少量清晰服務切分

## 7. Persistent Volumes

建議至少掛載：

```txt
./workspace:/app/workspace
./config:/app/config
./data:/app/data
```

其中：
- `workspace/`
  - 公司資料、Wiki、missions、projects

- `config/`
  - settings、governance、runtime configs

- `data/`
  - SQLite
  - usage db
  - audit logs
  - caches

## 8. 資料儲存策略

### 8.1 Filesystem

存：
- business truth
- company memory
- missions
- outputs

### 8.2 SQLite

存：
- session state
- task status index
- usage metrics
- notifications
- UI cache

重要限制：
- SQLite 不是 mission state 的唯一真相來源
- mission canonical state 應存在 mission folder
- SQLite 應可由 mission folder 重建索引

### 8.3 JSONL / Structured Logs

存：
- executor runs
- step traces
- failures
- audit trails

## 9. API 介面建議

不需要一開始就設計巨大 API surface，但至少應有：

### 9.1 Auth

- `POST /auth/login`
- `POST /auth/logout`
- `GET /auth/session`

### 9.2 Onboarding

- `GET /onboarding/state`
- `POST /onboarding/answer`
- `POST /onboarding/complete`

### 9.3 Praetor

- `POST /praetor/chat`
- `GET /praetor/briefing`
- `GET /praetor/escalations`

### 9.4 Missions / Tasks

- `GET /missions`
- `POST /missions`
- `GET /missions/:id`
- `POST /missions/:id/continue`
- `POST /missions/:id/pause`
- `GET /tasks`
- `GET /tasks/:id`

### 9.5 Memory

- `GET /memory/wiki`
- `GET /memory/decisions`
- `GET /memory/retrieval-preview/:run_id`

### 9.6 Usage / Models

- `GET /usage/overview`
- `GET /usage/models`
- `GET /usage/executors`

### 9.7 Settings

- `GET /settings`
- `PATCH /settings/general`
- `PATCH /settings/governance`
- `PATCH /settings/runtime`

## 10. 背景工作模型

### 10.1 Mission Runner

每個 mission 的執行週期應大致是：

1. read relevant context
2. create or update task plan
3. choose role / executor
4. execute one batch
5. review outputs
6. checkpoint or continue
7. persist state

### 10.2 為什麼要 batch

因為如果 executor 每一步都回來問：
- 使用者會煩
- 系統噪音大
- 任務不連續

Batch 可以讓 Praetor：
- 一次推進一段
- 到 checkpoint 再停

### 10.3 Resume 機制

Resume 不應該只靠 runtime memory。

應以 mission folder 為主恢復。

SQLite 可協助：
- 加速查詢
- 補充 UI state
- 提供索引

但不應成為唯一真相來源。

## 11. Executor Driver 設計

每個 executor 應該是一個獨立 adapter。

推薦結構：

```txt
executors/
├── base.py
├── bridge_client.py
├── openai_api.py
├── ollama.py
├── codex_cli.py
├── claude_code.py
└── openclaw.py
```

共同接口建議：

```python
class ExecutorAdapter:
    def healthcheck(self): ...
    def prepare(self, task_spec): ...
    def run(self, prepared_task): ...
    def collect_outputs(self, run_ref): ...
    def collect_usage(self, run_ref): ...
    def normalize_error(self, err): ...
```

補充要求：
- adapter 不只要會「呼叫」
- 還要會把底層 CLI 的互動性標準化成 Praetor 可理解的 batch 狀態

建議再加：

```python
class BatchExecutionResult:
    status: str  # completed | paused_budget | auth_required | failed_transient ...
    requires_owner_action: bool
    pause_reason: str | None
```

`subscription_executor` 類 adapter 應優先走：
- 非互動模式
- 事件流 / 狀態輪詢
- bridge 層統一 cancel / timeout / auth-required / approval-required

## 12. 安全工程

### 12.1 Browser 與 secrets 分離

API keys、executor credentials 不應該直接暴露到前端。

前端只應看到：
- redacted status
- connectivity
- health

### 12.2 Workspace Scope Enforcement

不能只靠 prompt 寫「請不要超出資料夾」。

應有真正 enforcement：
- path normalization
- path allowlist checks
- denylist checks
- destructive action guards

### 12.3 Subscription Executor 特殊風險

Codex CLI / Claude Code / OpenClaw 類執行器可能有自己的權限模型。

Praetor 必須：
- 在呼叫前檢查 scope
- 在呼叫時帶上明確 task spec
- 在呼叫後做 output validation

不能假設 external executor 自己就會完全守規矩。

### 12.4 Remote Self-host 安全

若啟用遠端模式，至少需要：
- login
- password hash
- HTTPS
- session expiry
- CSRF / cookie policy
- brute-force 基本保護

第一版不需要多使用者，但不能完全不做安全。

## 13. 穩定性工程

### 13.1 Health Checks

至少要檢查：
- API health
- worker health
- SQLite writable
- workspace mounted
- runtime mode healthy
- executor health

### 13.2 Retries

可重試類型：
- transient executor failure
- temporary provider outage
- file lock conflict

不可盲目重試：
- destructive write
- strategy decision
- repeated invalid output

### 13.3 Failure Classification

錯誤至少分：
- user-action-needed
- runtime-temporary
- configuration-error
- permission-error
- executor-failure
- mission-logic-failure

這樣 UI 才能顯示正確指引。

### 13.4 Audit Trail

每次重要執行應記錄：
- mission id
- task id
- role
- executor
- model
- tokens / cost
- input set
- output files
- decision points

### 13.5 Backups

至少要有：
- workspace snapshot policy
- SQLite backup policy
- optional export bundle

## 14. 測試策略

Praetor 不能只測 UI，也不能只測 prompt。

至少要分 5 層：

### 14.1 Schema Tests

測：
- config validity
- role schema
- company DNA schema
- mission schema

### 14.2 Policy Tests

測：
- approval policy
- PM creation policy
- path permissions
- checkpoint routing

### 14.3 Adapter Tests

測：
- executor contract
- failure normalization
- usage extraction

### 14.4 Workflow Tests

測：
- create project
- review inbox
- build company wiki
- update status

### 14.5 UI Tests

測：
- onboarding
- Praetor page
- approvals
- mission pause / continue
- models page visibility

## 15. 開發體驗

### 15.1 本機開發

應支援：
- web 熱更新
- api 熱重載
- worker 可單獨跑
- sample workspace
- fake executor / dry-run mode

### 15.2 為什麼 fake executor 很重要

因為真實模型與 executor：
- 昂貴
- 不穩
- 難測

fake executor 可用於：
- UI demo
- workflow smoke tests
- onboarding 測試

## 16. 建議 repo 細節

推薦補這些檔案：

```txt
.env.example
compose.yaml
compose.production.yaml
workspace.example/
config.example/
README.md
Makefile
```

`workspace.example/` 應內含：
- Wiki seed
- sample mission
- sample inbox files
- sample project

這會大幅提升第一印象。

## 17. 完成度標準

Praetor 什麼時候算不是 demo，而是可用產品原型？

至少要同時做到：
- 一鍵起來
- onboarding 可跑完
- 會生成 Company DNA
- 會建立 workspace
- 可以啟動 mission
- 可以看到 task 狀態
- 可以在 checkpoint 停下
- 可以 continue / approve
- 可以看到 model / token / runtime 狀態
- 有清楚安全邊界

## 18. MVP 實作順序

### Step 1

- contracts / schemas
- workspace model
- governance rules
- runtime mode config

### Step 2

- onboarding backend
- Praetor page
- settings basics

### Step 3

- mission runtime
- tasks page
- file outputs

### Step 4

- executor abstraction
- API mode
- one subscription executor

### Step 5

- models page
- pause / continue UX
- audit logs

### Step 6

- hidden PM creation
- meetings
- retrieval preview

## 19. 最後的架構結論

Praetor 最好的技術結構不是最炫的，也不是最微服務的。

而是：

**對使用者維持一個非常簡單的部署與使用入口，對內部維持清楚的模組邊界、背景執行層、權限邊界與可恢復狀態。**

簡單說：

- 對外：一個 command center
- 對內：一個有治理、有 runtime、有 executor abstraction 的 AI operating system
