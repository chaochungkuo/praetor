# Praetor UI 重建 Playbook（給 Codex 執行用）

Status: source of truth · v1 · 2026-05-12

這份文件是 Praetor v1 UI 重建的完整腳本。Codex 應該按照「Migration plan」一節一個 commit 一個 commit 執行，每個 commit 完成後跑 acceptance checklist 才能進下一個。

---

## 0. Context（給 Codex 的快速 onboarding）

Praetor 是一個 local-first AI company OS。當前狀態：

- **後端**已經做完 5 個 foundation commits：刪掉 workspace-steward layer、加入持久化的 mission worker queue、CEO planner 改 retrieval-windowed、FilesystemStore 抽出獨立模組、Jinja 翻譯表抽出獨立模組。
- **後端 API 不再變動**。所有 JSON endpoints 已穩定，列表見第 6 節。
- **前端有兩條 UI 並存的問題**：
  - 12 個 Jinja server-rendered 頁面（在 `apps/api/praetor_api/ui.py` + `apps/api/praetor_api/templates/`）
  - 一個極簡 React SPA（只有 `/office` 一頁，在 `apps/web/frontend/src/main.tsx`，1,071 行 single-file）
- **本次重建的目標**：把所有 working surfaces 收斂到 React SPA，最後刪掉所有 Jinja 頁面，`ui.py` 只剩 onboarding / login 兩個 HTML 入口。

### 不要做的事

- 不要新增後端 endpoint（除非 acceptance checklist 明確要求）
- 不要動 `apps/api/praetor_api/_filesystem_store.py`、`storage.py`、`service.py` 的 method 定義
- 不要動 `bridges/praetor-execd/`
- 不要把已棄用的 file-asset / workspace-reconciliation 加回來
- 不要引入 Redux、Zustand、MobX、styled-components、emotion、MUI、Chakra
- 不要做 board view / Kanban（v1 只做 list）
- 不要做 mobile responsive 到 phone 解析度（v1 桌面為主，平板能用即可）

---

## 1. Design DNA

> **「平靜的入口 + 密集的工作面」**

`/office` 是董事長每天打開 Praetor 的「早安畫面」，氣質要平靜、留白多、prompt 為中心（參考：AI design generator dashboards、Linear inbox）。其它頁面是 command center，密集但乾淨（參考：Linear、ClickUp dashboards 的 metric + table 結構）。

### 1.1 配色 (CSS tokens)

放在 `apps/web/frontend/src/lib/tokens.css`：

```css
:root {
  /* Surfaces */
  --bg-app: #F7F7F8;
  --bg-card: #FFFFFF;
  --bg-subtle: #F1F2F4;
  --bg-hover: #ECECEF;

  /* Borders & dividers */
  --border-hairline: rgba(15, 17, 21, 0.08);
  --border-focus: #3B5BFD;

  /* Text */
  --fg-default: #0A0A0A;
  --fg-muted: #5C5F66;
  --fg-subtle: #8A8D94;
  --fg-on-accent: #FFFFFF;

  /* Accent */
  --accent: #3B5BFD;
  --accent-hover: #2F4DE0;
  --accent-soft: #EEF1FF;

  /* Status pills (bg / fg pairs) */
  --status-active-bg: #E7F5EB;     --status-active-fg: #126B2C;
  --status-running-bg: #E5EEFF;    --status-running-fg: #234CD6;
  --status-waiting-bg: #FFF3D6;    --status-waiting-fg: #8A5B00;
  --status-blocked-bg: #FCE6E6;    --status-blocked-fg: #B0271A;
  --status-done-bg: #ECECEF;       --status-done-fg: #3D4148;
  --status-failed-bg: #FCE6E6;     --status-failed-fg: #B0271A;
  --status-paused-bg: #F1ECFF;     --status-paused-fg: #5A37C8;

  /* Shadows */
  --shadow-card: 0 1px 2px rgba(15, 17, 21, 0.04), 0 0 0 1px var(--border-hairline);
  --shadow-popover: 0 8px 24px rgba(15, 17, 21, 0.12), 0 0 0 1px var(--border-hairline);

  /* Radius */
  --radius-card: 16px;
  --radius-input: 12px;
  --radius-pill: 9999px;
  --radius-button: 10px;

  /* Type */
  --font-sans: "Inter", "Noto Sans TC", ui-sans-serif, system-ui, -apple-system, sans-serif;
  --font-mono: "JetBrains Mono", ui-monospace, monospace;
}

[data-theme="dark"] {
  --bg-app: #0B0C0E;
  --bg-card: #131418;
  --bg-subtle: #1B1D22;
  --bg-hover: #22252B;

  --border-hairline: rgba(255, 255, 255, 0.08);

  --fg-default: #F5F6F8;
  --fg-muted: #9CA0A8;
  --fg-subtle: #6E727A;

  --accent: #6B85FF;
  --accent-hover: #8197FF;
  --accent-soft: #1A1F36;

  --status-active-bg: #0F2C18;     --status-active-fg: #6BCB87;
  --status-running-bg: #0F1D3D;    --status-running-fg: #8DA3FF;
  --status-waiting-bg: #2E2204;    --status-waiting-fg: #FFD27A;
  --status-blocked-bg: #2E0F0E;    --status-blocked-fg: #FF8A80;
  --status-done-bg: #1B1D22;       --status-done-fg: #B0B4BC;
  --status-failed-bg: #2E0F0E;     --status-failed-fg: #FF8A80;
  --status-paused-bg: #1F1838;     --status-paused-fg: #B59AFF;

  --shadow-card: 0 0 0 1px var(--border-hairline);
  --shadow-popover: 0 8px 24px rgba(0, 0, 0, 0.6), 0 0 0 1px var(--border-hairline);
}
```

### 1.2 Type scale

| Token | Size | Line | Weight | Use |
|---|---|---|---|---|
| `text-display` | 32px | 1.2 | 600 | `/office` Good morning headline, login title |
| `text-h1` | 24px | 1.3 | 600 | page title |
| `text-h2` | 18px | 1.4 | 600 | section title |
| `text-body` | 14px | 1.5 | 400 | default |
| `text-small` | 13px | 1.4 | 400 | secondary |
| `text-meta` | 12px | 1.4 | 500 | uppercase labels, timestamps |
| `text-code` | 13px | 1.5 | 400 | monospace for IDs, JSON |

Headings always use letter-spacing -0.01em; uppercase meta uses +0.06em.

### 1.3 Spacing

8px base grid. Common values: 4 / 8 / 12 / 16 / 20 / 24 / 32 / 40 / 56.

Card padding: 24px (desktop), 16px (tablet).
Section gap: 24px between cards in a column, 16px in a row.

### 1.4 Motion

- Default transition: `150ms cubic-bezier(0.2, 0, 0.1, 1)`
- Page transitions: none (instant route swap; only data fade-in)
- Hover state: opacity / background only, no scale / no glow
- Loading: skeleton blocks, not spinners (Linear style)
- 禁止：粒子、glassmorphism、blur 過重的 popover、漸層按鈕（漸層只允許出現在 `/office` 的「Send to CEO」按鈕和 login/onboarding 的天空背景）

### 1.5 Accessibility

- 所有 interactive 元素 keyboard reachable
- Focus ring: 2px solid var(--border-focus) + 2px offset
- Color contrast ≥ WCAG AA
- 全部 icon-only button 必須有 `aria-label`
- `prefers-reduced-motion` 時 transition duration → 0

---

## 2. Information Architecture

### 2.1 Top-level routes（5 條）

| Route | 名稱 | 取代的 Jinja 頁面 |
|---|---|---|
| `/office` | Office | `/app/praetor`, `/app/inbox`, 現有的 `/office` |
| `/missions` + `/missions/:id` | Missions | `/app/tasks`, `/app/overview`, `/app/missions/:id`, `/app/activity` |
| `/memory` | Memory | `/app/memory`, `/app/decisions`, `/app/meetings` |
| `/runtime` | Runtime | `/app/models`, `/app/agents`（admin tabs 部分） |
| `/settings` | Settings | `/app/settings`, `/app/agents`（org tabs 部分） |

預設 landing 是 `/office`。

### 2.2 App shell

```
┌─────────────────────────────────────────────────────────────────┐
│  TopBar: [Workspace name]  [⌘K omnibox]            [● runtime]  │
├──────┬──────────────────────────────────────────┬───────────────┤
│ Rail │  Page content                            │ Right panel   │
│ 56px │  (max-width 1280px, centered)            │ (optional,    │
│ ↔    │                                          │  per-page)    │
│ 240  │                                          │ 320px         │
└──────┴──────────────────────────────────────────┴───────────────┘
```

- Rail 預設 collapsed (56px icon only)；`⌘\` 或 hover 展開到 240px
- TopBar 高 56px，固定
- Right panel 可選，由各頁決定是否顯示

### 2.3 Sidebar groups

```
✦  Office
▤  Missions
☷  Memory
⚡  Runtime
⚙  Settings
────────────────
👤 Owner avatar / menu
```

展開時群組標籤：`Workspace` (上 5 個) / `Account` (下 1 個)。

### 2.4 Keyboard shortcuts (Linear-style)

| Combo | Action |
|---|---|
| `⌘K` | Open command palette |
| `⌘\` | Toggle sidebar |
| `g o` | Go to Office |
| `g m` | Go to Missions |
| `g r` | Go to Runtime |
| `g k` | Go to Memory (knowledge) |
| `g s` | Go to Settings |
| `c` | New mission (anywhere) |
| `/` | Focus search in current page |
| `?` | Show keyboard shortcuts overlay |
| `esc` | Close any modal/popover |

實作用 [`tinykeys`](https://github.com/jamiebuilds/tinykeys)（或自己寫的 keymap hook）。

### 2.5 Command palette (⌘K)

固定區塊：

1. **Quick actions**: New mission · New decision · Open CEO chat
2. **Pages**: Office / Missions / Memory / Runtime / Settings
3. **Recent missions**: 最近 5 個 mission
4. **Settings shortcuts**: Switch language · Toggle dark mode · Logout

Fuzzy search 用 [`cmdk`](https://cmdk.paco.me/) library。

---

## 3. Page specs（細到 Codex 能直接寫）

### 3.1 `/office`

**佈局**：兩欄。主欄 + 右側 rail。

```tsx
<AppShell rightPanel={<NeedsDecisionPanel />}>
  <OfficePage>
    <GreetingHeader />                  {/* "Good morning, {owner}" + briefing line */}
    <CEOChat />                         {/* big prompt input */}
    <Section title="Tasks in flight">
      <MissionCardGrid missions={runningMissions} />
    </Section>
    <Section title="Recent memory">
      <MemoryTimeline events={recentMemoryEvents} />
    </Section>
  </OfficePage>
</AppShell>
```

**GreetingHeader**:
- 早 / 中 / 晚問候依時間切換
- 主標 `text-display`：「Good morning, {owner_name}」（zh-TW: 「早安，{owner_name}」）
- 次標 `text-body fg-muted`：「目前 N 個任務在跑，M 件等你決定」
- 上 padding 40px、下 24px

**CEOChat**:
- 卡片寬度 max 720px，置中
- 大 textarea：min-height 120px，auto-grow 到 max 320px
- 左上角 ✦ icon + placeholder：「想跟 CEO 說什麼？」
- 左下角：附件 icon + 麥克風 icon
- 右下角：[Send to CEO] 按鈕（**唯一允許的漸層按鈕**：blue → indigo）
- 送出後 input 清空，回應顯示在輸入框上方的「latest exchange」氣泡（不是聊天室；只顯示最新一輪）
- 全部對話記錄收進 `<details>` 折疊區，預設關閉
- 行為對應 `POST /api/office/conversation`、`GET /api/office/conversation`

**MissionCardGrid**:
- 3-column grid (1280px), 2-column (1024px), 1-column (640px)
- 每張卡片：mission title、status pill、progress bar（如有 run_attempt）、owner role、最後更新時間
- 點卡片 → `/missions/{id}`

**MemoryTimeline**:
- 最近 5 個 audit_event 中 type 為 `memory_update` / `decision_*` / `mission_completed` 的項目
- 每行：icon + title + relative time（「8 分鐘前」）

**NeedsDecisionPanel (right rail)**:
- `Needs Decision` 區：來自 `GET /approvals` (status=pending) + escalations (status=pending)
  - 每項：mission title、reason、`[Approve]` `[Reject]` button
- `Runtime` 區：runtime dot + provider/model + last-sync 時間
- `Standing Orders` 區：最近 3 條，可 「全部 →」連到 /settings

**資料來源**：單一 `GET /api/office/snapshot` call（已存在），TanStack Query key `["office", "snapshot"]`，stale 30s。

---

### 3.2 `/missions`（列表）

```
┌──────────────────────────────────────────────────────────────────┐
│  Missions                              [+ New mission]           │
│  ───────────                                                      │
│  [All ▾]  [Status: any ▾]  [Domain: any ▾]   🔍 search           │
│                                                                   │
│  Status  Title                Owner   Priority  Updated   Progress│
│  ●●     Draft contract Acme  PM      high      2 hours   ────░80%│
│  ○○     Stop me              CEO     normal    1 day     done    │
│  ...                                                              │
└──────────────────────────────────────────────────────────────────┘
```

- 表頭可排序（Updated 預設 desc）
- Row hover → bg-hover
- Row click → 進詳情頁
- 多選 checkbox 留給 v2，先不做
- 資料來源：`GET /missions`，Query key `["missions", "list"]`

### 3.3 `/missions/:id`

頂部 banner：title + status pill + priority pill + [Run] [Pause] [Stop] [Enqueue]

Tab 列（用 URL 子路徑而非 query 參數）：

| Tab | Content | API |
|---|---|---|
| Briefing (default) | summary / requested_outputs / governance / board_briefings | `GET /missions/{id}`, `GET /api/missions/{id}/board-briefings` |
| Tasks | task list + run_attempts + jobs queue | `GET /api/missions/{id}/run-attempts`, `GET /api/missions/{id}/jobs` |
| Decisions | approvals + escalations + completion contract | `GET /approvals`, `GET /api/missions/{id}/completion-contract` |
| Files | bridge_runs.changed_files + workspace scope | `GET /api/missions/{id}/workspace-scope`, `GET /api/missions/{id}/timeline` |
| Activity | timeline + agent_messages + work_sessions | `GET /api/missions/{id}/timeline`, `GET /api/missions/{id}/agent-messages`, `GET /api/missions/{id}/work-sessions` |

**Jobs queue 顯示**：
- 用 `GET /api/missions/{id}/jobs` 取最近 10 個 job
- 每個 job 顯示 status pill、enqueued_at、started_at、finished_at、error if any
- `[Run]` 按鈕現在預設呼叫 `POST /api/missions/{id}/enqueue`（非阻塞），不再阻塞前端
- 若 job 在 running 狀態，按鈕變成 disabled「Job running…」

**New mission modal**:
- Form fields: title, summary, domains (chips), priority (radio), requested_outputs (multi-line)
- 送出 `POST /missions`
- 成功後 navigate 到新 mission detail

---

### 3.4 `/memory`

```
┌──────────────────────────────┬───────────────────────────────────┐
│ TREE (220px)                 │ DETAIL                            │
│                              │                                   │
│ ▾ Wiki (8)                   │ # CEO Memory.md                   │
│   · CEO Memory.md            │                                   │
│   · Company DNA.md           │ ## 2026-05-12                     │
│   · ...                      │ Stop spending on cosmetic AI...   │
│ ▾ Standing orders (5)        │                                   │
│   · 對外通訊一律升級         │ ─── Retrieval Preview ───────────│
│   · ...                      │ 過去 7 天被 CEO chat 引用 3 次    │
│ ▾ Decisions (12)             │ 最近一次：今天 09:42              │
│   · Ship MVP without...      │ Prompt context score: 0.78        │
│ ▾ Open questions (3)         │                                   │
└──────────────────────────────┴───────────────────────────────────┘
```

- Tree 用 collapsible groups (Wiki / Standing orders / Decisions / Open questions)
- 點 item → 右側 markdown render
- 右下顯示 retrieval preview（先 placeholder「coming soon」，等後端 endpoint）
- 編輯：v1 只支援 Standing Order 的新增（form），Wiki edit 與 Decision 編輯都 v2 再做（v1 顯示 read-only + 「在你的編輯器修改 markdown 後 Praetor 會自動 reload」）
- 資料來源：`GET /api/knowledge` + `GET /api/governance/review`

---

### 3.5 `/runtime`

```
┌──────────────────────────────────────────────────────────────────┐
│  Runtime                                                          │
│                                                                   │
│  ┌─ Health Hero ────────────────────────────────────────────┐   │
│  │  ● Healthy                                                │   │
│  │  API mode · openai · gpt-4.1-mini · last sync 12s ago     │   │
│  │  [Test connection]   [Switch provider]                    │   │
│  └───────────────────────────────────────────────────────────┘   │
│                                                                   │
│  [Models] [Executors] [Recent runs] [Usage]                       │
│                                                                   │
│  Tab content...                                                   │
└──────────────────────────────────────────────────────────────────┘
```

- Hero 卡片狀態：`Healthy` (green) / `Misconfigured` (amber) / `Offline` (red)
- Models tab: provider/model 切換、API key 設定（form post 到 `/app/settings/runtime` — 注意這仍是 Jinja，先用 fetch 改成 JSON 路徑，需要 backend 加一個 `POST /api/settings/runtime`，**這是唯一允許新增的後端 endpoint**）
- Executors tab: 顯示 `GET /api/office/snapshot` 的 `runtime_health.executors`
- Recent runs tab: `GET /api/missions/{id}/run-attempts`（跨 mission）— 列前 20 筆
- Usage tab: 用 `recharts` 畫單線圖（tokens / day），資料聚合自 run_attempts

---

### 3.6 `/settings`

縱向 tab，左寬 200px / 右 form 區。

| Tab | Form / Section |
|---|---|
| Owner | name / email / language / change password |
| Governance | autonomy_mode / require_approval categories / run_budget defaults |
| Workspace | workspace_root (read-only) / permissions allow/deny lists |
| Roles | list `agent_roles` + `agent_permission_profiles`（v1 read-only） |
| AI | re-link to /runtime（避免重複設定） |
| Telegram | bot_token / webhook_secret / allowed_user_id / pairing code |
| Advanced | export schemas / debug routes / reset (危險區域) |

**API**：`GET /settings`（read），其它 form post 暫時仍指向既有的 Jinja routes，等 backend 補 JSON endpoint（這部分 v1 可保留 Jinja form post，因為 settings 是低頻使用面）。

---

### 3.7 `/app/login` 和 onboarding（保留 Jinja，但翻新視覺）

這兩頁是唯一允許保留 Jinja 的入口。但視覺要翻新成「Image 1 天空漸層」氣質：

- 全頁背景：linear-gradient(180deg, #B6D4FA 0%, #E8F1FE 50%, #FFFFFF 100%)
- 中央卡片：max-width 480px、white bg、shadow-popover
- 字體與 token 跟 SPA 同步
- 更新 `apps/api/praetor_api/static/praetor.css` 中對應的 selector（不要動到 SPA 那邊）

Onboarding wizard 步驟視覺也用同一張卡片，每步切換用淡入。

---

## 4. Component primitives

放在 `apps/web/frontend/src/components/ui/`。全部複製 [shadcn/ui](https://ui.shadcn.com/) 的 source 後改 tokens，不要 install MUI/Chakra。

| 元件 | 檔名 | 仿照 |
|---|---|---|
| `Button` (variants: primary / secondary / ghost / danger / gradient) | `Button.tsx` | shadcn |
| `Card` | `Card.tsx` | shadcn |
| `Badge` | `Badge.tsx` | shadcn |
| `StatusPill` | `StatusPill.tsx` | 自製（綁定 status → token 配色） |
| `Input` / `Textarea` | `Input.tsx`, `Textarea.tsx` | shadcn |
| `Select` | `Select.tsx` | radix-ui/react-select |
| `Dialog` (modal) | `Dialog.tsx` | radix-ui/react-dialog |
| `Popover` | `Popover.tsx` | radix-ui/react-popover |
| `Tooltip` | `Tooltip.tsx` | radix-ui/react-tooltip |
| `Tabs` | `Tabs.tsx` | radix-ui/react-tabs |
| `DataTable` | `DataTable.tsx` | 自製，支援 sort / hover row / sticky header |
| `Skeleton` | `Skeleton.tsx` | 自製 div + shimmer |
| `Avatar` | `Avatar.tsx` | radix-ui/react-avatar |
| `CommandPalette` | `CommandPalette.tsx` | cmdk |
| `EmptyState` | `EmptyState.tsx` | 自製：icon + headline + action |

### 4.1 StatusPill API

```tsx
type MissionStatus =
  | "planned" | "staffing" | "active" | "review" | "reviewing"
  | "ready_for_ceo" | "needs_decision" | "waiting_approval"
  | "paused" | "resumed" | "completed" | "archived" | "failed";

type StatusKind = "active" | "running" | "waiting" | "blocked" | "done" | "failed" | "paused";

function statusKind(s: MissionStatus): StatusKind { /* lookup */ }

<StatusPill kind={statusKind(mission.status)}>{label(mission.status)}</StatusPill>
```

Pill 是 `--radius-pill`、`12px 8px` padding、`text-meta` 大小、bg/fg 用對應 token pair。

### 4.2 Button gradient variant 只給 CEO Send 用

```css
.btn-gradient {
  background: linear-gradient(135deg, #3B5BFD 0%, #6B85FF 100%);
  color: white;
}
```

別處的 primary button 一律 `bg: #0A0A0A`、`color: white`。

---

## 5. Tech stack（已確認，不要改）

| Concern | Choice | 理由 |
|---|---|---|
| Build | Vite (已存在) | 不變 |
| Framework | React 19 (已存在) | 不變 |
| Router | `react-router-dom@6` | 與 React 18+ 兼容、社群最大 |
| Server state | `@tanstack/react-query@5` | 取代手寫 useEffect+fetch |
| Forms | `react-hook-form@7` + `zod@3` | type-safe form validation |
| Icons | `lucide-react` (已存在) | 不變 |
| Styling | Tailwind v3 + CSS tokens | 不要 styled-components |
| UI primitives | shadcn/ui pattern + radix-ui | 沒有 vendor 鎖死 |
| Cmd palette | `cmdk@1` | Linear/Vercel 都用這個 |
| Keyboard | `tinykeys` | 輕量 |
| Date | `date-fns@3` (tree-shakable) | 不要 moment |
| Markdown render | `react-markdown@9` + `remark-gfm` | for /memory |
| Charts | `recharts@2` | for /runtime usage |
| Dark mode | 自寫 ThemeProvider + `data-theme` attribute | 不需要 next-themes |

### 5.1 npm install 命令

```bash
cd apps/web
npm install --save \
  react-router-dom@^6 \
  @tanstack/react-query@^5 \
  react-hook-form@^7 zod@^3 \
  @radix-ui/react-dialog@^1 @radix-ui/react-popover@^1 \
  @radix-ui/react-tooltip@^1 @radix-ui/react-tabs@^1 \
  @radix-ui/react-select@^2 @radix-ui/react-avatar@^1 \
  @radix-ui/react-checkbox@^1 @radix-ui/react-dropdown-menu@^2 \
  cmdk@^1 tinykeys@^3 date-fns@^3 \
  react-markdown@^9 remark-gfm@^4 recharts@^2 \
  clsx@^2 class-variance-authority@^0.7 tailwind-merge@^2

npm install --save-dev \
  tailwindcss@^3 postcss@^8 autoprefixer@^10 \
  @types/node
```

### 5.2 Tailwind 設定

`apps/web/tailwind.config.ts`：

```ts
import type { Config } from "tailwindcss";

export default {
  content: ["./frontend/index.html", "./frontend/src/**/*.{ts,tsx}"],
  darkMode: ["class", "[data-theme='dark']"],
  theme: {
    extend: {
      colors: {
        app: "var(--bg-app)",
        card: "var(--bg-card)",
        subtle: "var(--bg-subtle)",
        hover: "var(--bg-hover)",
        accent: "var(--accent)",
        "accent-hover": "var(--accent-hover)",
        "accent-soft": "var(--accent-soft)",
        fg: "var(--fg-default)",
        muted: "var(--fg-muted)",
        "border-hairline": "var(--border-hairline)",
      },
      fontFamily: {
        sans: "var(--font-sans)",
        mono: "var(--font-mono)",
      },
      borderRadius: {
        card: "var(--radius-card)",
        input: "var(--radius-input)",
        pill: "var(--radius-pill)",
        button: "var(--radius-button)",
      },
      boxShadow: {
        card: "var(--shadow-card)",
        popover: "var(--shadow-popover)",
      },
      transitionTimingFunction: {
        ease: "cubic-bezier(0.2, 0, 0.1, 1)",
      },
    },
  },
  plugins: [],
} satisfies Config;
```

---

## 6. Backend API contract（不變，不要新增）

所有 endpoint 都需要 cookie session + `X-CSRF-Token` header（CSRF token 從 `GET /auth/session` 取，存進 TanStack Query cache）。

### 6.1 Auth & onboarding

| Method | Path | 用在 |
|---|---|---|
| GET | `/auth/session` | App boot, 取 CSRF token + ui_language |
| POST | `/auth/login` | Login form |
| POST | `/auth/logout` | Logout menu |
| POST | `/onboarding/preview` | Onboarding wizard 預覽 |
| POST | `/onboarding/complete` | Onboarding 完成（需要 `X-Praetor-Setup-Token` header） |
| GET | `/settings` | 讀目前 settings |

### 6.2 Office

| GET | `/api/office/snapshot` | `/office` 主頁所有資料 |
| GET | `/api/office/conversation` | CEO chat history |
| POST | `/api/office/conversation` | 送 CEO 訊息（body: `{body, related_mission_id?}`） |

### 6.3 Missions

| GET | `/missions` | mission list |
| POST | `/missions` | create mission |
| GET | `/missions/{id}` | mission detail |
| POST | `/missions/{id}/run` | run mission (synchronous, blocks) |
| POST | `/api/missions/{id}/enqueue` | enqueue mission job (非阻塞，**新建議用法**) |
| POST | `/missions/{id}/pause` |  |
| POST | `/missions/{id}/continue` |  |
| POST | `/missions/{id}/stop` |  |
| POST | `/api/missions/{id}/executor-control` | pause/resume executor |

### 6.4 Mission detail tabs

| GET | `/api/missions/{id}/timeline` | events |
| GET | `/api/missions/{id}/agent-messages` | AI internal conversation |
| GET | `/api/missions/{id}/work-sessions` | work sessions |
| GET | `/api/missions/{id}/run-attempts` | run attempts |
| GET | `/api/missions/{id}/jobs` | **mission queue jobs (NEW)** |
| GET | `/api/missions/{id}/work-trace` | stages + work events + contracts |
| GET | `/api/missions/{id}/knowledge` | mission knowledge snapshot |
| GET | `/api/missions/{id}/workspace-scope` | scope |
| GET | `/api/missions/{id}/completion-contract` | contract |
| GET | `/api/missions/{id}/board-briefings` | board briefings |
| POST | `/api/missions/{id}/board-briefings` | create briefing |
| GET | `/api/missions/{id}/memory-promotion` | promotion reviews |
| POST | `/api/missions/{id}/memory-promotion` | create promotion review |
| POST | `/missions/{id}/meeting` | create review meeting |

### 6.5 Jobs

| GET | `/api/mission-jobs/{job_id}` | poll a single job status |

### 6.6 Approvals & governance

| GET | `/approvals` | list pending |
| POST | `/approvals` | create approval |
| POST | `/approvals/{id}/approved` | approve |
| POST | `/approvals/{id}/rejected` | reject |
| GET | `/api/governance/review` | latest review |
| POST | `/api/governance/review` | run review |

### 6.7 Knowledge / Memory

| GET | `/api/knowledge` | full snapshot |
| GET | `/api/workflow` | workflow contract |

### 6.8 Organization

| GET | `/api/organization` | agents/teams/delegations/escalations |
| POST | `/api/organization/skill-sources` | add skill source |
| POST | `/api/organization/skill-sources/{id}/import` | import skills |
| POST | `/api/organization/skills/{id}/status` | approve/reject skill |

### 6.9 TanStack Query keys 標準

```ts
// apps/web/frontend/src/lib/queryKeys.ts
export const qk = {
  session: ["session"] as const,
  settings: ["settings"] as const,
  officeSnapshot: ["office", "snapshot"] as const,
  conversation: ["office", "conversation"] as const,
  missions: ["missions"] as const,
  mission: (id: string) => ["missions", id] as const,
  missionJobs: (id: string) => ["missions", id, "jobs"] as const,
  missionTimeline: (id: string) => ["missions", id, "timeline"] as const,
  missionAgentMessages: (id: string) => ["missions", id, "agent-messages"] as const,
  missionWorkSessions: (id: string) => ["missions", id, "work-sessions"] as const,
  missionRunAttempts: (id: string) => ["missions", id, "run-attempts"] as const,
  missionWorkTrace: (id: string) => ["missions", id, "work-trace"] as const,
  missionKnowledge: (id: string) => ["missions", id, "knowledge"] as const,
  missionBoardBriefings: (id: string) => ["missions", id, "board-briefings"] as const,
  approvals: ["approvals"] as const,
  knowledge: ["knowledge"] as const,
  organization: ["organization"] as const,
  governanceReview: ["governance", "review"] as const,
  workflow: ["workflow"] as const,
  job: (jobId: string) => ["mission-jobs", jobId] as const,
};
```

### 6.10 CSRF + fetch wrapper

```ts
// apps/web/frontend/src/lib/api.ts
let csrfToken: string | null = null;

export function setCsrfToken(token: string) {
  csrfToken = token;
}

export async function api<T>(path: string, init: RequestInit = {}): Promise<T> {
  const method = (init.method ?? "GET").toUpperCase();
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(init.headers as Record<string, string>),
  };
  if (csrfToken && method !== "GET" && method !== "HEAD") {
    headers["X-CSRF-Token"] = csrfToken;
  }
  const res = await fetch(path, { ...init, credentials: "same-origin", headers });
  const env = await res.json();
  if (!res.ok || !env.ok) {
    throw new ApiError(env.error?.code ?? "http_error", env.error?.message ?? res.statusText, res.status);
  }
  return env.data as T;
}

export class ApiError extends Error {
  constructor(public code: string, message: string, public status: number) {
    super(message);
  }
}
```

---

## 7. Migration plan (commit by commit)

每個 commit 都要：
- 通過 `npm run typecheck`
- 通過 `npm run build`
- 通過後端 smoke (`pixi run app-import-check && pixi run app-smoke && pixi run app-ui-smoke`)
- 不能引入任何 `console.error` 或 unhandled promise rejection
- commit message 用第二人稱現在式：「Add app shell」、「Replace tasks page with /missions」

### Commit 1 — Wipe legacy SPA and install foundation

**動作**：
1. 砍掉 `apps/web/frontend/src/main.tsx`（保留 git history，但檔案重寫）
2. 砍掉 `apps/web/frontend/src/styles.css`、`api.ts`、`types.ts`
3. 安裝第 5.1 節的所有 npm packages
4. 建立 `apps/web/tailwind.config.ts`、`apps/web/postcss.config.js`
5. 建立 `apps/web/frontend/src/lib/tokens.css`（複製第 1.1 節）
6. 建立 `apps/web/frontend/src/index.css`：

```css
@tailwind base;
@tailwind components;
@tailwind utilities;
@import "./lib/tokens.css";

html, body { background: var(--bg-app); color: var(--fg-default); font-family: var(--font-sans); }
body { font-size: 14px; line-height: 1.5; }
* { box-sizing: border-box; }
```
7. 確保 `frontend/index.html` 載入 Inter 與 Noto Sans TC（preconnect + font-display swap）

**Acceptance**：
- `npm run build` 出來的 bundle <500KB gzipped
- 訪問 `/office` 顯示一個空白頁但底色、字體正確

---

### Commit 2 — App shell + routing + theme

**動作**：
1. 建立 `apps/web/frontend/src/lib/` 模組：
   - `api.ts`（第 6.10 節）
   - `queryKeys.ts`（第 6.9 節）
   - `auth.ts`（`useSession()` hook，從 `/auth/session` 取 session + csrf）
   - `theme.ts`（`useTheme()` hook，read/write `localStorage("praetor-theme")` → set `data-theme` on `<html>`）
   - `i18n.ts`（兩個 dict：`en` / `zh-TW`，shell-only 用語；長文還是給後端產）
2. 建立 `components/AppShell.tsx`、`Sidebar.tsx`、`TopBar.tsx`、`CommandPalette.tsx`、`ThemeToggle.tsx`
3. 建立 5 個空白 page：`Office.tsx`、`Missions.tsx`、`Memory.tsx`、`Runtime.tsx`、`Settings.tsx`（每個都用 `<EmptyState>` 顯示 placeholder）
4. 建立 `App.tsx` + 新版 `main.tsx`：
   - `QueryClientProvider`
   - `BrowserRouter`
   - `<AuthGate>` (未登入導向 `/app/login`)
   - `<AppShell>` 包 5 條 Route
5. 全域鍵盤：`⌘K`, `⌘\`, `g o/m/k/r/s`
6. Command palette 內容先放：pages + dark mode toggle + logout

**Acceptance**：
- 5 條 route 都能切換
- `⌘K` 開 palette
- 切換 dark mode 即時生效並 persist
- Sidebar collapse/expand 動畫順 (150ms)
- 直接訪 `/office` (未登入) → redirect 到 `/app/login`
- 已登入 → 進 `/office` 看到 `<EmptyState>` 「Office coming soon」

---

### Commit 3 — `/office` 上線（取代既有 React `/office`）

**動作**：
1. 實作 `pages/Office.tsx` 完整版（第 3.1 節）
2. 子元件：`GreetingHeader.tsx`、`CEOChat.tsx`、`MissionCardGrid.tsx`、`MemoryTimeline.tsx`、`NeedsDecisionPanel.tsx`
3. CEO chat 的「latest exchange」氣泡：送出後 50ms 內 optimistic 顯示 chairman 訊息，CEO 回應到了再淡入
4. 中文語音輸入：保留現有的 `webkitSpeechRecognition`，再加一條 fallback 路徑：點麥克風 → 錄音 → 上傳到 `POST /app/ceo/transcribe`（Jinja 路徑，先共用）
5. `NeedsDecisionPanel` 的 approve/reject 按鈕直接 hit `POST /approvals/{id}/{status}`，成功後 invalidate `qk.officeSnapshot`

**Acceptance**：
- Good morning 文字在不同時段顯示對 (早 / 中 / 晚)
- 沒任務時顯示 EmptyState「準備好開始第一個任務嗎？」+ [建立任務] button
- 送出 CEO 訊息後 1.5s 內看到 CEO 回應（依 backend planner 速度）
- 滑鼠 hover mission card → bg-hover + cursor pointer
- 點 mission card → 進 `/missions/{id}`

---

### Commit 4 — `/missions` + `/missions/:id`（刪掉 Jinja `/app/tasks` 和 `/app/missions/:id`）

**動作**：
1. 實作 `pages/Missions.tsx`（list，第 3.2 節）
2. 實作 `pages/MissionDetail.tsx`（tabs，第 3.3 節）
3. 子元件：`MissionTable.tsx`、`NewMissionDialog.tsx`、`MissionTabBriefing.tsx`、`MissionTabTasks.tsx`、`MissionTabDecisions.tsx`、`MissionTabFiles.tsx`、`MissionTabActivity.tsx`
4. `[Run]` 改用 `POST /api/missions/{id}/enqueue`，並 poll `/api/missions/{id}/jobs` 每 2s 直到最新 job `status` 是 terminal
5. **刪掉 Jinja**：
   - `apps/api/praetor_api/ui.py` 中的 `/app/tasks`、`/app/overview`、`/app/activity`、`/app/missions/{mission_id}`、`/app/missions/{mission_id}/events`、`/app/missions/{mission_id}/run`、`/app/missions/{mission_id}/pause`、`/app/missions/{mission_id}/continue`、`/app/missions/{mission_id}/stop`、`/app/missions/{mission_id}/executor-control`、`/app/missions/{mission_id}/meeting`、`/app/missions/{mission_id}/memory-promotion`、`/app/missions/{mission_id}/board-briefing`、`/app/missions/{mission_id}/approval`、`/app/approvals/{approval_id}/{status}` 全部刪除
   - 對應 templates：`tasks.html`、`overview.html`、`activity.html`、`mission_detail.html` 刪除
   - `_translations.py` 中只屬於這幾頁的 key 刪除（其它頁仍會用到的保留）

**Acceptance**：
- `/missions` list 載入 < 1s
- 新建 mission → 自動跳到 detail 頁
- 點 [Run] → 看到 job 出現在 Tasks tab 並逐步從 queued → running → completed
- `pixi run app-ui-smoke` 中對應的 `tasks_has_board`、`mission_detail_has_*` 檢查項要從 smoke 中**刪除**（Codex 改 smoke 檔）

---

### Commit 5 — `/memory`（刪掉 `/app/memory`, `/app/decisions`, `/app/meetings`, `/app/inbox`）

**動作**：
1. 實作 `pages/Memory.tsx`（第 3.4 節）
2. 子元件：`MemoryTree.tsx`、`MemoryDetail.tsx`、`StandingOrderForm.tsx`
3. 用 `react-markdown` + `remark-gfm` render
4. **刪掉 Jinja**：`/app/memory`、`/app/decisions`、`/app/meetings`、`/app/inbox`、`/app/inbox/governance-review`，對應 templates 與 i18n key 刪除

**Acceptance**：
- 樹節點展開/收合動畫順
- 點 wiki page → 右側顯示 markdown
- 新增 standing order → form 提交後 tree 自動 refresh

---

### Commit 6 — `/runtime`（刪掉 `/app/models`）

**動作**：
1. 實作 `pages/Runtime.tsx`（第 3.5 節）
2. 子元件：`RuntimeHealthCard.tsx`、`ModelsTab.tsx`、`ExecutorsTab.tsx`、`RecentRunsTab.tsx`、`UsageChart.tsx`
3. **後端只允許這個新增**：在 `apps/api/praetor_api/main.py` 加一個 `POST /api/settings/runtime`（payload: `RuntimeSelection`），內部呼叫既有的 `service.update_runtime()`
4. **刪掉 Jinja**：`/app/models`、`/app/settings/runtime`（form post path）、`/app/settings/runtime/test`，對應 template 與 i18n key 刪除

**Acceptance**：
- Health hero 顯示正確 dot 顏色
- Switch provider → 表單 submit → snapshot refresh → hero 反映新 model
- Usage chart 顯示最近 7 天的 token 趨勢（即使 0 也要顯示空圖而非空白）

---

### Commit 7 — `/settings`（縮減 Jinja settings 為僅 form post）

**動作**：
1. 實作 `pages/Settings.tsx`（第 3.6 節）
2. 各 tab 顯示 read-only 資料 + 「Edit」按鈕，按 Edit 開 Dialog 顯示既有 Jinja form（用 iframe）— v1 妥協方案，**v2 才把 settings form 全 JSON 化**
3. 例外：Telegram 的「Create pairing code」按鈕直接 hit `POST /app/settings/telegram/pairing-code` 並顯示回傳碼
4. **刪掉 Jinja**：`/app/agents`、`/app/agents/skill-sources`、`/app/agents/skill-sources/{id}/import`、`/app/agents/skills/{id}/status`，對應 template + i18n
5. `apps/api/praetor_api/ui.py` 至此應 < 600 行（只剩 `/app/login`, `/app/welcome`, `/app/praetor` (onboarding), `/app/settings/*` form posts, `/app/onboarding`, `/app/login`/`/app/logout`, `/app/set-language/*`, `/m/briefing`(mobile)）

**Acceptance**：
- 5 個 SPA tab 全部能看到對應資料
- Telegram pairing code 顯示出來
- 後端 routes 數 < 95（之前 102）

---

### Commit 8 — Onboarding & login 視覺翻新

**動作**：
1. 更新 `apps/api/praetor_api/static/praetor.css` 中 `/app/login`、`/app/welcome`、`/app/praetor` 三頁 CSS，套上第 3.7 節的天空漸層
2. 字體切到 Inter + Noto Sans TC
3. 表單視覺對齊 SPA token

**Acceptance**：
- Logout → `/app/login` 看到天空漸層
- 第一次安裝 → `/app/praetor` onboarding 視覺與漸層一致
- 漸層**不**出現在 `/office`、`/missions`、`/memory`、`/runtime`、`/settings`

---

### Commit 9 — i18n 統一

**動作**：
1. 寫一個 build-time script `apps/web/scripts/extract-translations.mjs`：讀 `apps/api/praetor_api/_translations.py` 用 regex 抓 dict，輸出 `apps/web/frontend/src/translations.json`
2. 在 `package.json` 加 `"prebuild": "node scripts/extract-translations.mjs"`
3. 把 `lib/i18n.ts` 改成從 `translations.json` 讀取，不再內嵌 dict
4. 跟後端共用同一份 zh-TW / en key

**Acceptance**：
- 前後端文字一致（不再各自漂移）
- `npm run build` 時自動執行 extract
- 新增一個 key 只要改 `_translations.py`，重新 build 即生效

---

## 8. 完成定義（整個重建結束時）

- [ ] `apps/web/frontend/src/main.tsx` < 100 行（純 bootstrap）
- [ ] `apps/api/praetor_api/ui.py` < 600 行（只剩 onboarding + login + mobile briefing）
- [ ] `apps/api/praetor_api/templates/` 只剩 `base.html`, `login.html`, `welcome.html`, `praetor.html` (onboarding), `m_briefing.html`
- [ ] `apps/api/praetor_api/static/praetor.css` 縮減到 < 800 行（只剩 onboarding/login 用）
- [ ] 後端 routes 總數 < 90
- [ ] 全部 pixi smoke 通過：`app-import-check`, `app-smoke`, `app-api-smoke`, `app-ui-smoke` (rewritten)、`app-auth-smoke`, `app-security-smoke`, `planner-smoke`
- [ ] `npm run typecheck && npm run build` 在 CI 通過
- [ ] Bundle size: main chunk < 400KB gzipped, total < 700KB gzipped
- [ ] Lighthouse: performance > 90, accessibility > 95 (desktop)
- [ ] Dark mode 在所有頁面可切換且 persist
- [ ] zh-TW / en 切換在所有 SPA 頁面生效

---

## 9. Codex 執行注意事項

1. **每個 commit 都要先讀這份 playbook 對應段落**，不要從 git log 推測意圖。
2. **遇到設計選擇衝突**：以這份文件為準；若文件未涵蓋，選 Linear 的做法。
3. **不要新增後端 endpoint**，除非 commit 6 的「POST /api/settings/runtime」這條已明確列出的例外。
4. **不要修改既有 Pydantic models**（除非 commit 期間發現 type bug）。
5. **每次刪 Jinja 頁面前**：先確認 SPA 對應頁能完整取代它，再刪。
6. **smoke tests 是 source of truth**：跑 `pixi run app-smoke` 失敗就要修，不要 skip。
7. **commit message** 用英文（與既有 commit history 一致），但程式碼註解和文件用 zh-TW 可。
8. **branch 策略**：每個 commit 直接 push 到 `claude/crazy-taussig-d75255` worktree branch；要開 PR 時再合到 main。
9. **無頭測試**：每個 commit 結束跑一輪 `npm run build && pixi run app-import-check && pixi run app-smoke` 三連。
10. **不確定就停**：如果 Codex 在某個 commit 改了 > 30 個檔案、或刪掉的程式碼 > 500 行還沒進到刪 Jinja 階段，停下來等人工 review。

---

## 10. Reference 圖片的氣質

兩張參考圖的 spirit 對應到 Praetor 的哪一面：

- **Image 1 (Jimmy AI / "Good morning, Jimmy")** → `/office` 的氣質：留白、prompt 為中心、天空感的 onboarding 入口
- **Image 2 (veris dashboard)** → `/missions`, `/memory`, `/runtime`, `/settings` 的氣質：分群側欄、metric cards、表格、status pill、黑色 primary CTA
- **Linear** → 全站的 keyboard-first refinement：⌘K omnibox、tight typography、status pill 配色克制、dark-mode first-class

如果 Codex 在某個視覺決策上猶豫：
- 「這個按鈕該長怎樣？」→ 看 Linear new issue button
- 「這個 table 列要不要 row hover？」→ 看 Linear my-issues page，會
- 「empty state 該怎麼處理？」→ 看 Image 1 的「Start generating your designs」結構

---

End of playbook.
