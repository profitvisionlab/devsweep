# 專案主規範

專案主規範與細部規範索引。devsweep 清除可重建的開發產物（`node_modules`、`.next`、`dist`、`.venv`、`target` 等），永遠不碰 AI coding agent 自己的環境；用途與規則見 [README.md](README.md)。

## 主從規範

本文件為唯一主規範，細則補充本文件，衝突時以主規範為準，並遵守使用者指示與執行環境上層指令。依任務讀取相關細則，不假設連結會自動載入。

## 細部規範

| 規範 | 用途 |
| --- | --- |
| [tech-stack.md](.agent-rules/tech-stack.md) | 技術堆疊：單檔 Python 標準函式庫 CLI＋macOS launchd |
| [project-structure.md](.agent-rules/project-structure.md) | 專案目錄結構與文件歸屬 |
| [tracking.md](.agent-rules/tracking.md) | 工作追蹤：git 歷史與 PR，執行紀錄在使用者的 ~/.devsweep |
| [verification.md](.agent-rules/verification.md) | 驗證：沒有自動測試，scan 為唯讀；文件檢查 |

`docs/` 各分類的用途見 [project-structure.md](.agent-rules/project-structure.md)。

## 共通原則

先釐清重要假設，以最少必要變更完成需求，避免修改無關內容，並如實回報驗證結果與限制。規範模板不代表已授權 Git、安裝或其他外部操作。
