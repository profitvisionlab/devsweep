# 工作追蹤

[主規範](../AGENTS.md)

## 用途

工作追蹤：git 歷史與 PR，執行紀錄在使用者的 ~/.devsweep

## 適用範圍

本 repo 的變更紀錄、待辦與交接；不含工具在使用者機器上產生的執行紀錄。

## 現況

- **變更紀錄**：git 歷史目前只有一個 commit（初版）。沒有 CHANGELOG、issue 或 devlog。
- **執行紀錄**：屬於工具本身的功能，不在本 repo——每次執行都在 `~/.devsweep` commit manifest，`ledger.jsonl` 每項一行（README 規則 8）。
- `docs/tracking/devlog/`、`docs/tracking/handoff/` 骨架已建，尚未使用。

## 作法

- 變更走分支與 PR，PR 說明寫明改了什麼與驗證方式。
- 改變行為的變更（例如判定可重建的條件、保護清單）同步更新 README 的規則與用法。

## 待 Ben 確認

- 是否用 GitHub issue 追蹤待辦與交接。
- 是否需要 CHANGELOG 或版本號（目前沒有發佈版本）。
- 新的實測結果（README「Measured results」）是否改記在 `docs/tracking/devlog/`。
