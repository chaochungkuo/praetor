# Praetor 文件索引

這個目錄是目前 Praetor 的產品與實作規格中心。

建議閱讀順序：

1. [ROADMAP.md](../ROADMAP.md)
2. [PRAETOR_PRODUCT_BRIEF.zh-TW.md](../PRAETOR_PRODUCT_BRIEF.zh-TW.md)
3. [PRAETOR_SYSTEM_SPEC.zh-TW.md](PRAETOR_SYSTEM_SPEC.zh-TW.md)
4. [PRAETOR_UI_SPEC.zh-TW.md](PRAETOR_UI_SPEC.zh-TW.md)
5. [PRAETOR_SURFACES_SPEC.zh-TW.md](PRAETOR_SURFACES_SPEC.zh-TW.md)
6. [PRAETOR_REPO_ARCHITECTURE.zh-TW.md](PRAETOR_REPO_ARCHITECTURE.zh-TW.md)
7. [PRAETOR_PUBLIC_SECURITY_REVIEW.zh-TW.md](PRAETOR_PUBLIC_SECURITY_REVIEW.zh-TW.md)
8. [PRAETOR_PRIVACY_BOUNDARIES.zh-TW.md](PRAETOR_PRIVACY_BOUNDARIES.zh-TW.md)
9. [DEVELOPER_SETUP.md](DEVELOPER_SETUP.md)
10. [ADVANCED_DEPLOYMENT.md](ADVANCED_DEPLOYMENT.md)
11. [INSTALL_CHECKLIST.md](INSTALL_CHECKLIST.md)
12. [DEPLOYMENT_SECURITY_SPEC.zh-TW.md](DEPLOYMENT_SECURITY_SPEC.zh-TW.md)
13. [PRAETOR_EXECUTOR_BRIDGE_SPEC.zh-TW.md](PRAETOR_EXECUTOR_BRIDGE_SPEC.zh-TW.md)
14. [PRAETOR_OPEN_SOURCE_SUCCESS_SPEC.zh-TW.md](PRAETOR_OPEN_SOURCE_SUCCESS_SPEC.zh-TW.md)
15. [PRAETOR_BRAND_SPEC.zh-TW.md](PRAETOR_BRAND_SPEC.zh-TW.md)
16. [PRAETOR_LOCAL_DEPLOY.md](PRAETOR_LOCAL_DEPLOY.md)
17. [PRAETOR_REMOTE_PRIVATE_DEPLOY.md](PRAETOR_REMOTE_PRIVATE_DEPLOY.md)
18. [PRAETOR_BACKUP_RESTORE.md](PRAETOR_BACKUP_RESTORE.md)

文件角色：

- `ROADMAP.md`
  - 單一執行 roadmap、勾選清單、目前完成度、下一步里程碑

- `PRAETOR_PRODUCT_BRIEF.zh-TW.md`
  - 產品定位、市場、方向、MVP、價值主張

- `PRAETOR_SYSTEM_SPEC.zh-TW.md`
  - 核心概念、schema、治理、記憶、runtime、executor、安全策略

- `PRAETOR_UI_SPEC.zh-TW.md`
  - 資訊架構、頁面、元件、互動、onboarding、checkpoint 與可見性

- `PRAETOR_SURFACES_SPEC.zh-TW.md`
  - Web / Mobile / Telegram 三端邊界、文字 wireframe、interaction flow

- `PRAETOR_REPO_ARCHITECTURE.zh-TW.md`
  - 技術選型、repo 切分、部署形態、背景工作、測試、穩定性、實作順序

- `DEPLOYMENT_SECURITY_SPEC.zh-TW.md`
  - Docker 部署模式、網路邊界、資料持久化、備份還原、secrets、host executor bridge

- `PRAETOR_EXECUTOR_BRIDGE_SPEC.zh-TW.md`
  - `praetor-execd` 的責任邊界、API contract、事件模型、狀態機、path mapping、安全規則、與 Praetor worker 的整合

- `PRAETOR_OPEN_SOURCE_SUCCESS_SPEC.zh-TW.md`
  - 目前 codebase 現況、記憶與使用者流程盤點、開源定位落差、產品化與行銷執行規格

- `PRAETOR_PUBLIC_SECURITY_REVIEW.zh-TW.md`
  - 公開使用前安全稽核、已完成控制、上線前阻擋項

- `PRAETOR_PRIVACY_BOUNDARIES.zh-TW.md`
  - 使用者資料存放、檔案存取、外部 provider 與刪除資料說明

- `DEVELOPER_SETUP.md`
  - Pixi、本機開發、smoke tests、planner、bridge 開發流程

- `ADVANCED_DEPLOYMENT.md`
  - 手動 Docker、production overlay、多服務 stack、host executor bridge

- `INSTALL_CHECKLIST.md`
  - release candidate 前的乾淨安裝與 smoke test checklist

- `PRAETOR_BRAND_SPEC.zh-TW.md`
  - 官方 logo、品牌語氣、色彩方向、產品內的使用原則

- `PRAETOR_LOCAL_DEPLOY.md`
  - 目前可直接使用的本地 Docker 啟動方式與 bridge 連接方式

- `PRAETOR_REMOTE_PRIVATE_DEPLOY.md`
  - 目前可行的私有遠端部署方式、reverse proxy 建議與 runtime 選擇說明

- `PRAETOR_BACKUP_RESTORE.md`
  - 備份與還原方式、狀態目錄說明、最小可行 backup script

目前共識：

- 方向已穩定，但實作細節仍可調整
- 核心是 `role + governance + company memory + bounded autonomy`
- 使用者管理的是 Praetor，不是多個 agent
- MVP 先求可信、可部署、可用，不求功能最大
