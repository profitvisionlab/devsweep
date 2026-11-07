# 技術堆疊

[主規範](../AGENTS.md)

## 用途

技術堆疊：單檔 Python 標準函式庫 CLI＋macOS launchd

## 適用範圍

本 repo 的語言、執行環境、依賴與支援平台。

## 現行堆疊

- **語言**：Python 3，單一檔案 [`devsweep.py`](../devsweep.py)（shebang `#!/usr/bin/env python3`）。
- **依賴**：只用標準函式庫（`argparse`、`json`、`shutil`、`subprocess`、`dataclasses`、`pathlib` 等）；沒有 `requirements.txt`、`pyproject.toml` 或 lockfile。
- **執行方式**：README 一律寫 `python3 -I devsweep.py <scan|apply|worktrees|ledger>`。
- **外部指令**：程式呼叫 `git`、`df`、`du` 等系統指令（README 規則 7、9）。
- **排程**：macOS launchd，[`launchd/install.sh`](../launchd/install.sh) 以 `launchd/com.devsweep.scan.plist` 為範本安裝每週一 09:00 的 scan（只掃不刪）；用到 `launchctl`、`plutil`。
- **狀態目錄**：執行紀錄寫到使用者的 `~/.devsweep`（本身是 git repo），可用 `DEVSWEEP_HOME` 環境變數改變 HOME 位置（程式開頭）。
- **授權**：MIT（[`LICENSE`](../LICENSE)）。

## 依賴原則

目前零第三方依賴。README 的實測與規則都以 macOS／APFS 為前提（例如 pnpm `node_modules` 為 APFS clone）。

## 待 Ben 確認

- 支援的最低 Python 版本（程式用 `from __future__ import annotations`，未宣告版本）。
- 是否正式支援 macOS 以外的平台（Linux 的 clone 與 `df` 行為未記載）。
- 是否維持零第三方依賴作為規則。
