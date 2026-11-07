# 專案目錄結構

[主規範](../AGENTS.md)

## 用途

專案目錄結構與文件歸屬

## 適用範圍

本 repo 的頂層檔案與 `docs/` 分類。新增檔案前先對照本檔；新增頂層目錄或分類時同步更新本檔。

## 頂層

```text
./
├── AGENTS.md             # 主規範與細部規範索引
├── README.md             # 用途、九條規則、用法、實測結果（英文＋繁中）
├── LICENSE               # MIT
├── devsweep.py           # 主程式（scan／apply／worktrees／ledger）
├── launchd/
│   ├── com.devsweep.scan.plist  # 每週 scan 的 launchd 範本
│   └── install.sh        # 安裝／移除排程
├── .agent-rules/         # 細部規範（本檔所在）
├── .claude/ .agents/     # Claude Code／Codex 的 skill（project-scaffold）
└── docs/                 # 專案文件（分類見下，目前皆為空）
```

執行產生的 manifest、報告與 `ledger.jsonl` 寫在使用者的 `~/.devsweep`，不在本 repo。

## docs/ 分類

| 目錄 | 放什麼 |
| --- | --- |
| `docs/requirements/` | 需求文件 |
| `docs/research/` | 研究資料（例如各平台磁碟量測） |
| `docs/architecture/` | 架構與決策紀錄 |
| `docs/tracking/devlog/` | 開發過程與驗證紀錄 |
| `docs/tracking/handoff/` | 目前狀態與接續事項 |
| `docs/guides/` | 操作與使用指南 |

目錄以 `.gitkeep` 佔位；放入實際文件後可刪除。

## 待 Ben 確認

- 本 repo 是否需要完整的 `docs/` 分類，或只保留部分（目前所有說明都在 README）。
- 若加入測試，測試目錄的位置（例如 `tests/`）。
