# Praetor 品牌與 Logo 規格 v0.1

狀態：設計稿

這份文件將目前的 Praetor 品牌視覺定為正式基線。

## 1. 官方 Logo

Praetor 的官方 logo 目前採用：

- 使用者提供的 `Praetor` 黑底品牌圖
- 中央為幾何化 `P` monogram
- 下方為 `PRAETOR` serif wordmark
- 底部 slogan：
  - `RUN YOUR COMPANY WITH AN AI CEO`

這張圖目前應視為：

- 官方主 logo
- 品牌 mood direction
- 首頁 / README / landing page 的優先視覺參考

## 2. 視覺特徵

這版 logo 傳達的核心感受是：

- authority
- calm
- precision
- hierarchy
- premium but restrained

它和 Praetor 的產品定位一致：

- 不是 playful AI tool
- 不是 workflow builder
- 不是 developer toy

而是：

- executive system
- AI company command center
- structured authority

## 3. 正式品牌語言

Praetor 的品牌語氣應該保持：

- 冷靜
- 果斷
- 有秩序
- 不吵鬧
- 不 gimmicky

不應走的方向：

- 可愛
- 過度科技霓虹
- chat app 風
- 卡通 agent 風

## 4. 色彩方向

根據目前 logo，品牌主色方向應暫定為：

- 背景：黑 / 近黑
- 主文字 / monogram：銀白 / 石灰白
- 輔助強調：低飽和金色

建議語意色：

- `brand-bg`
  - `#050505` 附近
- `brand-ink`
  - `#E8E2DA` 附近
- `brand-accent`
  - `#C9A25D` 附近

這裡先作為視覺方向，不代表最終 token 已定稿。

## 5. Logo 使用原則

### 5.1 主使用場景

優先使用完整 logo 的地方：

- README header
- landing page hero
- onboarding welcome screen
- login / splash screen
- brand deck

### 5.2 Monogram 使用場景

只使用 `P` monogram 的地方：

- app favicon
- mobile app icon
- sidebar collapsed logo
- Telegram avatar
- browser tab icon

### 5.3 不建議的用法

- 改成高飽和亮色
- 隨意加 3D 效果
- 改成圓角 playful 風
- 和其他 icon 混成一個標記
- 在淺色背景上不做對比調整直接硬貼

## 6. 產品 UI 的品牌要求

Praetor 的 UI 應和這個 logo 對齊：

- typography 要有 authority，不要 generic startup sans-only
- 背景應允許深色 executive mode
- 資訊密度高，但不應髒亂
- 重點不是花俏，而是 command center 氣質

如果未來做 light mode：

- 也要保留同樣的秩序感與高級感
- 不要變成普通 SaaS 模板

## 7. 資產管理原則

目前這張 logo 是設計來源。

接下來建議正式整理出三種 repo 資產：

1. [branding/praetor-logo-dark.png](branding/praetor-logo-dark.png)
2. [branding/praetor-mark-dark.png](branding/praetor-mark-dark.png)

如果未來要做網站與 favicon，應從這個版本導出，而不是重新畫一個不同的 mark。

## 8. 目前決定

自此開始，Praetor 的官方 logo 與品牌方向以這張圖為準。

也就是：

- `P` monogram 為正式品牌核心標記
- `PRAETOR` serif wordmark 為正式字標方向
- 黑 / 銀白 / 金色為正式視覺基調

## 9. 下一步

最合理的後續工作是：

1. 將這張 logo 匯出為 repo 內正式資產
2. 依這個品牌方向做 README header
3. 依這個品牌方向做 app shell / landing page

目前已完成：

- README header 已接上正式 PNG logo
- mark PNG 已建立，並用於 app favicon / app icon
