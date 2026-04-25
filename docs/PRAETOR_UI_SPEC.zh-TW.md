# Praetor UI / UX 規格 v0.1

狀態：設計稿

這份文件定義 Praetor 的整體 UI、資訊架構、主要頁面、互動模型、信任建立設計，以及如何在「掌控感」與「不被細節淹沒」之間取得平衡。

## 1. 核心 UX 目標

Praetor 的 UI 不是 agent playground，也不是 workflow builder。

它應該讓使用者感覺自己在使用：
- 董事長控制台
- AI CEO 指揮台
- 公司決策與執行總覽

使用者要同時獲得三種感受：
- 我知道公司在發生什麼
- 我不用自己盯每個細節
- 關鍵時刻我有最終決策權

## 2. UX 核心原則

### 2.1 只和 Praetor 對話

預設互動路徑應是：

`User -> Praetor -> internal roles`

不是：

`User -> worker agents directly`

### 2.2 先摘要，再展開

所有頁面先給：
- summary
- decisions needed
- risk
- next step

之後再允許使用者下鑽細節。

### 2.3 決策不能藏太深

任何需要使用者批准的事情都必須：
- 顯眼
- 可追溯
- 能快速處理

### 2.4 透明，但不噪音

使用者能查到：
- 誰在做
- 做到哪
- 用了什麼 model / executor
- 產出什麼

但首頁不應該變成 log wall。

### 2.5 讓 CEO 在所有事情裡，但不把所有事情都丟給使用者

Praetor 應該 system-wide involved。

但 UI 上只應該呈現：
- Praetor 認為你需要知道的內容
- 以及你主動要求下鑽的內容

## 3. 使用者角色

MVP 預設只有一個主要人類角色：
- Owner / Founder / Chairman

這個角色關心的是：
- 公司進度
- 任務狀態
- 需要批准的事項
- 風險
- 成本 / token / runtime 狀態

而不是：
- prompt 細節
- 個別 agent personality
- skill 內部 wiring

## 4. 資訊架構

推薦一級導航：

1. `Praetor`
2. `Overview`
3. `Tasks`
4. `Meetings`
5. `Memory`
6. `Models`
7. `Settings`

推薦理由：
- `Praetor`：主入口
- `Overview`：公司總覽
- `Tasks`：執行透明度
- `Meetings`：結構化會議與 review
- `Memory`：公司記憶
- `Models`：model / token / executor / cost
- `Settings`：治理與設定

## 5. 全域布局

推薦使用三欄布局：

```txt
┌──────────────────────────────────────────────────────────────┐
│ Top Bar                                                     │
│ Company | Runtime | Active Model | Alerts | User Menu       │
├──────────────┬───────────────────────────────┬───────────────┤
│ Left Nav     │ Main Workspace                │ Right Rail    │
│ Praetor      │ current page                  │ approvals     │
│ Overview     │                               │ checkpoints   │
│ Tasks        │                               │ running jobs  │
│ Meetings     │                               │ reminders     │
│ Memory       │                               │ decisions     │
│ Models       │                               │               │
│ Settings     │                               │               │
└──────────────┴───────────────────────────────┴───────────────┘
```

### 5.1 Top Bar

應固定顯示：
- company name
- runtime mode
- active primary model
- health status
- pending decisions count
- notifications
- owner menu

這能讓使用者一進來就知道：
- 現在公司用什麼大腦
- 有沒有東西卡住
- 有沒有東西在等我

### 5.2 Right Rail

右側 context panel 讓 UI 有持續運作感。

預設顯示：
- pending approvals
- active checkpoints
- running tasks
- recent decisions
- Praetor reminders

根據頁面不同動態變化。

## 6. Praetor 頁

這是主入口，也是最重要的頁面。

### 6.1 頁面目標

讓使用者像老闆一樣：
- 聽 briefing
- 下方向
- 批准事項
- 請 Praetor 統整內部資訊

### 6.2 頁面結構

#### A. Praetor Summary Card

內容：
- active missions
- tasks in progress
- blocked items
- approvals waiting

範例：

```txt
Praetor Briefing
- 3 active missions
- 2 items waiting for approval
- 1 blocked development task
- 4 tasks progressing normally
```

#### B. Praetor Chat

主對話區。

輸入快捷建議：
- Start a new project
- Review current priorities
- Summarize the company state
- Prepare a meeting
- Show me decisions needed

#### C. Praetor Action Strip

顯示目前最建議的可執行動作：
- Approve project plan
- Review contract summary
- Continue paused mission
- Delay low-priority work

每個 action 可快速選：
- approve
- ask
- defer
- redirect

#### D. Escalation Queue

只放真的需要 owner 的內容：
- strategy change
- spending
- external communication
- destructive write
- mission budget extension

### 6.3 使用者應能做什麼

- 發起新 mission
- 問公司目前狀態
- 請 Praetor 解釋特定任務
- 批准 / 拒絕 / 延後 decision
- 改變任務方向
- 開會

### 6.4 不應該放什麼

- 原始 agent prompt 編輯
- 低層技術 logs 直接鋪滿
- 讓使用者直接管理每個 agent 的 controls

## 7. Overview 頁

### 7.1 目標

讓使用者用 10 秒看懂整間公司現在的狀態。

### 7.2 頁面區塊

#### KPI Row

- Active Projects
- Tasks Running
- Pending Decisions
- Blocked Items
- This Week Outputs
- Memory Updates

#### Company State

三欄摘要：
- On Track
- Needs Attention
- Waiting For Owner

#### Timeline

顯示：
- today
- this week
- upcoming deadlines
- checkpoints

#### Project Snapshot

每個 project 卡片顯示：
- name
- status
- risk level
- next checkpoint
- current owner role

#### Recent Deliverables

展示最近產出：
- docs
- plans
- summaries
- decisions

#### Praetor Note

固定顯示 Praetor 對當前公司狀態的一句話總結。

## 8. Tasks 頁

### 8.1 目標

提供可檢查的執行透明度，但不破壞 Praetor-centered UX。

### 8.2 視圖

#### Board View

欄位：
- Planned
- Assigned
- Running
- Review
- Waiting Approval
- Done

#### List View

可排序與篩選：
- priority
- mission
- role
- due date
- state

### 8.3 Task Detail

點進任務應看到：
- task title
- related mission
- requested by
- role responsible
- current executor / model
- current status
- progress summary
- checkpoints
- outputs
- review notes
- activity log
- cost / token snapshot

### 8.4 底部操作

- Ask Praetor about this task
- Open meeting
- Approve checkpoint
- Pause
- Continue

## 9. Meetings 頁

### 9.1 產品意義

Meeting 不是為了聊天，而是為了讓「AI 公司內部的討論」轉成老闆可理解、可決策的會議成果。

### 9.2 頁面區塊

#### Meeting Templates

- Project Review
- Risk Review
- Weekly Planning
- Budget Review
- Decision Review

#### Active / Recent Meetings

每場會議卡片應顯示：
- title
- participants
- agenda
- summary
- decisions needed
- follow-ups

#### Start Meeting

輸入：
- topic
- participants requested
- whether Praetor moderates

### 9.3 會議輸出格式

固定結構：
- Summary
- Risks
- Decisions Needed
- Approved Actions
- Follow-ups

### 9.4 重要 UX 原則

不要顯示 agent 群聊 transcript 當主要結果。

顯示結構化 meeting summary 才是正確做法。

## 10. Memory 頁

### 10.1 目標

讓使用者理解公司到底記住了什麼，以及 AI 在用什麼記憶做事。

### 10.2 分頁

#### Wiki

顯示：
- Company DNA
- Strategy
- Operating Principles
- Project Rules
- Finance Rules
- Agent Handbook

#### Decisions

顯示：
- summary
- approved by
- impact
- related mission / task

#### Inbox / Source Files

顯示使用者丟進來的原始資料：
- PDFs
- contracts
- notes
- screenshots

#### Retrieval Preview

顯示某次任務 / 回答使用了哪些上下文：
- read wiki pages
- read files
- why selected

### 10.3 為什麼 Retrieval Preview 重要

這直接提高信任：
- AI 不是亂答
- 使用者看得到 Praetor 依據什麼做判斷

## 11. Models 頁

這是非常重要的頁面，不應該埋在 settings 裡。

### 11.1 目標

讓使用者清楚知道：
- 現在在用哪些模型 / executors
- token 用量
- 成本
- 哪些任務用了昂貴路徑
- 系統是否健康

### 11.2 頁面區塊

#### Current Runtime Configuration

- current mode
- primary model
- backup model
- available executors
- provider status

#### Usage Overview

- tokens used today
- tokens used this week
- estimated cost
- average cost per mission
- calls by provider

#### Per-model Breakdown

表格欄位建議：
- Model
- Used For
- Calls
- Input Tokens
- Output Tokens
- Estimated Cost

#### Executor Activity

- Codex CLI runs
- Claude Code runs
- OpenClaw runs
- success / failure
- average duration

#### Budget & Policy

- daily budget
- per-mission budget
- fallback rules
- expensive model restrictions

### 11.3 高價值設計

這頁不能只是數字堆疊。

要讓使用者可以看懂：
- 哪種工作最花 token
- 哪些任務該切到 cheaper route
- 哪些 executor 最常卡住

## 12. Settings 頁

Settings 不應是一頁大雜燴。

### 12.1 General

- company name
- language
- timezone
- owner profile

### 12.2 Governance

- autonomy mode
- required approvals
- never allow
- checkpoint policy
- pm creation policy

### 12.3 Workspace

- root path
- allowed read paths
- allowed write paths
- archive rules
- backup rules

### 12.4 Roles

重點是 role，不是 agent。

應可編輯：
- role name
- responsibilities
- outputs
- constraints
- style

### 12.5 AI / Executors

- provider selection
- API keys
- executor selection
- Codex / Claude / OpenClaw connectivity
- fallback behavior

### 12.6 Security

- local-only / remote mode
- login settings
- password rotation
- session management

### 12.7 Advanced

- debug logs
- shell policy
- import / export config
- experimental features

## 13. Onboarding UX

### 13.1 原則

Onboarding 不能只是表單。

它應該像 Praetor 帶你建立公司的第一場會議。

### 13.2 建議流程

1. owner account bootstrap
2. welcome
3. language
4. leadership style
5. decision style
6. organization style
7. autonomy
8. risk preference
9. runtime mode
10. executor connection（conditional）
11. workspace
12. approvals
13. first mission

補充原則：
- 即使 `Local-only` 也應有 owner account
- trusted local device 可以降低之後登入摩擦，但不應完全無帳號
- 若使用 `subscription_executor`，onboarding 必須檢查 host bridge 與 CLI login 狀態

### 13.3 Onboarding 的最終產物

不是只有設定完成而已，而是要落地產生：
- Company DNA
- workspace 結構
- 初始 roles
- 第一個 mission

### 13.4 Onboarding 結尾

Praetor 應該以一個明確的第一個行動結束：

`What would you like your company to do first?`

## 14. Checkpoint 與 Paused State UX

這是 Praetor 很重要的頁面行為。

### 14.1 必須出現的資訊

當 mission 暫停時，應顯示：
- pause reason
- completed items
- next possible steps
- cost / token used so far
- required decision

### 14.2 必須出現的按鈕

- Continue
- Continue with larger budget
- Stop
- Ask Praetor
- Change policy for this mission

### 14.3 文案方向

不要顯示像錯誤一樣。

應該讓使用者感覺：
- 系統有節奏
- 暫停是設計的一部分
- 不是故障

## 15. Activity / Agent View

### 15.1 這頁的定位

這是透明度頁，不是主操作頁。

### 15.2 顯示內容

- current active roles
- current active tasks
- currently running executor
- latest outputs
- review status

### 15.3 Direct chat 的取捨

建議：
- 預設不提供 direct raw chat with agent
- 若提供，也應走 `Talk to X via Praetor`

優點：
- 保住治理層
- 不破壞 executive UX

缺點：
- power users 會覺得少了一點直接操控感

判斷：
- 預設正確，debug / expert mode 可逐步放開

## 16. 通知與提醒

通知應分成三類：

### 16.1 Informational

例如：
- mission completed
- wiki updated
- inbox processed

### 16.2 Actionable

例如：
- approval needed
- paused due to budget
- reviewer blocked result

### 16.3 Critical

例如：
- executor unhealthy
- workspace path unavailable
- mission failed after retries

UI 上應該用不同顏色與優先級呈現。

## 17. Empty / Loading / Error / Degraded States

這些狀態會直接影響完成度。

### 17.1 Empty State

例如第一次使用：
- no missions yet
- no projects yet
- no wiki yet

應該搭配清楚的 next actions。

### 17.2 Loading State

不要只是一個 spinner。

應顯示：
- Praetor 正在做什麼
- 目前進度大概在哪

### 17.3 Error State

應說清楚：
- 問題在哪
- 建議怎麼處理
- 可以不要打斷其他 mission

### 17.4 Degraded State

例如：
- primary model unavailable
- fallback model active
- executor login expired

應在 top bar 與 Models 頁都明確呈現。

## 18. Responsive 設計

### 18.1 Desktop

完整三欄布局。

### 18.2 Tablet

右欄可折疊成 drawer。

### 18.3 Mobile

不應把全部頁面硬塞。

MVP mobile 重點應支援：
- 查看 briefing
- 批准 / 拒絕
- 看關鍵狀態
- 發簡短指令給 Praetor

重度管理與設定仍以 desktop 為主。

## 19. 視覺與語氣

### 19.1 Praetor 的語氣

建議：
- 冷靜
- 果斷
- 結構化
- 不討好
- 不拖泥帶水

### 19.2 視覺風格方向

應偏向：
- 權威感
- 清晰層級
- 高可掃描性
- 少量但有意義的強提示色

不應偏向：
- 可愛 agent 遊戲感
- 太像聊天工具
- 太像複雜 enterprise ERP

## 20. 核心 UI 取捨

### 20.1 為什麼不讓使用者直接管理 agent

優點：
- 保持 executive UX
- 降低認知負擔
- 更符合產品哲學

缺點：
- 會讓部分 power users 想要更深控制

判斷：
- 預設不暴露，之後再加 expert mode

### 20.2 為什麼 Models 要獨立成頁

優點：
- 成本與健康度是核心訊息
- 更容易建立信任

缺點：
- 導覽多一頁

判斷：
- 值得獨立，因為這不是小設定，而是產品運營透明度

### 20.3 為什麼 Meetings 值得獨立

優點：
- 明確凸顯 Praetor 的公司組織差異化
- 不讓所有 review 都塞進 chat

缺點：
- MVP 工作量增加

判斷：
- 若資源不足，可先藏在 Praetor page 的一種模式

## 21. MVP 頁面優先級

### P1

- Praetor
- Overview
- Tasks
- Settings

### P2

- Memory
- Models
- Meetings

### P3

- Activity / expert mode
- richer audit views
- deeper runtime diagnostics

## 22. 最後的 UI 結論

Praetor 的 UI 核心不應該是：

`讓你操作很多 agent`

而應該是：

**讓你像董事長一樣，透過一個 AI CEO 看整間公司的狀態、介入關鍵決策、並確認工作持續推進。**
