# Praetor 公開使用前安全稽核

日期：2026-04-25

狀態：可進入 owner-controlled beta；尚未建議作為多租戶或完全公開 SaaS。

## 結論

Praetor 目前的預設方向是 local-first、單一 owner、自行控制主機。這個邊界下，現況已具備公開給早期使用者自行安裝測試的基礎安全條件。

不建議現在直接把同一個 instance 開成多人共用平台。原因是目前權限模型、資料分區、審計與管理者功能都仍以單一 owner 為中心。

## 已具備的安全控制

- Owner login 預設啟用。
- 初次 onboarding 可用 `PRAETOR_SETUP_TOKEN` 保護。
- Production mode 會拒絕弱 `PRAETOR_SESSION_SECRET`、`PRAETOR_SETUP_TOKEN`、`PRAETOR_BRIDGE_TOKEN`。
- Session cookie 支援 production `secure` mode。
- Authenticated API write request 需要 CSRF token。
- Login rate limit 在 production 預設啟用。
- State 檔案、auth 檔案、audit log、SQLite index 以 `0600` 寫入。
- Praetor 產生的 workspace 檔案以 `0600` 寫入，workspace 目錄以 `0700` 建立。
- Mission/task/run/meeting ID 會拒絕路徑型 ID。
- API mode 寫檔受 workspace write allowlist / denylist 限制。
- Host executor bridge 使用 bearer token，且用 constant-time compare 驗證。
- Executor bridge 只接受設定檔裡允許的 executor。
- Executor bridge 會檢查 target workdir 是否落在 allowed roots 且不在 denied roots。
- Docker image 以非 root 使用者執行。
- Docker compose 已設定 `no-new-privileges`、drop Linux capabilities、API/worker 不直接公開。
- Production compose 使用 Docker secrets `_FILE` 注入敏感值。
- GitHub secret scanning、push protection、CodeQL、OpenSSF Scorecard、branch protection 已啟用。

## 本次稽核修正

- `compose.app.production.yaml` 明確設定 `PRAETOR_ENV=production`，確保 production secret validation 一定生效。
- monolithic `compose.app.yaml` 加上 `no-new-privileges`、`cap_drop: ALL`、`tmpfs: /tmp`。
- workspace bootstrap 目錄改為 `0700`，初始 wiki 檔案改為 `0600`。
- mission、task、run、meeting 相關輸出改為 `0600`。
- mission/task/run/meeting ID 增加格式驗證，避免 `../` 類型 id 被用來探測路徑。
- subscription executor 專案 workdir slug 改為安全字元集合，避免 mission title 影響路徑結構。
- `app-security-smoke` 補 production 弱 secret 拒絕測試與 unsafe mission id 測試。

## 上線前阻擋項

以下項目完成前，不建議宣稱為完全公開穩定版：

- 增加正式 backup/restore 演練記錄。
- 增加 release candidate 安裝測試紀錄。
- 補 2FA 或 passkey 設計，至少在 remote public 模式前完成。
- 補完整 audit event retention 與敏感欄位遮罩策略。
- 補安全回報流程測試：確認 `SECURITY.md` 內的回報管道可用。
- 補 dependency vulnerability 掃描或定期安全檢查。
- 明確標示 subscription executor mode 只支援 owner-controlled host，不支援公網多人共用。

## 建議公開說法

可以說：

- Praetor 是 local-first、owner-controlled 的 AI operating system。
- 預設不公開到網路，只綁 localhost。
- 使用者資料儲存在本機 workspace/data。
- 使用 API provider 時，任務內容會依使用者設定送到該 provider。
- 使用 subscription executor mode 時，Codex / Claude Code 在使用者自己的 host 上執行。

不要說：

- 不會讀任何檔案。
- 絕對不會把資料送出本機。
- 已適合多人共用或完全公開 SaaS。
- executor bridge 可以安全暴露到公網。

