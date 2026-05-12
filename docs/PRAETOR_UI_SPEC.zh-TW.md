# Praetor UI 原則 v0.2

Status: 2026-05 重寫，從 v0.1 的 841 行頁面規格瘦身為「原則文件」。

這份文件定義 Praetor UI 的**長期有效原則**——不會因為某一輪 UI 重建而過時。
具體的頁面 layout、配色 token、互動細節、commit 計畫，請看：

- **執行層**：[UI_REBUILD_PLAYBOOK.zh-TW.md](UI_REBUILD_PLAYBOOK.zh-TW.md)
- **視覺基線**：[PRAETOR_BRAND_SPEC.zh-TW.md](PRAETOR_BRAND_SPEC.zh-TW.md)
- **多端策略**：[PRAETOR_SURFACES_SPEC.zh-TW.md](PRAETOR_SURFACES_SPEC.zh-TW.md)

> 與 v0.1 的差異：v0.1 鉅細靡遺寫了 12 頁的 Jinja UI（Praetor / Overview / Tasks /
> Meetings / Memory / Models / Settings 等），含 ASCII layout、欄位清單、按鈕命名。
> 第一次 React 重建後，那些頁面被收斂為 5 條 SPA route，per-page layout 全部移到
> `UI_REBUILD_PLAYBOOK`。本版只保留**不會隨重建而失效的原則**。

---

## 1. UX 北極星

Praetor 的 UI 不是 agent playground，不是 workflow builder，不是 chat app。它是
**董事長控制台 / AI CEO 指揮台 / 公司決策與執行總覽**。

使用者用完應同時得到三種感受：

1. **我知道公司在發生什麼。**
2. **我不用自己盯每個細節。**
3. **關鍵時刻我有最終決策權。**

如果某次設計決策讓任一條變弱，就是錯的方向。

## 2. 六條 UX 原則

### 2.1 CEO 是預設互動路徑

預設互動是：

```
User → Praetor → internal roles
```

不是：

```
User → worker agents directly
```

不允許讓使用者直接和 Developer / Reviewer / PM 對話。若未來放開，必須是
`Talk to X via Praetor`，且使用者要知道自己在對誰說話。

### 2.2 先摘要，再展開

所有頁面進入時先給：

- summary
- decisions needed
- risk
- next step

之後才允許使用者下鑽到原始資料（payload、run ID、時間戳）。

### 2.3 決策不能藏

需要使用者批准的事情必須**顯眼、可追溯、能快速處理**。

實作上：

- 永遠有右側 rail 或頂條 badge 顯示待批准數
- 從任何頁面 ⌘K 一鍵跳到「待你決策」
- 不允許把 approval UI 藏在 settings tab 裡

### 2.4 透明，但不噪音

使用者隨時能查到：

- 誰在做（角色）
- 做到哪（status / progress）
- 用了什麼 model / executor
- 產出什麼檔案 / 決策

但首頁不該是 log wall。raw payload、run ID、token 計數**只在主動下鑽時出現**。

### 2.5 把 CEO 放在每件事裡，但不把每件事丟給使用者

Praetor 是 system-wide involved，但 UI 只應呈現：

- Praetor 認為使用者需要知道的內容
- 使用者主動要求下鑽的內容

不要為了「透明」而把每個 audit 行硬塞進主頁。

### 2.6 信任是可見的

Safety、privacy、approvals、runtime health、audit context 必須出現在它們**影響到的工作旁邊**，不是埋在獨立的 Settings 頁。

實作上：

- mission 詳情頁要看得到「這個 mission 受哪些 standing order 限制」
- CEO chat 旁邊要看得到 runtime 健康狀態
- 任何寫檔動作要看得到 workspace scope 邊界

## 3. 使用者角色

MVP 預設只有一個主要人類角色：**Owner / Founder / Chairman**。

這個角色關心：

- 公司進度
- 任務狀態
- 需要批准的事項
- 風險
- 成本 / token / runtime 狀態

不關心（除非主動下鑽）：

- prompt 內容
- 個別 agent personality
- skill 內部 wiring
- agent 的「對話歷史」

## 4. 資訊架構原則

UI 的頁面數應該**少而清楚**，每一頁有單一身份。

判斷一頁是否該獨立的問題：

1. **這頁有獨立的「進入狀態」嗎？**（使用者打開瀏覽器、直接連到這頁，期待什麼？）
2. **這頁失去後使用者會少做什麼？**（如果答案是「沒有」，這頁不該存在。）
3. **這頁和另一頁的決策樹有 70% 重疊嗎？**（有的話，合併。）

實際的 v1 IA 是 5 條 route，見 [UI_REBUILD_PLAYBOOK §2](UI_REBUILD_PLAYBOOK.zh-TW.md#2-information-architecture)。下一次大改時，先回來檢視這三題。

## 5. Checkpoint 與 Paused State

這是 Praetor 與一般 AI 工具最大的 UX 差異點。

當 mission 暫停時，UI **必須**顯示：

- pause reason（人類可讀，不是 enum 縮寫）
- 已完成的部分
- 接下來可能的下一步
- 目前累積的 cost / token
- 等待的決策

UI **必須**提供至少這幾個動作：

- `Continue`
- `Continue with larger budget`
- `Stop`
- `Ask Praetor`
- `Change policy for this mission`

**文案不能像錯誤訊息**。應讓使用者感覺：暫停是設計的一部分，是節奏，不是故障。

## 6. 通知分類

通知必須分三類，並有不同視覺優先級：

| 類別 | 例子 | 視覺 |
|---|---|---|
| **Informational** | mission completed / wiki updated / inbox processed | 中性色、不主動跳 |
| **Actionable** | approval needed / paused due to budget / reviewer blocked | accent 色、右側 rail 上方、頂條 badge |
| **Critical** | executor unhealthy / workspace path unavailable / mission failed after retries | warning 色、頂條 banner、不可關閉直到處理 |

不要把三類都做成 toast。toast 只給 informational。actionable 必須 persistent，critical 必須 blocking。

## 7. Empty / Loading / Error / Degraded States

完成度高低取決於這四種狀態做得多好。

### 7.1 Empty State

不能只有「No data」。必須有：

- 友善 headline（「準備好開始第一個任務嗎？」）
- 具體下一步 action（`[建立任務]` 按鈕）

### 7.2 Loading State

**不要只是 spinner**。應顯示：

- Praetor 正在做什麼（「正在請 CEO 規劃...」）
- 進度估計（若可知）

實作上用 **skeleton block** 比 spinner 好——它告訴使用者「下一秒會出現的東西長這樣」。

### 7.3 Error State

必須說清楚：

- 問題在哪
- 建議怎麼處理
- **不要打斷其它正在進行的 mission**

### 7.4 Degraded State

例如 primary model unavailable、fallback model active、executor login expired。

必須在 **top bar 與 `/runtime` 頁都明確呈現**。不能只在 `/runtime` 出現否則使用者不會看到。

## 8. 視覺與語氣

完整視覺基線見 [PRAETOR_BRAND_SPEC.zh-TW.md](PRAETOR_BRAND_SPEC.zh-TW.md)。原則摘要：

**語氣**：冷靜 / 果斷 / 結構化 / 不討好 / 不拖泥帶水。

**視覺**：權威感 / 清晰層級 / 高可掃描性 / 少量但有意義的強提示色。

**不允許**：

- 可愛 agent 遊戲感
- chat app 風（氣泡密集對話流）
- enterprise ERP 風（表格密度過高、無對比、無 hierarchy）
- 過度科技霓虹 / glow / 漸層粒子

## 9. 多端策略

詳見 [PRAETOR_SURFACES_SPEC.zh-TW.md](PRAETOR_SURFACES_SPEC.zh-TW.md)。摘要：

- **Web**：完整 control plane，所有功能都在這
- **Mobile Web**：輕量 executive dashboard，做 briefing / 批准 / 簡短互動
- **Telegram**：通知 + 簡短指令通道，不做高風險操作

不做三套平行產品。三端共享同一個 mission / decision / memory 真相來源（後端 JSON API）。

## 10. 核心取捨（已決議）

### 10.1 不讓使用者直接管理 agent

**Pro**：保持 executive UX、降低認知負擔、符合產品哲學
**Con**：power users 會想要更深控制

**決議**：預設不暴露 agent 個體。未來可加 expert mode（在 `/runtime` 的 Executors tab 內）。

### 10.2 `/runtime` 獨立成頁

**Pro**：成本與健康度是核心信任訊息，獨立呈現比埋在 settings 強
**Con**：導覽多一頁

**決議**：值得獨立。這不是設定頁，是運營透明度頁。

### 10.3 Meetings 不獨立成頁

v0.1 主張 Meetings 獨立。v0.2 改為：meetings 是 `/missions/:id` 詳情頁的一個 tab（或一個 modal），不獨立。原因：

- meetings 是 mission 內部事件，不是平行於 mission 的物件
- 獨立頁會讓 IA 從 5 條變 6 條，違反「少而清楚」原則
- chairman 不會想「我要看會議」，會想「Mission A 上次 review 結論」

### 10.4 `/memory` 合併 Wiki + Decisions + Open Questions

v0.1 主張 Decisions、Memory、Inbox 分頁。v0.2 改為合併到 `/memory`，左側 tree 用群組區分。原因：

- 三者都是「公司不會忘記的事」，心智上同一個 surface
- 合併後使用者要找「上次決議」與「下次提醒」是同一個動作

## 11. 何時回來改這份文件

下列任一發生，就回來更新本文件而不是只改 playbook：

- 新增第二個人類角色（例如「Team Member」非 owner）
- 預設互動模型從「使用者 → Praetor」改成其它
- 通知三分類失效（出現第四類）
- Checkpoint 暫停 UX 的必要欄位變更
- 多端策略改變（例如 Telegram 開放高風險操作）

不需要回來更新本文件的情況：

- 換配色 token（改 BRAND_SPEC）
- 換頁面 layout（改 PLAYBOOK）
- 換按鈕命名（不需要改任何 spec）
- 加 / 刪一個 mission detail tab（改 PLAYBOOK）

---

## 文件邊界備忘錄

| 想找什麼 | 看哪 |
|---|---|
| 為什麼這個 UI 該長這樣（價值判斷） | 本文件 |
| 視覺 token、字體、配色、動效 | PRAETOR_BRAND_SPEC |
| 頁面 layout、元件 API、commit 計畫 | UI_REBUILD_PLAYBOOK |
| Web / Mobile / Telegram 邊界 | PRAETOR_SURFACES_SPEC |
| 後端 API、資料模型 | PRAETOR_SYSTEM_SPEC |
| 安全 / 部署 | DEPLOYMENT_SECURITY_SPEC |

衝突時的權威順序：**PRODUCT_BRIEF > 本文件 > BRAND_SPEC > PLAYBOOK**。
PLAYBOOK 的細節若與本文件衝突，本文件勝。
