# Praetor 文件索引

Status: 2026-05-12 refreshed。

這個目錄是 Praetor 的產品與實作規格中心。文件依用途分四類，**讀的順序按目的，不是按字母**。

---

## A. 從這裡開始（必讀）

1. [ROADMAP.md](../ROADMAP.md) — 三條 track 的當前狀態、MVP 定義、執行優先序
2. [PRAETOR_PRODUCT_BRIEF.zh-TW.md](../PRAETOR_PRODUCT_BRIEF.zh-TW.md) — 產品北極星，市場定位，五條核心原則

## B. 設計層（UI / 視覺 / 多端策略）

| 文件 | 角色 |
|---|---|
| [UI_REBUILD_PLAYBOOK.zh-TW.md](UI_REBUILD_PLAYBOOK.zh-TW.md) **← Codex 執行用** | 當前 UI 重建工作的 source of truth：5 頁 layout、token、9-commit 計畫 |
| [PRAETOR_UI_SPEC.zh-TW.md](PRAETOR_UI_SPEC.zh-TW.md) | 長期有效的 UI 原則（六條 UX 原則、checkpoint UX、通知分類、多端策略總綱、核心取捨） |
| [PRAETOR_BRAND_SPEC.zh-TW.md](PRAETOR_BRAND_SPEC.zh-TW.md) | 視覺基線：配色 token、字體、logo、語氣、動效原則 |
| [PRAETOR_SURFACES_SPEC.zh-TW.md](PRAETOR_SURFACES_SPEC.zh-TW.md) | Web / Mobile Web / Telegram 三端邊界、權限、interaction flow |

衝突權威順序：`PRODUCT_BRIEF > UI_SPEC > BRAND_SPEC > UI_REBUILD_PLAYBOOK`。

## C. 系統層（後端 / 部署 / 安全）

| 文件 | 角色 |
|---|---|
| [PRAETOR_SYSTEM_SPEC.zh-TW.md](PRAETOR_SYSTEM_SPEC.zh-TW.md) | 核心概念、schema、治理、記憶、runtime、executor、安全策略 |
| [PRAETOR_REPO_ARCHITECTURE.zh-TW.md](PRAETOR_REPO_ARCHITECTURE.zh-TW.md) | 技術選型、repo 切分（含 as-built 對照）、部署形態、背景工作 |
| [PRAETOR_EXECUTOR_BRIDGE_SPEC.zh-TW.md](PRAETOR_EXECUTOR_BRIDGE_SPEC.zh-TW.md) | `praetor-execd` 主機側 bridge 的 API contract、事件模型、狀態機 |
| [DEPLOYMENT_SECURITY_SPEC.zh-TW.md](DEPLOYMENT_SECURITY_SPEC.zh-TW.md) | Docker 部署模式、網路邊界、secrets、備份還原 |
| [PRAETOR_PUBLIC_SECURITY_REVIEW.zh-TW.md](PRAETOR_PUBLIC_SECURITY_REVIEW.zh-TW.md) | 公開使用前的安全稽核、已完成控制、上線阻擋項 |
| [PRAETOR_PRIVACY_BOUNDARIES.zh-TW.md](PRAETOR_PRIVACY_BOUNDARIES.zh-TW.md) | 使用者資料存放、檔案存取、外部 provider 與刪除說明 |

## D. 行為層（產品內的核心流程）

| 文件 | 角色 |
|---|---|
| [PRAETOR_MEMORY_PROMOTION.md](PRAETOR_MEMORY_PROMOTION.md) | 對話 → 決策 → 文件 → 長期 Wiki 記憶的沉澱流程 |
| [PRAETOR_TEAM_PLANNING.md](PRAETOR_TEAM_PLANNING.md) | CEO 組隊、PM 交辦、董事長簡報、授權執行與升級邊界 |
| [PRAETOR_ORGANIZATION_OPERATING_SYSTEM.md](PRAETOR_ORGANIZATION_OPERATING_SYSTEM.md) | mission lifecycle、agent employment contracts、permission profiles、work trace |

## E. 安裝 / 部署 / 對外手冊

| 文件 | 角色 |
|---|---|
| [PRAETOR_LOCAL_DEPLOY.md](PRAETOR_LOCAL_DEPLOY.md) | 本地 Docker 啟動方式 |
| [PRAETOR_REMOTE_PRIVATE_DEPLOY.md](PRAETOR_REMOTE_PRIVATE_DEPLOY.md) | 私有遠端部署、reverse proxy |
| [ADVANCED_DEPLOYMENT.md](ADVANCED_DEPLOYMENT.md) | 手動 Docker、production overlay、多服務 stack |
| [INSTALL_CHECKLIST.md](INSTALL_CHECKLIST.md) | release candidate 前的乾淨安裝 checklist |
| [PRAETOR_BACKUP_RESTORE.md](PRAETOR_BACKUP_RESTORE.md) | 備份還原、最小可行 backup script |
| [DEVELOPER_SETUP.md](DEVELOPER_SETUP.md) | Pixi 本機開發、smoke tests、planner、bridge 開發 |
| [CHATGPT_SUBSCRIPTION_EXECUTOR.md](CHATGPT_SUBSCRIPTION_EXECUTOR.md) | ChatGPT subscription 連接 Praetor 的設定流程 |
| [TELEGRAM_SETUP.md](TELEGRAM_SETUP.md) | Telegram CEO 入口、webhook、配對碼 |
| [GITHUB_SETUP.md](GITHUB_SETUP.md) | GitHub Pages 發布與 CI 相關設定 |

## F. 對外行銷 / 開源定位

- [PRAETOR_OPEN_SOURCE_SUCCESS_SPEC.zh-TW.md](PRAETOR_OPEN_SOURCE_SUCCESS_SPEC.zh-TW.md) — codebase 現況盤點、開源定位落差、產品化與行銷執行

## G. 歷史 / 延期（不在 v1 執行路徑）

- [PRAETOR_WORKSPACE_STEWARD.md](PRAETOR_WORKSPACE_STEWARD.md) — Phase-2 設計，v1 已移除，等待真實使用者痛點再恢復
- [../PRODUCT_INTAKE.md](../PRODUCT_INTAKE.md) — 原始討論材料，未經整理，保留作為來源紀錄

---

## 目前共識（2026-05）

- **產品方向已穩定**：core 是 `role + governance + company memory + bounded autonomy`
- **使用者管理的是 Praetor（CEO 層），不是多個 agent**
- **MVP 先求可信、可部署、可用，不求功能最大**
- **執行優先序**：foundation cleanup（已完成）→ UI 重建（規劃中，Codex 執行）→ Docker app stack 收尾 → Telegram commands
- **被 deferred 的**：workspace steward layer、skill marketplace、進階 role tuning
