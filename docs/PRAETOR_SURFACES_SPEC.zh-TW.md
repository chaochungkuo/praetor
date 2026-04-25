# Praetor Web / Mobile / Telegram 跨端規格 v0.1

狀態：設計稿

這份文件專門定義 Praetor 的三個使用介面：

- Web
- Mobile Web
- Telegram

重點不是做三套平行產品，而是定義：
- 每一端的角色
- 功能邊界
- 權限邊界
- 可暴露資訊範圍
- interaction flow
- 何時應跳轉到另一端

## 1. 核心原則

Praetor 的三端不應該是三個獨立產品。

它們應該是同一個公司控制系統的三種入口：

- `Web`：董事長辦公室
- `Mobile Web`：董事長隨身控制台
- `Telegram`：董事長與 Praetor 的快速專線

三端的共同原則：

1. 使用者只主要對話 `Praetor`
2. 不預設直接對底層 agent 操作
3. 高風險行為不能在低上下文介面內直接完成
4. 資訊先摘要，再允許下鑽
5. 三端共享同一個 mission / decision / memory 真相來源

## 2. 三端定位總結

| Surface | 角色定位 | 適合做什麼 | 不適合做什麼 |
|---|---|---|---|
| Web | 完整控制台 | 深度管理、文件檢視、會議、設定、深入任務 | 極短頻快速通知 |
| Mobile Web | 輕量 executive dashboard | 查看狀態、快速批准、簡短互動 | 複雜設定、重度文件作業 |
| Telegram | 快速通知與指令通道 | 接通知、簡報、快速 approve、簡短提問 | 高風險操作、全量資料檢視、複雜管理 |

## 3. 全域跨端規則

### 3.1 Canonical surface

唯一完整 control plane 是 `Web`。

這代表：
- 所有完整資料都能在 Web 找到
- 所有高風險動作都應可回到 Web 完成
- Mobile / Telegram 可以觸發，但不應取代 Web

### 3.2 Praetor-centered routing

三端預設互動都應是：

`User -> Praetor`

而不是：

`User -> Dev Agent`
`User -> Finance Agent`
`User -> Reviewer`

若未來要支援 direct specialist interaction，也必須是：

`Talk to X via Praetor`

### 3.3 Risk-based surface gating

建議根據風險決定在哪一端允許操作：

#### Low risk

可在 Web / Mobile / Telegram 完成：
- 查看 briefing
- 查看狀態
- 低風險 approve
- 要求 summary
- 啟動 meeting summary

#### Medium risk

Web / Mobile 可完成，Telegram 只通知或只做簡化版：
- continue mission
- pause mission
- approve mission batch continuation
- approve non-destructive internal document generation

#### High risk

只能在 Web 完成：
- destructive file overwrite
- shell execution approval
- strategy change
- budget / spending
- external communication
- 改公司治理與全域設定

### 3.4 Identity consistency

三端都應使用同一個 executive identity：

- Praetor Briefing
- Ask Praetor
- Praetor Decision
- Praetor Alert

不要在不同端突然變成：
- CEO
- Bot
- Assistant
- Agent Manager

## 4. Web 正式功能邊界

### 4.1 定位

Web 是：

**Praetor Office**

也就是董事長辦公室與完整控制台。

### 4.2 Web 必須承擔的功能

#### A. 完整公司總覽

- active missions
- project status
- upcoming deadlines
- pending approvals
- blocked items
- recent outputs

#### B. 完整 Praetor 對話

- 深度對話
- multi-turn context
- strategy discussion
- role definition refinement
- meeting creation

#### C. 任務透明度

- board view
- list view
- task detail
- execution log
- review notes
- checkpoint state

#### D. 公司記憶管理

- Wiki
- Decisions
- Inbox
- Retrieval Preview

#### E. 模型與成本透明度

- model breakdown
- token usage
- executor status
- daily / mission cost

#### F. 全域治理與設定

- autonomy mode
- approvals
- workspace permissions
- executor config
- security settings

### 4.3 Web 禁止簡化過度的地方

Web 不應只剩：
- 一個 chat box

因為那樣會破壞 Praetor 的產品差異化。

Web 必須讓使用者感覺：
- 公司真的在運作
- 任務真的被追蹤
- 決策真的被治理

### 4.4 Web 不應預設暴露的東西

- 底層 agent prompt
- raw prompt engineering controls
- 每個 agent 的人格面板
- skill wiring 細節

## 5. Mobile Web 正式功能邊界

### 5.1 定位

Mobile Web 是：

**Praetor Mobile Briefing**

它不是桌面版縮小，而是「隨身 executive dashboard」。

### 5.2 Mobile 應該承擔的核心功能

#### A. 今日簡報

- today's briefing
- active missions
- urgent alerts
- pending approvals

#### B. 快速決策

- approve
- reject
- ask for summary
- continue paused mission
- pause mission

#### C. 簡短對話

- ask current status
- ask what needs my decision
- ask summarize this mission

#### D. Meeting Summary 閱讀

- 看會議摘要
- 看 risks
- 看 decisions needed

#### E. 通知後快速處理

- 點開 mobile web deep link
- 快速完成決策

### 5.3 Mobile 不應承擔的功能

- 大量文件編輯
- 全量 mission debugging
- 深度 log 審查
- 大型 settings 編輯
- 大量 memory browsing

### 5.4 Mobile 的互動原則

- 先給 Praetor summary
- 再給 1 到 3 個明確 action
- 不應逼使用者手機上讀長篇大論

## 6. Telegram 正式功能邊界

### 6.1 定位

Telegram 是：

**Praetor Direct Line**

它是通知、回應、簡短命令的窄入口，不是完整產品面。

### 6.2 Telegram 應該做什麼

#### A. 主動通知

例如：
- `1 decision requires approval`
- `Mission paused due to budget limit`
- `Project Alpha is ready for review`

#### B. 快速查詢

例如：
- `briefing`
- `status`
- `what needs my decision`
- `show project alpha`
- `what is blocked`

#### C. 快速回覆

例如：
- approve
- reject
- continue
- pause
- summarize

#### D. 引導回 Web

高風險事項應用：
- concise summary
- button / deep link to web

### 6.3 Telegram 不應該做什麼

- 直接改全域設定
- 看大量敏感文件全文
- 高風險批准
- 刪檔或覆蓋重要文件
- shell / executor 高風險操作
- 大範圍 memory 管理

### 6.4 Telegram 的產品價值

Telegram 不是要替代 Web。

它的價值是：
- 讓 Praetor 能主動找到你
- 讓你不必打開完整系統就能處理小決策

## 7. 跨端導流規則

### 7.1 Telegram -> Mobile / Web

應跳轉的情況：
- 內容太長
- 需要看附件
- 需要看 diff
- 需要看 mission 全貌
- 高風險批准

### 7.2 Mobile -> Web

應跳轉的情況：
- 要改 settings
- 要深入 memory
- 要看大量文檔
- 要做複雜會議與多方 review

### 7.3 Web -> Telegram

可主動設定：
- whether to notify on approvals
- whether to notify on mission completion
- whether to notify on blocked state

## 8. Web 文字版 Wireframe

## 8.1 Web 首頁 / Praetor Page

```txt
┌──────────────────────────────────────────────────────────────┐
│ Praetor Office                                               │
│ Company: Praetor Studio | Mode: Subscription Executor        │
│ Active Model: Codex CLI | Pending Decisions: 2               │
├──────────────────────────────────────────────────────────────┤
│ Praetor Briefing                                             │
│ - 3 active missions                                          │
│ - 1 blocked item                                             │
│ - 2 approvals waiting                                        │
│ - 4 tasks progressing normally                               │
├───────────────────────────────┬──────────────────────────────┤
│ Praetor Chat                  │ Decision Queue               │
│                               │ - Approve budget refinement  │
│ You ↔ Praetor                 │ - Approve file overwrite     │
│                               │                              │
│ [Start project] [Briefing]    │ [Approve] [Review] [Defer]   │
│ [Meeting] [Status]            │                              │
├───────────────────────────────┴──────────────────────────────┤
│ Suggested Actions                                             │
│ - Continue paused mission                                     │
│ - Review Project Alpha                                        │
│ - Delay low-priority work                                     │
└──────────────────────────────────────────────────────────────┘
```

## 8.2 Web Overview Page

```txt
┌──────────────────────────────────────────────────────────────┐
│ Overview                                                     │
├──────────────────────────────────────────────────────────────┤
│ KPIs                                                         │
│ 6 Active Projects | 8 Running Tasks | 2 Pending Decisions    │
│ 1 Blocked Item | 14 Outputs This Week | 3 Memory Updates     │
├──────────────────────────────────────────────────────────────┤
│ On Track            Needs Attention      Waiting For Owner   │
│ - Project A         - Budget missing     - Strategy review   │
│ - Project C         - One blocked task   - Approval X        │
├──────────────────────────────────────────────────────────────┤
│ Timeline                                                     │
│ Today | This Week | Upcoming Checkpoints                     │
├──────────────────────────────────────────────────────────────┤
│ Project Snapshot                                             │
│ [Alpha] [Beta] [Gamma]                                       │
├──────────────────────────────────────────────────────────────┤
│ Recent Deliverables                                          │
│ - Budget draft                                               │
│ - Contract summary                                           │
│ - Wiki update                                                │
└──────────────────────────────────────────────────────────────┘
```

## 8.3 Web Task Detail Page

```txt
┌──────────────────────────────────────────────────────────────┐
│ Mission: Build Website                                       │
│ Owner: Praetor | Manager: PM(auto) | Status: Review          │
├──────────────────────────────────────────────────────────────┤
│ Progress                                                     │
│ - Structure completed                                        │
│ - Draft homepage generated                                   │
│ - QA pending                                                 │
├──────────────────────────────────────────────────────────────┤
│ Checkpoints                                                  │
│ - before_completion : pending                                │
├──────────────────────────────────────────────────────────────┤
│ Outputs                                                      │
│ - /Projects/Website/PROJECT.md                               │
│ - /Projects/Website/TASKS.md                                 │
├──────────────────────────────────────────────────────────────┤
│ Activity Log                                                 │
│ - Dev role executed via codex_cli                            │
│ - Reviewer flagged missing budget                            │
├──────────────────────────────────────────────────────────────┤
│ [Ask Praetor] [Open Meeting] [Approve] [Pause]               │
└──────────────────────────────────────────────────────────────┘
```

## 9. Mobile 文字版 Wireframe

## 9.1 Mobile Home

```txt
┌──────────────────────────────┐
│ Praetor Mobile               │
├──────────────────────────────┤
│ Today's Briefing             │
│ - 2 approvals waiting        │
│ - 1 mission paused           │
│ - 3 running normally         │
├──────────────────────────────┤
│ Need Your Decision           │
│ [Approve budget]             │
│ [Review paused mission]      │
├──────────────────────────────┤
│ Active Missions              │
│ - Project Alpha              │
│ - Website Build              │
├──────────────────────────────┤
│ Quick Ask                    │
│ [What is blocked?]           │
│ [Summarize today]            │
│ [Ask Praetor...]             │
└──────────────────────────────┘
```

## 9.2 Mobile Approval Detail

```txt
┌──────────────────────────────┐
│ Approval Needed              │
├──────────────────────────────┤
│ Mission: Build Website       │
│ Reason: Budget planning      │
│ Impact: Medium               │
├──────────────────────────────┤
│ Completed                    │
│ - Structure done             │
│ - Draft plan written         │
├──────────────────────────────┤
│ Next                         │
│ - refine timeline            │
│ - update wiki                │
├──────────────────────────────┤
│ [Approve] [Reject] [Ask]     │
│ [Open in Web]                │
└──────────────────────────────┘
```

## 10. Telegram 文字版 Wireframe

## 10.1 主動通知

```txt
Praetor:
You have 1 decision waiting.

Mission: Build Website
Reason: Budget refinement required
Impact: Medium

[Approve]
[Ask for summary]
[Open in Web]
```

## 10.2 快速 briefing

```txt
User:
/briefing

Praetor:
Today's company status:
- 3 active missions
- 1 blocked task
- 2 approvals waiting

Most urgent:
Budget approval for Build Website

[Show decisions]
[Show blocked]
[Open dashboard]
```

## 10.3 Mission paused

```txt
Praetor:
Mission paused: Build Invoice Tool

Reason:
Token budget reached

Completed:
- project structure created
- first draft written

Next:
- refine parser
- run review

[Continue]
[Increase budget]
[Ask for summary]
[Open in Web]
```

## 11. Web Interaction Flow

## 11.1 Flow: Start New Mission

1. 使用者進入 `Praetor` 頁
2. 點 `Start a new project`
3. 輸入目標
4. Praetor 回：
   - 理解的任務
   - 建議的第一輪工作
   - 哪些會自動做
   - 哪些會停下來問
5. 使用者確認
6. 系統建立 mission
7. 跳到 mission detail 或保持在 Praetor 頁顯示 briefing

## 11.2 Flow: Review Blocked Mission

1. 使用者在 Overview 看到 blocked item
2. 點進 Task detail
3. 看：
   - blocked reason
   - current outputs
   - review notes
4. 點 `Ask Praetor`
5. Praetor 提供：
   - blocked cause
   - options
   - recommendation
6. 使用者決定：
   - continue
   - redirect
   - stop

## 11.3 Flow: Strategic Meeting

1. 使用者在 Praetor chat 輸入：`Let's review Project Alpha`
2. Praetor 建議會議議程
3. 使用者確認
4. 系統建立 meeting
5. 產出 structured summary
6. 顯示：
   - summary
   - risks
   - decisions needed
   - follow-ups

## 12. Mobile Interaction Flow

## 12.1 Flow: Quick Approval

1. 使用者手機打開 mobile web
2. 首頁看到 `Need Your Decision`
3. 點進 approval card
4. 看簡短摘要
5. 點：
   - approve
   - reject
   - ask
6. 系統更新 approval state
7. 回到 mobile home 顯示新 briefing

## 12.2 Flow: Ask Current Status

1. 使用者打開 mobile
2. 點 `What is blocked?`
3. Praetor 回短摘要
4. 若需要 deeper detail，提供 `Open in Web`

## 13. Telegram Interaction Flow

## 13.1 Flow: Approval via Telegram

1. Praetor 發送通知
2. 使用者點 `Approve`
3. 系統檢查：
   - approval category
   - current risk policy
4. 若屬 low / medium risk 且允許 Telegram：
   - 直接批准
5. 若屬 high risk：
   - 回覆摘要
   - 附 `Open in Web`

## 13.2 Flow: Quick Status Request

1. 使用者輸入 `/status`
2. Praetor 回：
   - active missions
   - blocked items
   - pending decisions
3. 若使用者輸入 `show project alpha`
4. 回傳精簡 summary
5. 如需全文或附件，給 deep link

## 14. 通知策略

### 14.1 Web

適合：
- in-app banners
- decision center
- activity panel

### 14.2 Mobile

適合：
- mobile notification
- deep link into approval or mission card

### 14.3 Telegram

適合：
- high-value push notifications
- quick response loops

### 14.4 不應該通知過量

預設應只推送：
- approvals
- blocked missions
- mission completion
- critical runtime health issues

不應推送：
- every internal task update
- every file write
- every reviewer note

## 15. 安全與隱私邊界

### 15.1 Web

可承載最高風險操作。

但仍需：
- login
- session controls
- audit trail

### 15.2 Mobile

可做中風險以內互動，但高風險最好仍要求 Web confirm。

### 15.3 Telegram

Telegram 應視為低上下文介面。

原則：
- 可查狀態
- 可看摘要
- 可做低中風險 approve
- 高風險 deep link 回 Web

絕不應預設在 Telegram 允許：
- destructive file overwrite
- shell execution approval
- company DNA 修改
- security settings 修改

## 16. 穩定性與產品取捨

### 16.1 為什麼不讓三端功能一樣

優點：
- 產品清楚
- 安全更好控
- 使用者不會困惑
- engineering 更可維護

缺點：
- 有些 power users 會想在 Telegram 做更多事

判斷：
- 功能不對稱是正確的，不是缺點

### 16.2 為什麼 Web 要是 canonical surface

優點：
- 完整上下文
- 最適合高風險決策
- 文件與 mission 可視化最好

缺點：
- 需要使用者回到桌面處理部分事情

判斷：
- 值得，因為 Praetor 本質上是公司控制台，不是純訊息 bot

## 17. MVP 建議範圍

### P1

- Web 完整 Praetor / Overview / Tasks / Settings
- Mobile Web briefing + approvals + ask Praetor
- Telegram notifications + status + low-risk approvals

### P2

- Mobile deeper mission cards
- Telegram deep link flows
- Meetings on Web

### P3

- expert mode specialist view
- richer cross-device continuity

## 18. 最後結論

Praetor 的三端應該是：

- `Web`：完整的董事長辦公室
- `Mobile Web`：隨身 executive dashboard
- `Telegram`：Praetor 的直接專線

這三端不應該互相競爭，而應該共同維持同一件事情：

**讓使用者始終透過 Praetor 管理整間 AI 公司，而不是被一堆 agent 與低層流程反過來管理。**
