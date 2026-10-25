# devsweep

Reclaim SSD space from rebuildable dev artifacts (`node_modules`, `.next`, `dist`, `.venv`, `target`, …) on a machine where AI coding agents (Codex, Claude Code) keep spawning worktrees. Never touches the agents' own state. Every run is version controlled.

繁體中文在下方。

## Why

Codex and Claude Code open a fresh git worktree per task and rarely remove it. Each worktree gets its own install and build. On one machine this was 53 worktrees of a single repo, 60 GB of `node_modules` + `.next`, and 1.4 GB free. The agents' session data (`~/.codex`, `~/.claude`) must survive, and `rm -rf` of a worktree can destroy uncommitted work. See openai/codex issues [#34061](https://github.com/openai/codex/issues/34061), [#41806](https://github.com/openai/codex/issues/41806), [#54891](https://github.com/openai/codex/issues/54891).

## Rules

1. **Scan is the default and changes nothing.** It writes a manifest and a report.
2. **`apply` acts only on what `scan` classified as `rebuildable`**, writes the manifest *before* acting, and refuses without `--yes`.
3. **Agent state is never a target.** `~/.codex`, `~/.claude`, the Claude desktop app, plus anything you pass with `--protect`. Reported by size only.
4. **Rebuildable means provable.** `node_modules` needs a lockfile next to it; `.venv` needs a lock or requirements; `target` needs `Cargo.lock`. The rebuild command is recorded per item.
5. **Skips anything in use**: a project with a running process inside it, or files changed within `--idle-hours` (default 48).
6. **Skips pnpm `node_modules` on macOS.** They are APFS clones of the global store. Measured: deleting 962 MB freed 0 bytes.
7. **Measures what it freed with `df`, not `du`.** `du` overcounts clones; the manifest records both.
8. **Everything is in git.** `~/.devsweep` is a repo. Each run commits its manifest; `ledger.jsonl` has one line per item with path, size, branch, dirty count, idle hours, rebuild command, and whether it was acted on.
9. **Worktrees are listed, never removed.** `devsweep worktrees` prints dirty / merged / unpushed state and marks safe candidates. You run `git worktree remove` yourself.

## Usage

```bash
python3 -I devsweep.py scan                      # default root ~/Developer
python3 -I devsweep.py scan --root ~/src --protect ~/src/keep-me

python3 -I devsweep.py apply --yes --kind .next --limit 1 --purge   # try one, read "df measured"
python3 -I devsweep.py apply --yes --kind .next --purge             # then the rest
python3 -I devsweep.py apply --yes --kind node_modules --purge      # npm/yarn only; pnpm is skipped

python3 -I devsweep.py worktrees                 # report only
python3 -I devsweep.py ledger                    # history
```

Without `--purge`, `apply` moves items to `~/.Trash/devsweep-<run>/`. Trash frees nothing until emptied; use it when you want a second look before committing.

### Weekly scan (launchd, macOS)

```bash
launchd/install.sh          # Monday 09:00, scan only, log in ~/.devsweep/logs/
launchd/install.sh remove
```

The job never runs `apply`. Read the log, then decide.

## Measured results (2026-10-25, macOS, 228 GB APFS)

| action | items | du estimate | df measured |
|---|---|---|---|
| delete one pnpm `node_modules` | 1 | 962 MB | ≈ 0 |
| purge `.next` | 24 | 12.5 GB | 12.6 GB |
| purge npm `node_modules` | 39 | 17.6 GB | 17.0 GB |

Free space went from 1.4 GB to 31.4 GB. Nothing under `~/.codex` or `~/.claude` was touched.

## Prevent it next time

- Finish a task, remove its worktree: `git worktree remove <path>` and `git branch -d <branch>`.
- pnpm projects: `package-import-method=hardlink` in `.npmrc` makes `du` honest about shared files.
- Run the weekly scan and read it.

---

## 繁體中文

**做什麼**：只清「可重建」的開發產物（`node_modules`、`.next`、`dist`、`.venv`、`target`），永遠不碰 Codex／Claude Code 自己的環境（`~/.codex`、`~/.claude`、Claude 桌面 app）。每一次執行都寫進 `~/.devsweep`（本身是 git repo），刪了什麼、為什麼、怎麼重建，都有紀錄可回溯。

**九條規則**：預設 `scan` 只量測不改動；`apply` 只處理 `scan` 判定可重建的項目，先寫 manifest 再動手，沒有 `--yes` 一律拒絕；agent 環境只回報大小；可重建要有 lockfile 證據；有程序在跑或 48 小時內有動的專案跳過；pnpm 的 `node_modules` 是 APFS clone，刪了不釋放（實測），跳過；釋放量用 `df` 實測，不信 `du`；全部進 git；worktree 只列不刪。

**用法**見上方指令。`launchd/install.sh` 裝每週一 09:00 的掃描，只掃不刪。

**實測**：三次 apply 共釋放約 29.6G，可用空間 1.4G → 31.4G，`~/.codex`、`~/.claude` 完全未動。

## License

MIT
