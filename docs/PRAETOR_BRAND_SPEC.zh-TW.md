# Praetor 品牌與視覺基線 v0.2

Status: 2026-05 重寫，與 [UI_REBUILD_PLAYBOOK](UI_REBUILD_PLAYBOOK.zh-TW.md) 視覺 token 對齊。

這份文件定義 Praetor 的品牌語氣與視覺基線。比 `UI_REBUILD_PLAYBOOK` 抽象一層——
playbook 講「按鈕的 padding 與 hover」，這份講「為什麼按鈕該長那樣」。

> 與 v0.1 的差異：v0.1 主張 dark + 銀白 + 金色 executive only。實際做 UI 時，
> Image 1 / Image 2 / Linear 三個參考都指向 light surface + cool blue accent +
> 黑色 primary CTA + dark mode sibling。本版以此為新基線。Logo 視覺方向不變。

---

## 1. 品牌定位（不變）

Praetor 的品牌是：

- executive system
- AI company command center
- structured authority

不是：

- playful AI tool
- workflow builder
- developer toy
- chat app

## 2. 品牌語氣

Praetor 的所有 surfaces——README、onboarding、UI label、commit message、錯誤訊息、
邀請信、Telegram 通知——都應保持：

- **冷靜**：不喊、不誇張
- **果斷**：講事實與決策，不講感受
- **有秩序**：先摘要再展開，先決策再說明
- **有自信**：不解釋自己為什麼存在，不抱歉
- **不吵鬧**：不用 emoji、不用驚嘆號、不用「！🎉」

不應走的方向：

- 可愛
- 過度科技霓虹（neon / glow / 漸層粒子）
- chat app 風（氣泡密集對話流）
- 卡通 agent 頭像
- generic SaaS 模板感（「Trusted by 10,000+ teams」）

## 3. 視覺基線

### 3.1 雙模式（Light + Dark，均為 first-class）

| 模式 | 何時為主要呈現 |
|---|---|
| **Light** | 預設工作面、登入頁、onboarding、外部 marketing |
| **Dark** | 使用者主動切換（會被 persist）、晚間工作、Linear 風 power user |

兩個模式都要做到 brand-faithful。**不存在「只支援深色」或「只支援淺色」的頁面**。

### 3.2 配色（與 playbook §1.1 token 同源）

#### Light（預設）

- **Background**：`#F7F7F8`（off-white，極淺中性灰）
- **Surface / card**：`#FFFFFF` + 1px hairline border + 微陰影
- **Ink（文字主）**：`#0A0A0A`
- **Muted（次要文字）**：`#5C5F66`
- **Accent**：`#3B5BFD`（深藍，接近 Linear indigo，**only** 用於連結、focus ring、進度條、`/office` 的 Send to CEO 漸層按鈕）
- **Primary CTA**：`#0A0A0A`（純黑），文字白
- **Status**：green / amber / red / gray / indigo 軟色 pill（見 playbook §1.1）

#### Dark

- **Background**：`#0B0C0E`
- **Surface / card**：`#131418`
- **Ink**：`#F5F6F8`
- **Accent**：`#6B85FF`（同一藍系，亮度提升）
- **Primary CTA**：accent 色而非純白（純白在深色背景太刺眼）

### 3.3 金色已不再是品牌色

v0.1 把 `#C9A25D` 列為輔助色。實作時發現：

- 金色與 AI 產品的「賭場 / 詐騙感」距離太近
- 與 light mode 的中性色架構衝突
- Linear / Vercel / 任何高密度 command center 都不用金色

金色從品牌色降級為**保留色**：只允許出現在 logo 內部裝飾（如果未來有需要），UI 中不再使用。

### 3.4 漸層的唯一允許出現

漸層在 working surfaces 全面禁用，**唯二例外**：

1. `/office` 的「Send to CEO」按鈕：linear-gradient(135deg, #3B5BFD 0%, #6B85FF 100%)
2. `/app/login`、`/app/welcome`、`/app/praetor` (onboarding) 的全頁背景：天空感漸層 linear-gradient(180deg, #B6D4FA 0%, #E8F1FE 50%, #FFFFFF 100%)

其餘任何 hover state、card border、icon、頂條都**不允許**任何形式的漸層。

## 4. Typography

- **主字**：Inter（拉丁字）+ Noto Sans TC（中文）—— 與 playbook §1.2 一致
- **權威感**來自於：
  - 行距克制（不要 line-height 1.7 的雜誌風）
  - 字重克制（標題 600 不用 700）
  - letter-spacing 微負（-0.01em on headings）

**不要做**：

- 用 serif 字體做 body（serif 只允許用在 logo 的 wordmark）
- 用 monospace 字體做 UI 標題（monospace 留給 ID / JSON / code）
- 用 italic 強調（用顏色或字重強調）

## 5. Logo

### 5.1 主使用情境

| 場景 | 用什麼 |
|---|---|
| README header | 完整 logo（dark 版本） |
| Landing page hero | 完整 logo（dark 版本） |
| Login / onboarding 卡片 | monogram + wordmark（中央） |
| App sidebar 展開 | wordmark only（左對齊） |
| App sidebar collapsed | monogram only（置中） |
| Favicon / Telegram avatar | monogram only |

### 5.2 Logo 不允許的用法

- 改成高飽和亮色（霓虹紫、橘、粉）
- 加 3D 效果、發光、glow
- 改成圓角 playful 風
- 與其他 icon 合成新 mark
- 在淺色背景上不調整 contrast 直接硬貼

### 5.3 資產

目前 repo 內：

- [`branding/praetor-logo-dark.png`](../branding/praetor-logo-dark.png)
- [`branding/praetor-mark-dark.png`](../branding/praetor-mark-dark.png)

未來要做：

- light 版本的 logo 與 mark（white-on-dark 的 invert）
- SVG 版本（給 favicon 與 retina）
- 1024×1024 mobile app icon（給未來的 PWA / Telegram）

## 6. 動效與觸感

- transition duration 預設 150ms，使用 `cubic-bezier(0.2, 0, 0.1, 1)`
- 任何 element 一次只動一個屬性（opacity OR transform OR color，不要同時三個）
- **禁止**：bounce、wobble、spring overshoot、scale > 1.05、glow pulse
- 可以：opacity fade、subtle translate（≤4px）、bg-hover

Praetor 的觸感是「冷靜的、可預測的、不喧賓奪主」。動效是回饋而非表演。

## 7. 語言

- UI shell（按鈕、選單、tab 名稱）：zh-TW 與 en 都備齊，使用者語言切換立即生效
- 內容（mission title、wiki body、決策文字）：保留原文，不自動翻譯
- 預設語言依使用者 onboarding 時選擇
- 不允許混語：UI 不會出現「設定 Settings 已儲存」這種 zh-en 拼裝

## 8. 與產品定位的對齊

`PRAETOR_PRODUCT_BRIEF` 第 8 節列了五條核心產品原則。每條對應到視覺：

| 產品原則 | 視覺對應 |
|---|---|
| Files Are the Source of Truth | UI 強調連結到檔案，不另造資料殼。記憶頁的 retrieval preview 是 trust 設計 |
| User Manages Roles, Not Agents | 不顯示 agent 個體 ID 給使用者；組織圖用角色名而非實例名 |
| Governance Is the Product | 批准 / 升級 / 預算 永遠視覺優先（右側 rail、status pill 醒目色） |
| Memory Belongs to the Company | 公司記憶用 wiki/markdown，不是聊天記錄。Memory 頁是讀文件，不是讀對話 |
| Product Should Feel Complete on Day One | 不允許「coming soon」label 在 v1 surfaces；empty state 必須有具體下一步 |

## 9. 自此開始的決定

- light + dark 雙 first-class，dark 不再是唯一面貌
- accent 從金色改為 cool indigo blue
- 漸層僅限 onboarding 背景與 CEO 送出按鈕
- 字型 Inter + Noto Sans TC 為唯一字體系列
- logo 視覺方向不變

未來變更這份文件時，須同步更新 [UI_REBUILD_PLAYBOOK](UI_REBUILD_PLAYBOOK.zh-TW.md) §1。
