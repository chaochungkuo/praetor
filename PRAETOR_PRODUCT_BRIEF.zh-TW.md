# Praetor 產品綜合文案 v0.1

狀態：整合稿

這份文件是根據目前所有討論材料整理出的第一版完整產品文案。

它的目的不是把所有細節永久定死，而是把下面三件事講清楚：
- 方向已經穩定到什麼程度
- 哪些設計判斷應該當成產品核心
- 哪些地方仍然可以彈性調整

## 1. 一句話先講清楚

`Praetor` 是一個給一人公司、solo founder、indie builder 使用的本地優先 AI 公司操作系統。

它不是一般 chatbot，不是 workflow builder，也不是單純的 multi-agent framework。

它的核心承諾是：

**你只需要像老闆一樣管理方向、責任與決策；Praetor 會像 AI CEO 一樣組織角色、推進任務、使用公司記憶、並在正確的時間停下來請你決策。**

## 2. 這個產品到底在解什麼問題

這個產品在解的，不只是「AI 幫你做事」。

它真正解的是：

**一個人如何有效管理一個 AI 團隊，而不被細節壓垮。**

典型目標使用者通常同時扮演：
- CEO
- PM
- researcher
- operator
- developer
- finance owner
- reviewer

真正的痛點不是能力不足，而是：
- 注意力被切碎
- 上下文一直切換
- 很多小決策不值得親自處理，卻又不能完全放掉
- 工具很多，但沒有一個清楚的「組織層」
- AI 很會回答，但不一定會在可控範圍內持續工作

所以 Praetor 的價值不只是 automation，而是：

**把角色與執行層外包給 AI，同時保留老闆該有的控制權。**

## 3. Praetor 是什麼，不是什麼

### 3.1 Praetor 是什麼

Praetor 是：
- 一個 founder-facing 的 AI 指揮中心
- 一個 role-based 的 AI 公司組織系統
- 一個 local-first / self-hosted 的工作系統
- 一個以治理、授權與記憶為核心的 AI runtime
- 一個用檔案系統當工作空間、用 Wiki 當長期記憶的產品

### 3.2 Praetor 不是什麼

Praetor 不是：
- 通用型 multi-agent playground
- 拖拉式 workflow 畫布產品
- 純 developer framework
- 普通的 AI chat app
- 一開始就瞄準企業 IT 治理的大型平台

## 4. 穩定方向與可彈性項目

### 4.1 已經足夠穩定的方向

以下判斷已經可以當成產品核心：

- 使用者主要互動對象是 Praetor，不是一堆平等 agent。
- 使用者操作的核心抽象是 `Role`，不是 `Agent`。
- 記憶屬於公司，不屬於個別 agent。
- MVP 不應該做 agent personal memory。
- 檔案系統是公司資料與記憶的主要真相來源。
- 產品必須容易部署，最好 Docker 起來就能用。
- UI 必須是 browser-first。
- 權限邊界、approval、checkpoint、可追溯性必須是第一級功能。
- 產品必須支援不只一種 AI runtime。
- 使用者應該可以很快感受到「今天就能開始有進展」。

### 4.2 仍然可以調整的部分

以下目前仍可彈性調整：
- 前後端拆分方式
- repo 實際結構
- 第一版哪些 UI 頁面獨立，哪些先合併
- 第一版內建幾種組織模板
- PM 自動產生的 threshold
- GitHub skill ecosystem 何時引入
- 視覺品牌風格細節

## 5. 市場位置與現有產品差異

截至 2026 年 4 月 24 日，現有產品已經很多，但它們大多分屬不同類別。

### 5.1 現有工具各自擅長什麼

`ChatGPT / Codex`
- 對話與任務協助強
- coding 與 delegated tasks 很強
- 可以在 app、CLI、IDE、cloud 上工作
- 但主要仍然是 assistant / coding agent surface

`Dify`
- 視覺化 workflow / chatflow builder
- 適合把 AI 做成應用或流程

`Flowise`
- 視覺化 AI agent / LLM workflow builder
- 偏 builder 工具與 flow 編排

`LangGraph`
- 偏低階 orchestration runtime
- 適合工程師打造長任務、stateful agent 系統

`CrewAI`
- 多 agent team、workflow、enterprise automation
- 偏 framework / orchestration 平台

### 5.2 Praetor 要打的不是同一場仗

Praetor 不需要和這些工具比誰更像 workflow builder，也不需要比誰更像 agent framework。

Praetor 的真正差異化是：

**把 AI 從「會做任務的工具」提升成「有治理、有分工、有記憶、有決策節點的公司組織」。**

市場上仍然相對缺少的是：
- founder-facing 的 AI command center
- role-first 而不是 agent-first 的產品
- local-first + file-native 的公司工作系統
- 公司級記憶與顯式決策紀錄
- 對「帶著自己已經付費的 AI 訂閱來用」有一級支援的產品

### 5.3 差異總結

| 類型 | 主要抽象 | 使用體驗 | Praetor 的差異 |
|---|---|---|---|
| ChatGPT / Codex | 對話或單次委派任務 | 助手 / coding agent | 沒有持續的公司治理模型 |
| Dify / Flowise | flow / graph / app | builder canvas | 不是 founder command center |
| LangGraph | agent runtime | developer framework | 對創辦人太低階 |
| CrewAI | agent team / workflow | 多 agent automation | 仍偏 framework / platform |
| Praetor | role + governance + company memory | 老闆視角的 AI 公司控制台 | 組織化、治理化、檔案原生 |

## 6. 為什麼這個產品有機會成立

Praetor 成立的關鍵，不在於「模型比別人更聰明」。

而在於它把真正麻煩的那一層做成產品：
- 組織
- 授權
- 可見性
- 記憶
- 決策節點
- 節奏控制

也就是說：

**現在 AI 的能力已經夠強，真正缺的是讓它能像一間公司那樣穩定運作的產品結構。**

## 7. 目標使用者

主要使用者：
- solo founder
- indie hacker
- freelancer
- consultant
- researcher
- creator with operational complexity
- 想要 leverage、但不想再多學一套很重系統的人

第一版不應該優先瞄準：
- 大型企業
- 多人協作複雜組織
- 需要完整 RBAC / SSO / compliance 的場景

## 8. 核心產品哲學

### 8.1 Files are the source of truth

公司真正的長期記憶與成果，應該存在：
- workspace folders
- wiki
- decisions
- missions
- project files

SQLite 可以存在，但只應該承擔：
- index
- cache
- UI 狀態
- 任務 metadata

不要讓真正的公司知識只存在於隱形資料庫裡。

### 8.2 User 管角色，不管人

使用者應該定義的是：
- 需要什麼角色
- 這個角色負責什麼
- 需要產出什麼
- 不能做什麼

使用者不應該管：
- agent 叫什麼名字
- personality 是什麼
- 用了哪些 prompt
- skill 怎麼配

### 8.3 治理不是附屬功能，而是產品本體

Praetor 的真正價值是：
- 誰可以決定
- 誰只能建議
- 什麼事情可以自動做
- 什麼事情一定要停下來問
- 什麼事情永遠不能做

### 8.4 記憶屬於公司，不屬於 agent

MVP 不應做：
- agent 自我記憶
- agent 關係網
- personality drift
- mood-like behavior

MVP 應該做：
- 公司級記憶
- 任務級記憶
- 可追溯的決策與執行紀錄

### 8.5 第一版就要讓人感覺完整

完整不代表功能很多。

完整代表：
- 安裝容易
- onboarding 清楚
- 第一天就能做事
- UI 有掌控感
- 輸出是實際可用的
- 邊界清楚

## 9. 核心使用者經驗

正確的心智模型是：

**Onboarding = 你和 Praetor 的第一場會議**

使用者應該感覺到：
- 我不是在填設定頁
- 我是在定義這家公司怎麼運作
- Praetor 在幫我翻譯成可執行的組織與流程

理想互動是：

使用者說：

`我想開始一個新專案`

Praetor 回：
- 我理解的目標是什麼
- 我打算怎麼做第一輪
- 哪些事情我可以自動處理
- 哪些地方我會停下來問你
- 我會用什麼角色結構推進

這裡的靈魂是：

**Praetor 決定怎麼跑，使用者決定方向與重要授權。**

## 10. Company DNA

`Company DNA` 是目前整個方向裡最強的一個設計點。

它應該在 onboarding 期間由 Praetor 引導產生，並落在：

`workspace/Wiki/Company/DNA.md`

它至少要定義：
- leadership style
- decision style
- organization style
- autonomy mode
- risk priority
- communication style
- operating principles

範例：

```yaml
company_dna:
  leadership_style: strategic
  decision_style: balanced
  organization_style: lean
  autonomy_mode: hybrid
  risk_priority: avoid_wrong_decisions
  communication_style: concise
  operating_principles:
    - default_to_action_escalate_when_uncertain
    - keep_roles_minimal_but_clear
    - document_important_decisions
    - avoid_unnecessary_user_interruption
```

這個設計的價值在於：

使用者定義文化與風格，系統依此生成組織與行為。

## 11. Role-Based Organization

Praetor 應該是 role-first。

使用者操作的最小單位應該是 `Role`，不是 `Agent`。

範例：

```yaml
role:
  name: Project Execution
  responsibility:
    - create_project_structure
    - maintain_project_status
    - organize_related_documents
  output:
    - project_folder
    - project_plan
    - status_updates
  constraints:
    - no_strategic_decisions
    - no_financial_actions
```

使用者只看這一層。

系統再做：
- role -> agent 形式
- role -> skill mapping
- role -> workflow placement

這會是 Praetor 相對於一般 multi-agent 產品最清楚的辨識點之一。

## 12. 組織層級

### 12.1 MVP 的正確層級

```txt
Owner
  ↓
Praetor（CEO 層）
  ↓
必要時產生的 PM / manager 層
  ↓
worker roles
  ↓
reviewer
  ↓
executors
```

### 12.2 為什麼這樣合理

這樣做的好處：
- 使用者只有一個穩定入口
- 內部可以隱藏複雜度
- 責任邊界清楚
- context 容易隔離

### 12.3 關鍵原則

**Hierarchy exists, but complexity is hidden.**

這句話很重要，因為它同時解決：
- UX 不要太複雜
- 系統又要能 scale

## 13. CEO Load Management

Praetor 不應該永遠硬扛全部 context。

當任務變大、token 過高、決策太密、mission 太多時，CEO 層應該有權建立 mission-scoped manager。

### 13.1 建立 PM 的觸發信號

建議納入：
- context token load
- estimated steps
- domain count
- active mission count
- blocked count
- decision queue size

示意設定：

```yaml
ceo_context:
  warning_at_tokens: 70000
  split_at_tokens: 90000

complexity:
  max_steps_without_pm: 5
  max_domains_without_pm: 1

organization:
  max_active_missions_per_ceo: 3

blocked:
  create_pm_after_blocked_count: 2
```

### 13.2 PM 的性質

PM 應該是：
- mission-scoped
- 功能性的 context owner
- 任務結束可解散或歸檔

而不是永久人格角色。

### 13.3 CEO 與 PM 的 context 分工

CEO 應該主要讀：
- Company DNA
- mission summaries
- PM reports
- pending owner decisions

PM 應該主要擁有：
- full mission history
- task breakdown
- local decisions
- execution logs
- detailed context

這是避免 context 爆炸的核心技術手段。

## 14. 記憶架構

推薦記憶模型如下。

### 14.1 Company Memory

共享、持久、可審核的公司記憶：
- Wiki
- Decisions
- Rules
- Project files
- SOPs

### 14.2 Task Memory

mission / task 級的工作記憶：
- input
- intermediate outputs
- notes
- review comments
- checkpoints

這些應該可歸檔，但不應污染 Wiki。

### 14.3 Agent Memory

MVP 建議：
- 不做 agent personal memory
- 不做 personality drift
- 不做 agent 關係模擬

理由：
- 更可控
- 更可重現
- 更好 debug
- 更符合 role-first 設計

### 14.4 一句最乾淨的記憶哲學

**不要讓 agent 記住事情，要讓公司記住事情。**

## 15. Skill 與 Capability Layer

Skill 不應該只是 prompt collection。

它應該是可執行能力。

例如：

```yaml
skill:
  name: create_project_structure
  description: create_standardized_project_folder
  input:
    - project_name
  output:
    - folder_created
  actions:
    - create_folder
    - create_files
    - write_markdown
```

### 15.1 技能分類

建議分成：
- core file skills
- knowledge skills
- execution skills
- external imported skills

例如：
- `file_read`
- `file_write`
- `create_folder`
- `update_markdown`
- `summarize_document`
- `extract_info`
- `generate_plan`
- `run_codex`
- `run_claude_code`
- `run_script`

### 15.2 Marketplace 時機

GitHub skill ecosystem 的方向是好的，但不應該進 MVP。

建議節奏：
- MVP：只做內建 skills
- Phase 2：enable/disable、custom import
- Phase 3：GitHub skill ecosystem

## 16. AI Runtime Modes

這是產品非常核心的決策。

Praetor 應該支援三種模式。

### 16.1 API Mode

直接使用 provider API：
- OpenAI API
- Anthropic API
- Gemini API

適合：
- 最穩定的後端整合
- 可預測的 production 行為

### 16.2 Local Mode

使用本地模型：
- Ollama
- 之後可擴展其他 local runtimes

適合：
- privacy-first
- 本地試驗
- 低外部依賴

### 16.3 Subscription Executor Mode

使用使用者已登入、已付費的工具：
- Codex CLI
- Claude Code
- OpenClaw-style executors

適合：
- 已經有既有 AI 訂閱的 power users
- coding-heavy 任務
- 避免額外 API 成本

限制：
- 不應作為「純 Docker 一鍵即用」的預設路線
- 需要額外的 host-side executor bridge
- v1 僅正式支援 `Local-only` 與 owner-controlled `Remote private`

### 16.4 為什麼這個設計很重要

這不是小細節，這會直接影響產品吸引力。

Praetor 可以說：

**Bring your own AI. Praetor 提供的是組織、治理、記憶與工作流程。**

## 17. Executor Abstraction

Praetor 不應該假設只有一種執行方式。

推薦抽象：

```yaml
ai_runtime:
  mode: api | local_model | subscription_executor
  transport: builtin | host_bridge

executors:
  codex:
    enabled: true
    requires_user_login: true
    workspace: /workspace
  api:
    enabled: false
  local:
    enabled: false
```

這一層至少要定義：
- task spec input
- allowed workspace scope
- approval mode
- expected outputs
- logs
- exit state

如果這層設計清楚，Praetor 才能同時支援：
- API-driven 工作
- Codex / Claude / OpenClaw 這類 executor-driven 工作

## 18. 部署模型

Praetor 應該至少支援兩種主要部署方式。

但安裝路線應明確拆成兩條：

### 18.0 官方安裝路線

#### A. Quick Start

目標：
- 讓第一次接觸 Praetor 的人最快啟動
- 不要求額外安裝 host bridge
- 優先對應 `api` 或 `local_model`

體驗：
- `docker compose up -d`
- 打開瀏覽器
- 建立 owner account
- 完成 onboarding

#### B. Bring Your Own Subscription

目標：
- 讓已經在用 Codex / Claude Code 的使用者沿用既有訂閱

體驗：
- 安裝 Praetor Docker stack
- 在宿主機安裝並登入 `codex` 或 `claude`
- 啟動 host executor bridge
- 在 onboarding 選擇 `subscription_executor`

### 18.1 本機部署

使用者只要：

```bash
docker compose up -d
```

然後打開：

`http://localhost:3000`

對於 Quick Start，建議預設使用：
- `api`
- 或 `local_model`

對於 `subscription_executor`：
- 不是單純 `docker compose up -d` 就完成
- 還需要宿主機 executor bridge

### 18.2 Remote self-hosted

部署到 VPS / server：
- HTTPS reverse proxy
- auth enabled
- persistent workspace volume
- persistent config and state

v1 的正式支援判斷：
- `Remote private`：可支援 `api`、`local_model`、`subscription_executor`
- `Remote public`：主打 `api`
- `Remote public + subscription_executor`：v1 不列為正式支援路線

關鍵原則：

**local-first，不代表 local-only。**

## 19. Workspace 模型

建議 workspace 長這樣：

```txt
workspace/
├── Inbox/
├── Wiki/
├── Projects/
├── Finance/
├── Operations/
├── Development/
├── Decisions/
├── Missions/
└── Archive/
```

各區角色：
- `Inbox`：使用者丟原始資料
- `Wiki`：長期公司記憶
- `Projects`：長期成果
- `Decisions`：治理與決策紀錄
- `Missions`：任務級上下文
- `Archive`：已關閉內容

Mission 建議再做自己的結構：

```txt
workspace/Missions/<mission_id>/
├── MISSION.md
├── STATUS.md
├── TASKS.md
├── DECISIONS.md
├── CONTEXT.md
├── REPORT.md
└── logs/
```

## 20. 安全與治理

Praetor 的安全模型必須是顯式的，不能只靠 prompt。

### 20.1 Writable Scope

系統預設不應該能編輯整台電腦。

建議：

```yaml
permissions:
  allow_read:
    - /app/workspace
  allow_write:
    - /app/workspace/Projects
    - /app/workspace/Wiki
    - /app/workspace/Decisions
    - /app/workspace/Missions
  deny_write:
    - /app/workspace/Archive
```

### 20.2 Approval 分級

系統至少要區分：
- auto-allowed
- batch report
- approval-required
- never-allowed

高風險例子：
- delete files
- overwrite important documents
- spend money
- send external messages
- run shell commands
- change strategy

### 20.3 Governance 要是 UI 一等公民

這些東西不能只躲在 config 裡。

使用者應能看到與調整：
- autonomy mode
- approval rules
- checkpoint policy
- role definitions
- executor policy

## 21. Onboarding

Onboarding 應該是對話式的，不是設定導向的。

正確心智模型：

**Onboarding 是你和 Praetor 的第一次建立公司會議。**

### 21.1 建議流程

1. owner account bootstrap
2. 語言
3. 領導風格
4. 決策風格
5. 組織風格
6. autonomy 偏好
7. risk preference
8. runtime mode
9. executor connection step（conditional）
10. workspace path
11. company template
12. approval boundaries
13. first mission

說明：
- `Local-only` 仍應建立 owner account
- 差別只在於 trusted local device 可以降低後續摩擦
- runtime 若選 `subscription_executor`，onboarding 應檢查 host bridge 與 executor login 狀態

### 21.2 為什麼這樣設計

好的 onboarding 要完成三件事：
- 建立信任
- 建立公司 identity
- 立刻產生 momentum

onboarding 結束時，使用者應該已經擁有：
- 一個 workspace
- 一份 Company DNA
- 一個初始角色結構
- 一個清楚的 first mission

## 22. 使用者介面

Praetor 的 UI 應該像：
- 公司指揮中心
- 董事長控制台
- AI 公司 operating console

而不應該像：
- 純聊天工具
- debug console
- node graph 編輯器

### 22.1 主導航

建議：
- CEO
- Overview
- Tasks
- Meetings
- Memory
- Models
- Settings

### 22.2 整體布局

推薦 shell：
- 左側導覽
- 中央主工作區
- 右側 context panel
- 上方 top bar 顯示 runtime / alerts / decisions

### 22.3 CEO Page

這會是最主要操作面。

應包含：
- summary briefing
- CEO chat
- pending decisions
- suggested actions
- escalation queue

### 22.4 Overview

董事長視角總覽：
- active projects
- blocked items
- deadlines
- recent outputs
- tasks running
- waiting for owner decisions

### 22.5 Tasks

任務頁要透明，但不能噪音太大。

需要支援：
- board view
- list view
- task detail
- checkpoint actions
- status history
- outputs
- logs

### 22.6 Meetings

會議不是聊天室，而是結構化 review space。

輸出要偏向：
- summary
- risks
- decisions needed
- next actions

### 22.7 Memory

應暴露：
- Wiki
- Decisions
- source files
- retrieval preview

`Retrieval Preview` 很重要，因為它會直接提高信任感。

### 22.8 Models

Models page 應該是一級頁面，不要塞進 settings。

至少要看得到：
- current runtime mode
- active models / executors
- token usage
- estimated cost
- provider breakdown
- executor activity
- budget 與 fallback policy

### 22.9 Settings

建議分組：
- General
- Governance
- Workspace
- Roles
- AI / Executors
- Security
- Advanced

## 23. 速度、Checkpoint 與 Run Budget

Praetor 的節奏政策應該是：

**AI 在正確的時間等人，人不應該每個小步驟都在等 AI。**

### 23.1 Run Budget

每個 mission 都應有清楚 budget：

```yaml
run_budget:
  max_steps: 20
  max_tokens: 100000
  max_time_minutes: 30
  max_cost_eur: 2.00
```

### 23.2 Stop Conditions

主要停止條件：
- token / cost budget reached
- decision checkpoint
- risk checkpoint
- mission completion

### 23.3 Default Autonomy Policy

推薦：

```yaml
autonomy_policy:
  low_risk_tasks: auto_continue
  medium_risk_tasks: report_after_batch
  high_risk_tasks: require_approval
```

這樣可以解決你對「Codex 一直停下來問」的反感，同時保留必要邊界。

### 23.4 UI 控件

AI 暫停時，UI 應提供：
- Continue
- Continue with larger budget
- Stop
- Ask Praetor

### 23.5 預設速度模式

建議三種：
- Careful
- Balanced
- Fast

預設應為 `Balanced`。

## 24. 技術架構建議

### 24.1 Frontend

推薦：
- Next.js 或 React app
- browser-first
- responsive
- 強 dashboard / task UI

### 24.2 Backend

推薦：
- Python runtime
- FastAPI 做 API layer

理由：
- 檔案系統處理順
- AI provider / document handling 比較自然
- executor integration 比較好做

### 24.3 核心 runtime 子系統

建議至少包含：
- governance engine
- mission runtime
- role-to-agent mapper
- executor adapter layer
- memory retrieval layer
- audit / logging layer

### 24.4 Storage

建議：
- filesystem：公司真相
- SQLite：operational metadata
- JSONL / structured logs：traceability

### 24.5 邏輯模組切法

```txt
backend/
├── api/
├── governance/
├── runtime/
├── roles/
├── executors/
├── memory/
├── missions/
├── models/
└── storage/
```

這是邏輯切分，不代表 repo 一定要長這樣。

## 25. 可擴展性

Praetor 的擴展不應該是「讓使用者看到更多複雜度」。

它應該是：

### 25.1 人類視角的可擴展

即使 mission 變多、PM 增加、executors 增加，使用者仍只看到一個穩定 executive interface。

### 25.2 技術上的可擴展

透過以下手段 scale：
- mission-scoped context
- hidden PM 層
- modular executors
- explicit run budgets
- summarized upward reporting

### 25.3 產品上的可擴展

產品越來越強，但不應越來越難懂。

## 26. 什麼會讓使用者第一天就有感

這一點非常重要。

使用者要立刻感覺到：

**Praetor 不是概念，而是真的開始幫我工作。**

推薦的 day-1 立即有感場景：

### 26.1 Create Project

輸入：
- `Create a new project for X`

輸出：
- project folder
- project plan
- status page
- tasks page

### 26.2 Review Inbox

輸入：
- 丟原始資料到 `Inbox`

輸出：
- summaries
- extracted facts
- suggested actions
- mission proposals

### 26.3 Build Company Wiki

輸入：
- onboarding 答案
- 現有檔案

輸出：
- DNA
- strategy
- operating principles
- decision log

### 26.4 Update Status

輸入：
- 現有 project files

輸出：
- refreshed status
- highlighted blockers
- next decisions

這些都會在 workspace 產生真實可見成果，所以很有感。

## 27. 什麼會讓產品感覺完整

完整不等於大。

Praetor 要讓人覺得完整，至少需要：
- 清楚 onboarding
- 可用 dashboard
- 可工作的 CEO interface
- 可見的 tasks 與 decisions
- 清楚記憶模型
- model/token/cost visibility
- 真實文件輸出
- 安全邊界
- 暫停與繼續的清楚節奏

如果這些都在，即使 integrations 還不多，產品也會有完成度。

如果這些不在，功能再多都會像 demo。

## 28. 主要風險與應對

### 28.1 風險：產品變太廣

應對：
- 堅持 MVP 收斂
- 不要一開始做 enterprise features
- 不要把所有構想都塞進 v1

### 28.2 風險：CEO 層變成瓶頸

應對：
- hidden PM creation
- mission-scoped context
- load-based delegation

### 28.3 風險：全靠 prompt magic

應對：
- 顯式 governance rules
- mission files
- logs
- executable skills

### 28.4 風險：使用者不信任系統

應對：
- retrieval preview
- task logs
- run budgets
- approvals
- file change visibility

### 28.5 風險：成本與 token 感覺不可控

應對：
- model page
- budget controls
- executor selection
- per-task policy

### 28.6 風險：coding executor 一直中斷

應對：
- run budget policy
- PM-managed batch execution
- meaningful checkpoints only

## 29. 建議 MVP 範圍

Praetor 第一版不應該做整個宇宙。

推薦 MVP：
- Docker deployment
- browser UI
- conversational onboarding with Praetor
- company DNA generation
- role-based internal organization
- CEO page
- overview page
- tasks page
- settings page
- workspace filesystem
- wiki memory
- mission/task logging
- approval rules
- API mode
- 至少一種 executor mode
- 3 到 5 個 built-in use cases

推薦 MVP use cases：
- create project
- organize workspace
- review inbox
- build company wiki
- update project status

## 30. 建議的建置順序

### Phase 1

- product spec
- repo structure
- workspace model
- governance model
- company DNA
- role schema

### Phase 2

- onboarding
- Praetor interaction layer
- mission runtime
- task pages
- file outputs

### Phase 3

- executor abstraction
- API mode
- subscription executor mode
- model usage page

### Phase 4

- hidden PM creation
- meetings
- retrieval preview
- skill tuning

### Phase 5

- GitHub skill import
- richer executor ecosystem
- advanced role tuning

## 31. 最後收斂成一句產品命題

最強的版本可以寫成：

**Praetor 是一個 founder-facing 的 AI 公司指揮中心。**

它給一個人：
- AI executive layer
- governed organization of roles
- company-owned memory
- bounded autonomy
- safe execution in a controlled workspace

使用者不設定 agents。

使用者定義的是：
- direction
- culture
- responsibilities
- approvals

Praetor 定義的是：
- organization
- delegation
- execution flow
- skill use
- escalation timing

## 32. 最後的產品建議

目前這條產品方向是強的。

它強的原因不是它有很多 agent，而是它在正確的地方很有主見：
- founder-first
- Praetor-centered UX
- role-first abstraction
- company memory over agent memory
- self-hosted and local-first
- multi-runtime support
- visible governance

接下來最重要的，不是再擴散想法。

而是守住核心，不讓產品稀釋。

真正的核心不是：

`很多 agent`

而是：

**一間有結構、有記憶、有治理，而且 solo founder 真的能每天使用的 AI 公司。**

## 33. 參考來源

市場定位部分有用官方資料做交叉確認，基準日期為 2026 年 4 月 24 日：

- [Dify workflow / chatflow docs](https://docs.dify.ai/en/use-dify/build/workflow-chatflow)
- [Flowise introduction docs](https://docs.flowiseai.com/)
- [LangGraph overview docs](https://docs.langchain.com/oss/python/langgraph)
- [CrewAI introduction docs](https://docs.crewai.com/introduction)
- [OpenAI Codex overview](https://platform.openai.com/docs/codex/overview)
- [OpenAI：Using Codex with your ChatGPT plan](https://help.openai.com/en/articles/11369540/)
- [OpenAI：Introducing the Codex app](https://openai.com/index/introducing-the-codex-app/)
- [Anthropic Claude Code overview](https://docs.anthropic.com/en/docs/claude-code/overview)
