# Praetor 開源成功與產品化執行規格

Status: working spec
Date: 2026-04-25

這份文件整理目前 codebase 的實際狀態，並把它對照到 Praetor 作為開源專案、未來服務化與商業化的成功路線。它的用途不是重新定義 Praetor，而是讓後續產品、工程、文件、行銷可以跟著同一份現況與優先順序前進。

## 1. 核心判斷

Praetor 目前已經不是單純概念文件。codebase 裡已經存在一條可跑的產品縱切：

1. 使用者完成 onboarding。
2. 系統建立 owner auth、settings、workspace、company DNA、governance、roles。
3. 使用者建立 mission。
4. mission 以檔案系統作為 canonical state。
5. runtime 透過 API provider 或 host-side subscription executor bridge 執行。
6. 執行結果寫回 task log、bridge run、REPORT、DECISIONS、audit log、approvals。
7. Web UI 顯示 Praetor、Overview、Tasks、Activity、Memory、Decisions、Models、Meetings、Settings、mission detail、mobile briefing。

但目前離「能打動開源使用者」還有一段距離。主要問題不是缺更多頁面，而是：

- demo story 還不夠尖銳
- mission 執行仍偏同步與工具原型感
- role / AI CEO / hidden PM 的概念有資料模型，但實際 orchestration 還偏薄
- company memory 可以讀寫，但還不是一個明確、有生命週期的產品能力
- approval 可以建立與解決，但批准後不會真正恢復或改變執行策略
- worker service 目前主要是 health/status stub，真正 mission runtime 還在 API service inline 執行

對外定位應該保持：

> Praetor is a local-first AI company operating system for solo builders.

中文定位：

> Praetor 是給獨立開發者、創業者、研究者使用的本地優先 AI 公司作業系統。使用者只需要和 AI CEO 溝通，Praetor 負責角色、任務、記憶、執行、檢查點與回報。

## 2. 目前 codebase 設置

### 2.1 Repo 主要模組

目前實作分成幾個清楚邊界：

- `apps/api/praetor_api/`
  - 主要 FastAPI app
  - Web UI templates
  - auth / CSRF / setup token
  - onboarding、mission、runtime、memory、approval、meeting、usage
  - 目前 mission runtime 實際在這裡 inline 執行

- `apps/web/praetor_web/`
  - thin proxy web service
  - 在 split stack 中代理到 API service

- `apps/worker/praetor_worker/`
  - worker service skeleton
  - 目前提供 health/status
  - 還沒有真正接管 mission queue / background execution

- `bridges/praetor-execd/`
  - host-side executor bridge
  - 用 bearer token 保護
  - 負責把 Docker 內 Praetor 的 run request 映射到宿主機 workspace
  - 支援 `codex` 與 `claude_code` runner

- `workers/runtime/praetor_runtime/`
  - worker-side bridge client
  - 負責呼叫 `praetor-execd` 的 health、executors、runs、events、cancel

- `docs/`
  - 產品、系統、UI、surface、repo architecture、deployment security、bridge spec

- `tools/`
  - smoke tests / import checks / fake OpenAI server

### 2.2 部署形態

目前有兩種主要 Docker 形態：

- `compose.app.yaml`
  - 單一 `app` service
  - 綁定 `workspace` 與 `data`
  - 對使用者最容易解釋

- `compose.yaml`
  - `web` / `api` / `worker` split stack
  - 可連 host-side `praetor-execd`
  - 包含 optional `ollama` profile
  - worker 目前還不是正式 queue worker

目前推薦開源 demo 應先以 `compose.app.yaml` 或 Pixi local flow 為主，避免 split stack 增加初次使用成本。

### 2.3 設定與環境變數

核心設定來源在 `apps/api/praetor_api/config.py`：

- state:
  - `PRAETOR_STATE_DIR`

- bridge:
  - `PRAETOR_BRIDGE_BASE_URL`
  - `PRAETOR_BRIDGE_TOKEN`

- API providers:
  - `OPENAI_API_KEY`
  - `ANTHROPIC_API_KEY`
  - `PRAETOR_OPENAI_BASE_URL`
  - `PRAETOR_ANTHROPIC_BASE_URL`

- security:
  - `PRAETOR_SESSION_SECRET`
  - `PRAETOR_SETUP_TOKEN`
  - `PRAETOR_REQUIRE_LOGIN`
  - `PRAETOR_SECURE_COOKIE`
  - `PRAETOR_ENV`
  - `PRAETOR_DEBUG_ROUTES`
  - rate limit envs

目前 production security guard 會拒絕弱 session secret、弱 bridge token、缺失或弱 setup token。這是對開源信任很重要的基礎。

## 3. 目前記憶管理設計

### 3.1 記憶原則

目前 codebase 實作方向符合既有產品原則：

- company memory yes
- agent personal memory no
- filesystem 是長期真相來源
- SQLite 是 index/cache
- mission folder 是 mission canonical state

這個方向適合開源 positioning，因為它能支撐：

- local-first
- user-owned data
- inspectable memory
- backup/restore
- Git-friendly future

### 3.2 Workspace bootstrap

`bootstrap_workspace()` 目前會建立：

- `Wiki`
- `Projects`
- `Finance`
- `Operations`
- `Development`
- `Decisions`
- `Agents`
- `Missions`
- `Meetings`
- `Inbox`
- `Archive`
- `.praetor`
- `.praetor/history`

並建立預設 wiki：

- `Wiki/Company.md`
- `Wiki/Strategy.md`
- `Wiki/Decision Log.md`
- `Wiki/Agent Handbook.md`

注意：`Agents` 與 `Agent Handbook` 文字上仍偏 agent-centric。若要強化「使用者管理 role，不管理 agent」的定位，後續應考慮改為 `Roles` / `Role Handbook`，或保留底層但 UI 文案避免讓使用者覺得要管理多個 agent。

### 3.3 App state

`AppStorage` 同時寫：

- filesystem:
  - `settings.json`
  - `auth.json`
  - `audit.jsonl`
  - `approvals.json`

- SQLite:
  - `index.sqlite3`
  - `settings`
  - `missions`

重要現況：

- auth password hash 儲存在 state dir，不在 workspace。
- audit log 儲存在 state dir，不在 workspace。
- approvals 儲存在 state dir，不在 mission folder。
- settings 同步寫 filesystem 與 SQLite。
- missions 優先從 workspace `Missions/*/mission.json` 讀，SQLite 作為 fallback/index。

### 3.4 Mission memory

每個 mission 會建立：

- `Missions/<mission_id>/mission.json`
- `Missions/<mission_id>/MISSION.md`
- `Missions/<mission_id>/STATUS.md`
- `Missions/<mission_id>/TASKS.md`
- `Missions/<mission_id>/DECISIONS.md`
- `Missions/<mission_id>/CONTEXT.md`
- `Missions/<mission_id>/PM_REPORT.md`
- `Missions/<mission_id>/REPORT.md`
- `Missions/<mission_id>/logs/*.task.json`
- `Missions/<mission_id>/logs/*.bridge.json`
- `Missions/<mission_id>/meetings/*.meeting.json`
- `Missions/<mission_id>/meetings/*.md`

目前問題：

- `TASKS.md`, `CONTEXT.md`, `DECISIONS.md`, `PM_REPORT.md`, `REPORT.md` 在建立時會被重寫為初始內容。若未來重複 save mission，可能覆蓋人工補充或 runtime 產出。
- task 主要寫 JSON log，`TASKS.md` 目前沒有同步更新。
- decision 主要由 API provider payload 的 `decisions` 附加到 `DECISIONS.md`，不是完整 decision object lifecycle。
- retrieval 目前只取 `Wiki/*.md` 前六個檔案，每個最多 6000 字，還沒有索引、排序、任務相關性或引用來源權重。

### 3.5 Memory UI

目前 UI 已有：

- Memory page:
  - 顯示 wiki pages
  - 顯示 recent runs

- Decisions page:
  - 從 mission `DECISIONS.md` 抽取 `- ` 開頭項目
  - 顯示 audit events

- Mission detail:
  - 顯示 report、status、PM report、tasks file、run records、changed files、usage

這已經能展示「公司記憶屬於 workspace」的概念。下一步應把它從「檔案列表」升級成「可被 Praetor 主動維護的公司記憶」。

## 4. 目前使用者流程

### 4.1 First-time setup

入口：

- `/app/welcome`
- `/app/praetor`

若尚未初始化，`/app/praetor` 顯示六步 onboarding wizard：

1. owner name / email / password / company language
2. leadership style / decision style / organization style / autonomy / risk priority
3. workspace root
4. runtime mode / provider / model / executor
5. require approval categories
6. summary and initialize

完成後：

- 建立 workspace
- 建立 settings
- 建立 auth record
- 建立 company DNA
- 建立 governance policy
- 建議 roles
- 自動登入 owner session
- audit: `onboarding_completed`

### 4.2 Login / protected UI

目前有：

- owner password login
- session cookie
- CSRF token
- setup token for onboarding
- optional login requirement
- basic login rate limiter in production

API 與 UI 的 protected behavior：

- 未初始化時允許 onboarding。
- 初始化後如果 require login，UI route 會導向 `/app/login`。
- 已登入 API write request 需要 CSRF，除了 login / onboarding complete。

### 4.3 Mission creation

使用者在 `/app/praetor` 或 API 建立 mission：

欄位：

- title
- summary
- domains
- priority
- requested_outputs

系統會計算：

- complexity_score
- pm_required
- escalation_reason
- manager_layer: `pm_auto` 或 `praetor_direct`

若 PM required，會附加 PM report：

- complexity score
- escalation reason
- PM owner created

目前 mission creation 偏表單式，還沒有真正「AI CEO 與使用者對話後生成 mission plan」。

### 4.4 Mission run

使用者在 mission detail 按 `Run mission`。

目前執行流程：

1. mission status -> `active`
2. 建立 `MissionRuntime`
3. 根據 settings runtime 選擇：
   - `api`
   - `subscription_executor`
4. 執行後寫 task log 與 bridge run
5. 若 API failure 且有 executor，或 executor failure 且有 provider，嘗試 fallback
6. 根據 normalized status 更新 mission status
7. append `REPORT.md`
8. 若 PM required，append `PM_REPORT.md`
9. append audit event
10. 若需要 owner action，建立 approval request

目前 status mapping：

- `completed` -> `completed`
- `paused_budget`, `paused_decision`, `paused_risk`, `interactive_approval_required` -> `waiting_approval`
- `auth_required` -> `paused`
- others -> `failed`

### 4.5 API mode

API mode 目前支援：

- OpenAI chat completions
- Anthropic messages
- configurable base URL

API prompt 要求模型回傳 JSON：

- `summary`
- `files`
- `decisions`
- `notes`

系統會：

- 從 `Wiki/*.md` 收集 retrieval preview
- 讓 provider 產生 files/decisions
- 檢查 write allowlist/denylist
- 寫入檔案
- append decisions
- 建立 run record

目前限制：

- 沒有實作 budget enforcement，只記錄 budget fields。
- 沒有明確支援 streaming 或 background progress。
- API payload parse 若模型回傳非 JSON，會失敗。
- `notes` 目前沒有完整寫入產品 surface。

### 4.6 Subscription executor mode

subscription executor mode 透過 host bridge：

- API app -> `BridgeClient`
- `praetor-execd` -> `RunManager`
- `CodexRunner` 或 `ClaudeCodeRunner`
- host-side CLI tool 執行
- bridge 追蹤 changed files、stdout/stderr、usage、normalized status

安全邊界：

- bearer token
- path mapping
- allowed roots / deny roots
- no arbitrary binary path
- limited env forwarding
- non-interactive executor mode

目前限制：

- app runtime 固定 target workdir 為 `Projects/<mission title with underscores>`。
- input_files 目前為空，mission context 沒有完整傳給 executor。
- approval policy 固定 `allow_shell: false`, `allow_destructive_write: false`。
- approval 被建立後不會回寫下一次 run 的 policy。

### 4.7 Approval flow

目前 approval 可以：

- runtime 自動建立
- 使用者在 mission detail 手動建立
- Executive Rail 顯示 pending approvals
- 使用者 approve/reject
- audit `approval_resolved`

但目前 approval resolution 只是狀態更新，不會：

- resume mission
- retry run
- unlock shell/destructive write
- extend budget
- write decision record
- trigger new task plan

這是產品信任敘事的最大短板之一，因為「stop at checkpoint」已經有，但「批准後可治理地繼續」還沒有。

### 4.8 Meeting flow

目前可以建立 review meeting：

- type: `project_review`
- participants: Praetor / Project Execution / Reviewer
- agenda fixed
- outputs 根據 mission status、task count、latest run、report excerpt 產生
- 寫入 mission `meetings`
- append PM report

這是一個好的雛形，但目前更像 summary generator，不是真正 decision meeting 或 planning loop。

## 5. 對照開源成功定位的差距

### 5.1 已經符合定位的部分

目前已經有幾個很適合拿來行銷的真實基礎：

- local-first workspace
- self-hostable Docker / Pixi
- owner account
- setup-token / CSRF / production secret guard
- company DNA
- governance policy
- role definitions
- mission folders
- report / decisions / PM report
- audit log
- API model mode
- Codex / Claude Code bridge mode
- changed files tracking
- runtime health / usage summary
- mobile briefing skeleton

這些都支撐「不是一般 chatbot，而是 AI company operating system」。

### 5.2 目前不應過度宣稱的部分

對外行銷應避免過早宣稱：

- fully autonomous AI company
- robust multi-agent orchestration
- production-ready background worker queue
- advanced memory retrieval
- marketplace / plugin ecosystem
- enterprise governance
- rich approval resume semantics
- local model fully implemented

目前比較準確的說法：

> Praetor is an early local-first AI company command center with mission-based execution, company memory files, governance settings, and support for API models or host-side coding executors.

### 5.3 開源 demo 最該展示的能力

最強 demo 應該是：

> Ask Praetor to prepare this repo for an open-source v0.1 release.

展示順序：

1. 初始化公司 workspace。
2. 設定 approval boundaries。
3. 建立 mission：prepare v0.1 open-source release。
4. Praetor 讀 wiki/context。
5. 產出 release checklist / docs / project status。
6. 透過 Codex 或 API mode 寫入 workspace。
7. 顯示 changed files。
8. 顯示 report、decisions、audit、usage。
9. 遇到高風險行為時建立 approval checkpoint。

這個 demo 比「多 agent 自動工作」更可信，因為它正好展現 Praetor 現在已經有的優勢。

## 6. 後續產品規格

### 6.1 P0: 開源可信 MVP

目標：

讓一個陌生開發者 clone repo 後，在 30 分鐘內完成第一個有價值 mission，並理解 Praetor 的差異。

必須完成：

- 穩定 quickstart
- sample workspace
- fake provider / dry-run mode
- first mission template
- demo script
- README 重寫成產品導向
- onboarding 預設 workspace 不應是 `/tmp/praetor-workspace`
- mission run 需要更清楚顯示「下一步建議」
- approval 被 approve 後至少要產生明確 next action

驗收：

- 新使用者照 README 可完成 onboarding
- 不需要真 API key 也能跑完 demo
- demo mission 會產生可檢查的 markdown output
- UI 能看見 report / decisions / changed files / audit

### 6.2 P1: Memory 產品化

目標：

讓 company memory 成為 Praetor 的核心賣點，而不是只是 wiki file list。

需求：

- `Wiki/Company.md` 顯示為 Company Memory
- `Wiki/Strategy.md` 顯示為 Strategy Memory
- `Wiki/Decision Log.md` 與 mission decisions 同步
- mission 完成後產生 memory update proposal
- approval 後才寫入長期 company memory
- retrieval preview 顯示「使用了哪些 memory」
- 每次 run 的 prompt context 保存摘要

驗收：

- 使用者能看到 Praetor 為什麼引用某段 memory
- mission report 能提出 memory update
- decision 不只是一行 markdown，而有狀態、owner、impact、source mission

### 6.3 P2: Approval resume semantics

目標：

讓「停在正確檢查點」變成真的 workflow。

需求：

- approval category 對應下一次 run policy
- approve once / approve for mission / reject 實際影響 runtime
- budget approval 可延長 budget
- shell command approval 可讓下一次 run `allow_shell=true`
- destructive write approval 可針對 specific path 解鎖
- rejected approval 應寫入 decision/audit，並讓 mission 回到 review 或 failed-safe 狀態

驗收：

- mission 因 approval 停下
- owner approve
- mission 可以繼續
- audit 可追蹤批准前後的 policy change

### 6.4 P3: True CEO planning layer

目標：

讓使用者不是填 mission form，而是和 Praetor 定義目標，由 Praetor 建立 mission plan。

需求：

- Praetor page 支援 founder brief input
- 產生 mission plan:
  - objective
  - roles
  - tasks
  - context needed
  - expected outputs
  - checkpoints
  - risk flags
- user approve plan 後才開始 run
- PM required 不只是 complexity flag，而是真的產生 mission-scoped context

驗收：

- 使用者輸入一段自然語言
- Praetor 產生可讀 plan
- 使用者批准後轉成 mission/task files
- mission detail 顯示 role responsibilities 與 task sequence

### 6.5 P4: Background worker

目標：

把 mission execution 從 API request 中移出，支援長任務與 UI progress。

需求：

- worker 接管 run queue
- API 只建立 mission/run request
- UI polling 或 server-sent events
- run cancel 真正連到 bridge cancel
- worker crash 後可從 mission folder 恢復狀態

驗收：

- 按 Run 後 UI 不 block
- 任務執行中可刷新頁面
- status / events 持續更新
- worker restart 後不丟 mission state

### 6.6 P5: Open-source packaging

目標：

讓 Praetor 能被開源社群理解、安裝、展示、貢獻。

需求：

- `examples/`
  - sample workspace
  - sample mission
  - expected output screenshots or markdown

- docs:
  - quickstart
  - concept guide
  - architecture for contributors
  - executor bridge setup
  - security model
  - troubleshooting

- community:
  - issue templates
  - contribution guide
  - roadmap labels
  - good first issues

驗收：

- README 第一屏能講清楚：what / why / demo / quickstart
- 新 contributor 知道可貢獻 role templates、mission templates、executor adapters、docs
- 不需要讀完整 spec 才知道 Praetor 是什麼

## 7. 行銷與產品訊息規格

### 7.1 首頁與 README 應強調

核心訊息：

> Stop managing many AI agents. Run work through one AI CEO.

輔助訊息：

- Define goals, roles, memory, and approval boundaries.
- Praetor delegates execution and stops when your judgment is needed.
- Your company memory lives in local files.
- Use API models or your existing Codex / Claude Code subscription.

### 7.2 避免使用的訊息

避免：

- "fully autonomous"
- "enterprise-ready"
- "multi-agent platform"
- "no-code workflow builder"
- "replaces your team"

原因：

這些字會把 Praetor 放進過度擁擠或目前實作還無法支撐的市場敘事。

### 7.3 推薦 demo mission

Demo mission:

Title:

> Prepare this repository for an open-source v0.1 release

Summary:

> Review the current repository, produce a release readiness report, update the project status, identify trust/security gaps, and recommend the next three contributor-friendly issues.

Requested outputs:

- `/workspace/Projects/PraetorRelease/RELEASE_READINESS.md`
- `/workspace/Projects/PraetorRelease/NEXT_ISSUES.md`
- `/workspace/Wiki/Strategy.md`

展示重點：

- local files are memory
- mission produces real artifacts
- governance boundaries are visible
- changed files are inspectable
- Praetor summarizes and escalates

## 8. 建議執行順序

### Milestone A: Sharpen the demo

1. 建立 `examples/praetor-release-workspace`
2. 建立 demo mission template
3. 加入 fake provider / deterministic demo mode
4. 修改 README quickstart 指向 demo
5. 錄製 3 分鐘 demo script

### Milestone B: Fix memory overwrite risk

1. `save_mission` 不再每次覆蓋 markdown memory files
2. 初次建立與更新 mission metadata 分離
3. `TASKS.md` 與 task JSON log 同步 append
4. decisions 建立 structured record

### Milestone C: Approval becomes real

1. approval resolution 寫入 mission decision
2. approval status 影響 next run policy
3. mission waiting approval -> approved continuation
4. UI 顯示 approved scope

### Milestone D: CEO planning

1. Founder brief input
2. Praetor plan preview
3. User approves plan
4. Plan materializes into mission/tasks/context

### Milestone E: Background execution

1. worker queue
2. run event polling
3. cancel/resume
4. restore from filesystem state

## 9. 成功指標

### 開源採用指標

- 30 分鐘內完成 first mission
- 10 個外部使用者成功跑 demo
- 5 個外部使用者願意留下 workspace/output feedback
- README conversion: clone -> run -> mission complete
- GitHub issues 中開始出現真實使用案例

### 產品價值指標

- 使用者是否真的少開多個 AI 對話視窗
- 使用者是否回來看 mission report / decision log
- 使用者是否願意把第二個專案交給 Praetor
- approval checkpoint 是否增加信任而不是增加負擔
- memory 是否讓下一次 mission 更省心

### 商業化指標

- 是否有人願意使用 hosted private beta
- 是否有人願意為 managed setup 付費
- 是否有人願意為 always-on worker / backup / team features 付費
- 是否有人要求 GitHub / Slack / Linear integration

## 10. Product truth table

| 能力 | 目前狀態 | 對外可說法 | 下一步 |
|---|---|---|---|
| Local-first workspace | 已實作 | 可強調 | 補 sample workspace |
| Company memory | 基礎已實作 | 可強調但避免過度 | memory update lifecycle |
| AI CEO | UI/文案/服務雛形 | 可作定位 | CEO planning layer |
| Roles | model/onboarding 已有 | 可說 role-first | role-to-task orchestration |
| Hidden PM | complexity flag / PM report | 可說 early PM layer | mission-scoped PM context |
| Approvals | 建立/顯示/解決 | 可說 checkpoint tracking | approve 後 resume semantics |
| API mode | OpenAI/Anthropic 已有 | 可說 BYO API key | better JSON recovery / streaming |
| Subscription executor | Codex/Claude bridge 已有 | 可強調 | richer context + policy bridge |
| Worker | health/status stub | 不應主打 | real background queue |
| Local model | compose 有 Ollama profile | 不應主打 | runtime implementation |
| SaaS readiness | 尚未 | 不應主打 | hosted beta architecture |

## 11. 決策

1. Praetor 的開源 wedge 是「一個 AI CEO 管理多角色工作」，不是「更多 agent」。
2. 第一個公開 demo 必須聚焦 software repo / release readiness，因為目前 codebase 最適合這個場景。
3. v1 不應追 enterprise、多使用者、marketplace、複雜 workflow builder。
4. 記憶與 approval 是信任核心，應優先於增加更多 integrations。
5. Worker queue 是產品可用性必要條件，但在 public demo 前可以先以同步 flow 展示。
6. README 與 website 應用真實能力說話，不要用超出目前實作的 autonomy 敘事。

## 12. 下一步 checklist

- [ ] 建立 demo workspace 與 demo mission template
- [ ] 補 fake/dry-run provider，讓無 API key 使用者能完成 demo
- [ ] 修正 `save_mission` 覆蓋 markdown 檔案的風險
- [ ] 讓 `TASKS.md` 跟 task log 同步
- [ ] 讓 approval approve/reject 寫回 mission decision
- [ ] 定義 approval -> next run policy mapping
- [ ] 新增 founder brief -> mission plan preview
- [ ] 更新 README 第一屏與 quickstart
- [ ] 建立 contributor guide 與 issue templates
- [ ] 規劃 worker queue 接管 mission execution
