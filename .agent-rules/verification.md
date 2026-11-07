# 驗證規範

[主規範](../AGENTS.md)

## 用途

驗證：沒有自動測試，scan 為唯讀；文件檢查

## 適用範圍

本 repo 所有變更。

## 現況

沒有測試檔、lint 設定或 CI（沒有 `.github/workflows/`），目前沒有自動檢查。

## 可做的檢查

- `python3 -I devsweep.py scan`：預設只量測並寫 manifest，不改動專案（README 規則 1）；但仍會寫入 `~/.devsweep`。
- `python3 -I devsweep.py worktrees`：只輸出報告。
- `apply` 會移動或刪除檔案，不得作為驗證手段，且沒有 `--yes` 會拒絕（README 規則 2）。
- `launchd/install.sh` 會改動使用者的 LaunchAgents，驗證時不執行。

## 文件變更

改 `AGENTS.md`、`.agent-rules/`、`README.md` 或 `docs/` 時：

- 確認新增或修改的相對連結都指向存在的檔案。
- 檔案用途或位置改了，同步更新：`AGENTS.md` 索引、[project-structure.md](project-structure.md) 樹狀圖、`README.md`。
- README 有英文與繁中兩段，規則或用法改了兩段都要改。
- 只寫 repo 裡查得到的事實；未定案的放「待 Ben 確認」。

## 回報

PR 說明寫明做了哪些檢查與結果；沒做的寫原因（例如「只改文件，沒有測試可跑」「apply 會刪檔，未執行」）。

## 待 Ben 確認

- 是否加入自動測試（例如以 `DEVSWEEP_HOME` 指向暫存目錄跑 scan）與 CI。
- 驗證 `apply` 行為的安全作法（暫存目錄、假專案）。
