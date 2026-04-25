# Praetor 系統規格 v0.1

狀態：設計稿

這份文件定義 Praetor 的核心系統模型、資料結構、治理規則、記憶架構、執行節奏、安全邊界與穩定性策略。

## 1. 設計目標

Praetor 的系統層要同時滿足 6 件事：

1. 使用者只需要面對一個 executive interface
2. 系統可以在內部做分層、拆任務、分配 skill
3. 記憶和成果必須可追溯、可審核、可重現
4. AI 可以主動前進，但不能越權
5. context 不可無限膨脹
6. 執行必須能暫停、恢復、歸檔

## 2. 核心系統原則

### 2.1 Role-first

對使用者暴露的最小抽象是 `Role`。

使用者定義：
- 職位
- 職責
- 產出
- 限制

系統決定：
- agent form
- internal prompt style
- skill assignment
- 是否建立 manager 層

### 2.2 Company-memory-first

記憶歸公司，不歸 agent。

MVP 只保留：
- Company Memory
- Mission / Task Memory

MVP 不做：
- agent personal memory
- agent emotional state
- agent relationship state

### 2.3 Governance-first

任何 AI 行為都應落在可治理範圍內。

治理必須顯式決定：
- 哪些動作自動做
- 哪些動作批次報告
- 哪些動作必須先批准
- 哪些動作永遠不能做

### 2.4 Hidden hierarchy

使用者看到的是 Praetor。

內部實際可以是：
- Praetor / CEO
- mission-scoped PM
- worker
- reviewer

但預設不把內部複雜度直接暴露給使用者。

## 3. 核心實體

### 3.1 Company DNA

Company DNA 是整個公司運作的頂層配置。

```yaml
company_dna:
  language: zh-TW
  leadership_style: strategic
  decision_style: balanced
  organization_style: lean
  autonomy_mode: hybrid
  risk_priority: avoid_wrong_decisions
  communication_style: concise
  operating_principles:
    - default_to_action_escalate_when_uncertain
    - keep_roles_minimal_but_clear
    - avoid_unnecessary_user_interruption
    - document_important_decisions
```

作用：
- 決定 Praetor 的語氣
- 決定 role 結構偏 lean / balanced / structured
- 決定 reviewer 嚴格度
- 決定 checkpoint 密度
- 決定預設批准邊界

### 3.2 Role

```yaml
role:
  id: role_project_execution
  name: Project Execution
  responsibility:
    - create_project_structure
    - maintain_project_status
    - organize_related_documents
  outputs:
    - project_folder
    - project_plan
    - status_update
  constraints:
    - no_strategy_change
    - no_budget_commitment
  style:
    tone: concise
    strictness: medium
    detail_level: medium
```

作用：
- 使用者定義工作意圖
- 系統據此生成 agent 和 skill mapping

### 3.3 Internal Agent Instance

`Agent` 是內部執行形態，不是主要使用者抽象。

```yaml
agent_instance:
  id: agent_project_execution_01
  role_id: role_project_execution
  type: worker
  mission_scope: mission_website_launch
  status: active
  derived_from:
    - company_dna
    - role_definition
    - runtime_policies
```

注意：
- agent 可以被重新生成
- agent 不應承擔持久人格記憶

### 3.4 Mission

Mission 是 Praetor 的主要工作單位。

```yaml
mission:
  id: mission_build_invoice_tool
  title: Build Invoice Tool
  requested_by: owner
  owner_layer: ceo
  manager_layer: pm_auto
  status: running
  priority: high
  domains:
    - development
    - finance
  run_budget:
    max_steps: 20
    max_tokens: 100000
    max_time_minutes: 30
    max_cost_eur: 2.00
```

Mission 應有清楚 lifecycle，並對應實體資料夾。

### 3.5 Task

Task 是 mission 內部的可執行單元。

```yaml
task:
  id: task_generate_project_structure
  mission_id: mission_build_invoice_tool
  title: Generate project structure
  role_owner: role_project_execution
  current_executor: codex_cli
  status: review
  checkpoint_policy:
    - before_completion
  outputs:
    - /workspace/Projects/InvoiceTool/PROJECT.md
```

### 3.6 Decision

```yaml
decision:
  id: decision_budget_strategy_001
  mission_id: mission_build_invoice_tool
  summary: choose_mvp_scope
  requested_by: ceo
  impact: strategic
  status: waiting_owner
  options:
    - lean_scope
    - expanded_scope
```

### 3.7 Approval Request

Approval 是 UI 與治理之間的重要交界。

```yaml
approval_request:
  id: approval_overwrite_file_002
  category: overwrite_important_file
  mission_id: mission_build_invoice_tool
  raised_by: pm
  reason: update_existing_status_document
  status: pending
  actions:
    - approve_once
    - approve_for_mission
    - reject
```

### 3.8 Meeting

Meeting 是結構化討論單位，不是自由聊天室。

```yaml
meeting:
  id: meeting_project_review_001
  mission_id: mission_build_invoice_tool
  type: project_review
  moderator: ceo
  participants:
    - pm
    - worker
    - reviewer
  agenda:
    - current_status
    - risks
    - next_steps
  outputs:
    - summary
    - risks
    - decisions_needed
    - follow_ups
```

## 4. 狀態機

### 4.1 Mission 狀態

```txt
planned
→ active
→ review
→ waiting_approval
→ resumed
→ completed
→ archived
```

可中途進入：
- `paused_budget`
- `paused_decision`
- `paused_risk`
- `failed`

### 4.2 Task 狀態

```txt
planned
→ assigned
→ running
→ review
→ waiting_approval
→ done
```

可中途進入：
- `blocked`
- `paused`
- `failed`

### 4.3 Approval 狀態

```txt
pending
→ approved_once
→ approved_for_scope
→ rejected
→ expired
```

## 5. 組織與分層規則

### 5.1 Praetor / CEO 層責任

Praetor 必須負責：
- 理解 owner 意圖
- 把需求翻譯成 roles / missions
- 決定是否建立 PM
- 決定是否升級給 owner
- 維持全域治理
- 做跨 mission 決策

Praetor 不應該負責：
- 長期硬扛所有 mission 細節
- 自己保留龐大局部上下文

### 5.2 PM 層責任

PM 是 mission-scoped context owner。

PM 應負責：
- 維持 mission context
- 拆 task
- 協調 worker / reviewer
- 做低風險局部決策
- 定期向 Praetor 上報

PM 不應負責：
- 修改公司 DNA
- 全域設定
- 對外高風險操作
- 超出 mission scope 的資源承諾

### 5.3 Worker 層責任

Worker 應負責：
- 完成具體 task
- 產出文件、修改檔案、執行 executor
- 回報結果

Worker 不應負責：
- 全域策略
- 最終決策
- 跨 mission 指揮

### 5.4 Reviewer 層責任

Reviewer 應負責：
- 檢查輸出
- 找出缺漏
- 阻擋明顯不合格結果

Reviewer 不應負責：
- 改寫公司方向
- 直接代替 owner 做批准

## 6. CEO Load Management

Praetor 需要內建 overload 檢測，而不是憑感覺。

### 6.1 指標

建議至少納入：
- `context_tokens`
- `estimated_steps`
- `domain_count`
- `active_mission_count`
- `blocked_count`
- `decision_queue_size`

### 6.2 基本規則

```yaml
ceo_load_policy:
  context_warning_at_tokens: 70000
  context_split_at_tokens: 90000
  max_steps_without_pm: 5
  max_domains_without_pm: 1
  max_active_missions_per_ceo: 3
  create_pm_after_blocked_count: 2
```

### 6.3 建議演算法

簡化版：

```python
def should_create_pm(mission):
    return (
        mission.context_tokens > 90000
        or mission.estimated_steps > 5
        or mission.domain_count > 1
        or mission.blocked_count >= 2
    )
```

進階版：

```python
load_score = (
    context_ratio * 0.4
    + active_task_ratio * 0.2
    + domain_ratio * 0.2
    + blocked_ratio * 0.2
)

if load_score > 0.7:
    create_pm()
```

### 6.4 PM 建立原則

建立 PM 的理由應該是：
- context 需要 owner
- 任務需要隔離
- 任務需要節奏管理

不是：
- 為了塑造戲劇化人格

## 7. 記憶架構

### 7.1 Company Memory

長期、共享、可版本化：
- `Wiki/`
- `Decisions/`
- `Projects/`
- `Operating Principles`
- `Company DNA`

### 7.2 Mission Memory

短中期、可歸檔：
- `MISSION.md`
- `STATUS.md`
- `TASKS.md`
- `DECISIONS.md`
- `CONTEXT.md`
- `REPORT.md`
- `logs/`

### 7.3 Runtime Ephemeral Context

這一層不應長期保存成 agent 人格，而應只存在於當前運行批次：
- current prompt context
- current retrieval set
- current step outputs
- temporary tool results

### 7.4 Retrieval 規則

Praetor 和 PM 不應該每次都讀完整 workspace。

建議 retrieval pipeline：

1. 先讀 Company DNA
2. 再讀 mission summary
3. 再根據 task 類型選 relevant wiki/pages/files
4. 顯示 retrieval preview 供使用者查看

這樣做的好處：
- 降低 token 消耗
- 增加可解釋性
- 降低 hallucinated context

## 8. 執行節奏與 Run Budget

### 8.1 Run Budget

每個 mission 都應有 budget：

```yaml
run_budget:
  max_steps: 20
  max_tokens: 100000
  max_time_minutes: 30
  max_cost_eur: 2.00
```

### 8.2 Pause 條件

必須支援三大暫停點：

1. token / cost budget reached
2. decision checkpoint
3. risk checkpoint

加上任務完成時的正常停止。

### 8.3 Autonomy Policy

建議：

```yaml
autonomy_policy:
  low_risk_tasks: auto_continue
  medium_risk_tasks: report_after_batch
  high_risk_tasks: require_approval
```

### 8.4 節奏哲學

Praetor 不追求「永遠不停」。

它追求的是：

**在安全範圍內主動前進，然後在正確時刻停下來請人決策。**

## 9. Executor Abstraction

Praetor 必須把執行器抽象乾淨。

### 9.1 Executor 類型

```yaml
executor:
  type: codex_cli | claude_code | openai_api | ollama
  transport: builtin | host_bridge
  workspace_scope: /app/workspace
  approval_mode: delegated
  supports_file_write: true
  supports_shell: conditional
  supports_streaming: optional
```

### 9.2 必要 contract

每個 executor adapter 至少要實作：
- `prepare_task_spec()`
- `check_preconditions()`
- `run()`
- `collect_outputs()`
- `collect_logs()`
- `normalize_result()`
- `classify_failure()`

### 9.3 Non-interactive batch contract

Praetor 的 executor contract 不能只是「能跑起來」。

它還必須保證：

- 預設以非互動 batch 模式執行
- 不把底層 CLI 的互動提示直接暴露給 owner
- 任何需要人類介入的狀態都要被標準化

因此每個 executor adapter 還應定義：
- `supports_noninteractive_batch`
- `supports_cancel`
- `supports_stream_events`
- `normalize_pause_reason()`
- `normalize_usage()`

標準化結果至少要分成：
- `completed`
- `paused_budget`
- `paused_decision`
- `paused_risk`
- `auth_required`
- `interactive_approval_required`
- `cancelled`
- `failed_transient`
- `failed_permanent`

Praetor 的原則是：

- executor 可以內部使用自己的 approval / auth 機制
- 但 Praetor 不應讓它直接打斷整個使用者體驗
- 所有互動需求都要先被 bridge / adapter 正規化，再交回 Praetor 的 checkpoint 與 approval 系統

### 9.4 特別注意 Subscription Executor Mode

這個模式要明確區分：
- 使用者的 ChatGPT / Claude 訂閱
- 平台 API billing

Praetor 不應嘗試「直接使用 ChatGPT 訂閱當 API」。

Praetor 應支援的是：
- 已登入 CLI
- 已登入 app / tool
- 可被安全呼叫的 executor surface

另外要明確限制：
- `subscription_executor` 不是 `Remote public` 的 v1 正式路線
- 正式支援範圍應以 `Local-only` 與 owner-controlled `Remote private` 為主

## 10. 權限與安全模型

### 10.1 Workspace 邊界

所有執行都應落在受控 workspace 內。

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
    - /app/workspace/Finance/Locked
```

### 10.2 危險動作分類

高風險：
- delete files
- overwrite important files
- shell command
- external communication
- spend money
- strategy change

永不允許：
- access outside allowed scope
- silent destructive actions
- external send without explicit rule

### 10.3 權限提升

重要規則：

**Praetor 可以自動建立 PM，但不能自動提升風險權限。**

也就是說：
- 組織可以動態擴編
- 權限邊界不能默默變大

## 11. 穩定性策略

### 11.1 Idempotency

重跑 mission 時，應盡量保證：
- 已存在輸出可辨識
- 不重複建立一樣的 artifacts
- 相同步驟可安全 retry

### 11.2 Canonical State

Praetor 必須明確定義 mission state 的真相來源。

建議：

- `mission folder` = canonical source of truth
- `SQLite` = index / cache / UI acceleration

這代表：
- mission resume 以 mission folder 為主
- SQLite 損毀時，理論上應可重建索引
- 若 mission folder 與 SQLite 不一致，以 mission folder 為準

### 11.3 Resumability

Mission 暫停後，應能靠 mission folder 恢復。

至少要保留：
- current status
- last completed step
- pending checkpoints
- current outputs
- executor logs

SQLite 可協助快速查詢，但不應成為唯一真相來源。

### 11.4 Auditability

任何重要動作都要可回溯：
- 誰發起
- 誰決定
- 讀了哪些記憶
- 寫了哪些檔案
- 用了哪個 model / executor
- 花了多少 tokens / cost

### 11.5 Failure Isolation

單一 mission / executor 失敗不應拖垮整個系統。

應至少保證：
- API 層還能回應
- UI 還能顯示失敗原因
- 其他 mission 可繼續
- mission 可重試或轉為人工介入

### 11.6 Backups

最少應有：
- workspace snapshot policy
- SQLite backup policy
- decision log durability

## 12. Mission 檔案建議

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

用途：

- `MISSION.md`
  - 任務目標、邊界、run budget、requested outputs

- `STATUS.md`
  - 當前狀態、完成比例、下一步

- `TASKS.md`
  - task breakdown

- `DECISIONS.md`
  - mission 級決策與批准紀錄

- `CONTEXT.md`
  - 任務所需局部上下文

- `REPORT.md`
  - 給 Praetor / owner 的摘要

- `logs/`
  - executor logs、runtime traces、review logs

## 13. 推薦預設政策

```yaml
organization_policy:
  hidden_pm_enabled: true
  ask_owner_first_time_for_pm_creation: true
  auto_create_pm_after_trust: true
  pm_scope: mission
  pm_lifetime: until_completed

memory_policy:
  agent_personal_memory: disabled
  company_memory: enabled
  mission_memory: enabled

runtime_policy:
  default_speed_mode: balanced
  default_autonomy_mode: hybrid
  default_checkpoint_policy:
    - before_external_action
    - before_destructive_write
    - before_completion_if_high_impact
```

## 14. 主要取捨與判斷

### 14.1 不做 agent personal memory

優點：
- 可預測
- 可重現
- 好 debug

缺點：
- 少了擬人化魅力
- 少了 agent 角色成長感

判斷：
- 對產品穩定性更重要，MVP 應明確不做

### 14.2 PM hidden by default

優點：
- UX 簡單
- 使用者心智負擔低

缺點：
- 專業使用者一開始看不到完整內部結構

判斷：
- 預設隱藏，但在 task detail / debug mode 可以看

### 14.3 Filesystem as truth + SQLite as operational state

優點：
- 可讀
- 可備份
- 可檢查
- 與 local-first 一致

缺點：
- 某些查詢效率較低
- 需要索引層幫 UI

判斷：
- 這是正確取捨

### 14.4 多 runtime 模式

優點：
- 覆蓋更多使用者
- 經濟模型更強

缺點：
- adapter 變多
- 測試矩陣變大

判斷：
- 必須支持，但 MVP 先做最少數量

## 15. MVP 必須實作到的系統能力

MVP 至少要完成：
- Company DNA schema
- Role schema
- Mission schema
- Approval schema
- Run budget policy
- Company memory + mission memory
- Executor abstraction
- API mode
- 至少一種 subscription executor mode
- Writable scope enforcement
- Mission pause / resume
- Audit log

## 16. 最後的系統結論

Praetor 的系統核心不是「讓很多 agent 自由互動」。

而是：

**用角色、治理、記憶、mission 邊界與執行器抽象，把 AI 變成一間可控、可追溯、可持續運作的公司。**
