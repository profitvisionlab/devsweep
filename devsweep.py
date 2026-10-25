#!/usr/bin/env python3
"""devsweep — reclaim disk from rebuildable dev artifacts, never from agent state.

Default mode `scan` only measures and writes a manifest. Nothing is changed.
`apply` acts only on items `scan` classified as rebuildable, writes the manifest
first, then moves them to ~/.Trash (or deletes with --purge). Every run is a
commit in ~/.devsweep, which is its own git repo, so the history of what was
removed, why, and how to rebuild it is version controlled.

Hard rules:
  * AI coding agent state (~/.codex, ~/.claude, the Claude desktop app) is never
    a target. It is reported by size only.
  * node_modules is rebuildable only when a lockfile sits next to it.
  * pnpm node_modules on macOS are APFS clones of the global store. Deleting
    them frees ~0 bytes (measured), so they are skipped.
  * A project with a running process inside it, or with file changes within
    --idle-hours, is skipped.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import shutil
import subprocess
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path

HOME = Path(os.environ.get("DEVSWEEP_HOME", str(Path.home())))
STATE = HOME / ".devsweep"
LEDGER = STATE / "ledger.jsonl"

# Never a target. Reported by size only. Extend with --protect.
PROTECTED = [
    HOME / ".codex",
    HOME / ".claude",
    HOME / "Library" / "Application Support" / "Claude",
    HOME / "Library" / "Application Support" / "Code",
]

# basename -> evidence files (any one) that must exist at the project root for the
# artifact to count as rebuildable. Empty tuple: always rebuildable from source.
ARTIFACTS: dict[str, tuple[str, ...]] = {
    "node_modules": ("pnpm-lock.yaml", "package-lock.json", "yarn.lock", "bun.lock", "bun.lockb"),
    ".next": (),
    ".turbo": (),
    ".nuxt": (),
    ".svelte-kit": (),
    ".parcel-cache": (),
    "__pycache__": (),
    ".pytest_cache": (),
    ".mypy_cache": (),
    ".ruff_cache": (),
    ".venv": ("uv.lock", "poetry.lock", "requirements.txt", "pyproject.toml"),
    "target": ("Cargo.lock",),
    "dist": ("package.json",),
}

REBUILD = {
    "pnpm-lock.yaml": "pnpm install --frozen-lockfile",
    "package-lock.json": "npm ci",
    "yarn.lock": "yarn install --frozen-lockfile",
    "bun.lock": "bun install --frozen-lockfile",
    "bun.lockb": "bun install --frozen-lockfile",
    "uv.lock": "uv sync",
    "poetry.lock": "poetry install",
    "requirements.txt": "python3 -m venv .venv && .venv/bin/pip install -r requirements.txt",
    "pyproject.toml": "python3 -m venv .venv && .venv/bin/pip install -e .",
    "Cargo.lock": "cargo build",
    "package.json": "npm run build",
}

# Do not descend into these. Artifacts among them are collected as candidates.
PRUNE = set(ARTIFACTS) | {".git", "Library", ".Trash", ".devsweep"}


@dataclass
class Candidate:
    path: str
    kind: str
    size_bytes: int
    project_root: str
    evidence: str | None
    rebuild_cmd: str | None
    branch: str | None
    dirty_files: int | None
    last_commit: str | None
    idle_hours: float | None
    decision: str  # rebuildable | skip-* (see classify)
    reason: str


@dataclass
class Run:
    run_id: str
    started: str
    mode: str
    roots: list[str]
    idle_hours_threshold: float
    protected_sizes: dict[str, int] = field(default_factory=dict)
    candidates: list[Candidate] = field(default_factory=list)
    acted: list[str] = field(default_factory=list)
    freed_bytes: int = 0  # sum of du; APFS clones make this an overestimate
    freed_bytes_actual: int | None = None  # df delta, the number that counts
    method: str | None = None


def human(n: float) -> str:
    for unit in ("B", "K", "M", "G", "T"):
        if n < 1024:
            return f"{n:.0f}{unit}" if unit == "B" else f"{n:.1f}{unit}"
        n /= 1024
    return f"{n:.1f}P"


def du(path: Path) -> int:
    out = subprocess.run(["du", "-sk", str(path)], capture_output=True, text=True)
    try:
        return int(out.stdout.split()[0]) * 1024
    except (IndexError, ValueError):
        return 0


def df_used(path: Path) -> int:
    st = os.statvfs(path)
    return (st.f_blocks - st.f_bfree) * st.f_frsize


def is_protected(p: Path) -> bool:
    return any(p == q or q in p.parents for q in PROTECTED)


def git(root: Path, *args: str) -> str | None:
    r = subprocess.run(["git", "-C", str(root), *args], capture_output=True, text=True)
    return r.stdout.strip() if r.returncode == 0 else None


def project_root_of(artifact: Path) -> Path:
    for anc in artifact.parents:
        if any((anc / m).exists() for m in ("package.json", "pyproject.toml", "Cargo.toml", ".git")):
            return anc
    return artifact.parent


def newest_mtime(root: Path, limit: int = 4000) -> float:
    newest = 0.0
    seen = 0
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in PRUNE]
        for f in filenames:
            try:
                m = os.lstat(os.path.join(dirpath, f)).st_mtime
            except OSError:
                continue
            newest = max(newest, m)
            seen += 1
            if seen >= limit:
                return newest
    return newest


def process_cwds() -> set[str]:
    r = subprocess.run(["lsof", "-d", "cwd", "-Fn"], capture_output=True, text=True)
    return {line[1:] for line in r.stdout.splitlines() if line.startswith("n")}


def find_artifacts(roots: list[Path]) -> list[Path]:
    found: list[Path] = []
    for root in roots:
        for dirpath, dirnames, _ in os.walk(root):
            here = Path(dirpath)
            if is_protected(here):
                dirnames[:] = []
                continue
            keep = []
            for d in dirnames:
                full = here / d
                if d in ARTIFACTS and not full.is_symlink():
                    found.append(full)
                elif d not in PRUNE:
                    keep.append(d)
            dirnames[:] = keep
    return found


def classify(art: Path, cwds: set[str], idle_threshold: float, now: float) -> Candidate:
    root = project_root_of(art)
    kind = art.name
    size = du(art)
    evidence = next((e for e in ARTIFACTS[kind] if (root / e).exists()), None)
    rebuild = REBUILD.get(evidence) if evidence else ("rebuild by running the project's build" if not ARTIFACTS[kind] else None)
    branch = git(root, "branch", "--show-current")
    status = git(root, "status", "--porcelain")
    dirty = len(status.splitlines()) if status is not None else None
    last_commit = git(root, "log", "-1", "--format=%cs")
    idle = (now - newest_mtime(root)) / 3600 if root.exists() else None

    base = dict(path=str(art), kind=kind, size_bytes=size, project_root=str(root), evidence=evidence,
                rebuild_cmd=rebuild, branch=branch, dirty_files=dirty, last_commit=last_commit,
                idle_hours=round(idle, 1) if idle is not None else None)
    if is_protected(art):
        return Candidate(**base, decision="skip-protected", reason="agent state, never touched")
    if ARTIFACTS[kind] and not evidence:
        return Candidate(**base, decision="skip-no-evidence", reason=f"no {'/'.join(ARTIFACTS[kind])}; rebuild not guaranteed")
    if kind == "node_modules" and evidence == "pnpm-lock.yaml" and (art / ".modules.yaml").exists():
        return Candidate(**base, decision="skip-apfs-clone", reason="pnpm node_modules share blocks with the store; deleting frees ~0")
    if any(c == str(root) or c.startswith(str(root) + "/") for c in cwds):
        return Candidate(**base, decision="skip-in-use", reason="a running process has its cwd inside this project")
    if idle is not None and idle < idle_threshold:
        return Candidate(**base, decision="skip-active", reason=f"files changed {idle:.1f}h ago, below --idle-hours {idle_threshold}")
    return Candidate(**base, decision="rebuildable", reason="lockfile or build present, project idle")


def ensure_state_repo() -> None:
    STATE.mkdir(parents=True, exist_ok=True)
    (STATE / "runs").mkdir(exist_ok=True)
    (STATE / "logs").mkdir(exist_ok=True)
    if not (STATE / ".git").exists():
        subprocess.run(["git", "init", "-q", str(STATE)], check=True)
        (STATE / ".gitignore").write_text("logs/\n")


def commit_state(msg: str) -> None:
    subprocess.run(["git", "-C", str(STATE), "add", "-A"], check=True)
    subprocess.run(["git", "-C", str(STATE), "commit", "-q", "-m", msg], capture_output=True)


def write_run(run: Run) -> Path:
    ensure_state_repo()
    out = STATE / "runs" / f"{run.run_id}.json"
    out.write_text(json.dumps(asdict(run), ensure_ascii=False, indent=2))
    with LEDGER.open("a") as f:
        for c in run.candidates:
            if c.decision == "rebuildable":
                f.write(json.dumps({"run_id": run.run_id, "ts": run.started, "mode": run.mode, "acted": c.path in run.acted,
                                    "method": run.method, **asdict(c)}, ensure_ascii=False) + "\n")
    commit_state(f"{run.mode} {run.run_id}: {len(run.acted)} acted, {human(run.freed_bytes)} freed")
    return out


def print_report(run: Run, top: int = 40) -> None:
    rebuild = [c for c in run.candidates if c.decision == "rebuildable"]
    skipped = [c for c in run.candidates if c.decision != "rebuildable"]
    total = sum(c.size_bytes for c in rebuild)
    print(f"\n== devsweep {run.mode} {run.run_id}  roots={', '.join(run.roots)}")
    print("protected (reported only, never touched):")
    for p, s in run.protected_sizes.items():
        print(f"  {human(s):>8}  {p}")
    print(f"\nrebuildable: {len(rebuild)} items, {human(total)} (du; APFS clones overestimate)")
    for c in sorted(rebuild, key=lambda c: -c.size_bytes)[:top]:
        print(f"  {human(c.size_bytes):>8}  {c.path}   [{c.branch or '-'} dirty={c.dirty_files} idle={c.idle_hours}h]  -> {c.rebuild_cmd}")
    if len(rebuild) > top:
        print(f"  ... {len(rebuild) - top} more in runs/{run.run_id}.json")
    by_reason: dict[str, tuple[int, int]] = {}
    for c in skipped:
        n, s = by_reason.get(c.decision, (0, 0))
        by_reason[c.decision] = (n + 1, s + c.size_bytes)
    print("\nskipped: " + ", ".join(f"{k} {n}/{human(s)}" for k, (n, s) in by_reason.items()))
    if run.acted:
        actual = human(run.freed_bytes_actual) if run.freed_bytes_actual is not None else "n/a"
        print(f"\nacted on {len(run.acted)} items: du {human(run.freed_bytes)}, df measured {actual} ({run.method})")


def act(run: Run, purge: bool, limit: int | None) -> None:
    trash_dir = HOME / ".Trash" / f"devsweep-{run.run_id}"
    run.method = "purge" if purge else f"trash:{trash_dir}"
    before = df_used(HOME)
    for c in run.candidates:
        if limit is not None and len(run.acted) >= limit:
            break
        if c.decision != "rebuildable":
            continue
        p = Path(c.path)
        # last gate: whitelisted basename, real directory, not a symlink, not protected
        if p.name not in ARTIFACTS or p.is_symlink() or is_protected(p) or not p.is_dir():
            continue
        if purge:
            shutil.rmtree(p, ignore_errors=True)
        else:
            dest = trash_dir / c.project_root.strip("/").replace("/", "__") / p.name
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(p), str(dest))
        run.acted.append(c.path)
        run.freed_bytes += c.size_bytes
    run.freed_bytes_actual = before - df_used(HOME)


def cmd_worktrees(roots: list[Path]) -> None:
    """List every git worktree with dirty/merged/pushed state. Never removes anything."""
    seen: set[str] = set()
    for root in roots:
        for dirpath, dirnames, _ in os.walk(root):
            here = Path(dirpath)
            if is_protected(here) or here.name in PRUNE - {".git"}:
                dirnames[:] = []
                continue
            if ".git" in dirnames and (here / ".git").is_dir():
                dirnames.remove(".git")
                out = git(here, "worktree", "list", "--porcelain") or ""
                for block in out.split("\n\n"):
                    wt = next((l[9:] for l in block.splitlines() if l.startswith("worktree ")), None)
                    if not wt or wt in seen:
                        continue
                    seen.add(wt)
                    wp = Path(wt)
                    br = git(wp, "branch", "--show-current") or "(detached)"
                    dirty = len((git(wp, "status", "--porcelain") or "").splitlines()) if wp.exists() else None
                    merged = git(here, "merge-base", "--is-ancestor", br, "main") is not None if br != "(detached)" else False
                    upstream = git(wp, "rev-parse", "--abbrev-ref", "@{u}") if wp.exists() else None
                    ahead = git(wp, "rev-list", "--count", "@{u}..HEAD") if upstream else "no-upstream"
                    size = du(wp) if wp.exists() else 0
                    flag = "MISSING" if not wp.exists() else ("CANDIDATE" if dirty == 0 and merged and ahead == "0" else "")
                    print(f"{human(size):>8}  dirty={dirty!s:>4} merged={str(merged):5} ahead={ahead:>11}  {br:45} {wt}  {flag}")
    print("\nCANDIDATE = clean, merged into main, nothing unpushed. devsweep never removes worktrees;"
          " decide yourself with `git worktree remove <path>`.")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("mode", choices=["scan", "apply", "worktrees", "ledger"], nargs="?", default="scan")
    ap.add_argument("--root", action="append", help="directory to scan (repeatable); default ~/Developer")
    ap.add_argument("--protect", action="append", help="extra path that is never a target (repeatable)")
    ap.add_argument("--idle-hours", type=float, default=48, help="project must be untouched this long (default 48)")
    ap.add_argument("--yes", action="store_true", help="required for apply to act")
    ap.add_argument("--purge", action="store_true", help="apply: delete instead of moving to ~/.Trash (Trash frees nothing until emptied)")
    ap.add_argument("--limit", type=int, help="apply: act on at most N items (try 1 first and read the df delta)")
    ap.add_argument("--only", help="apply: only candidates whose path contains this string")
    ap.add_argument("--kind", action="append", help="apply: only these artifact kinds (repeatable), e.g. --kind .next")
    a = ap.parse_args()

    PROTECTED.extend(Path(p).expanduser() for p in (a.protect or []))

    if a.mode == "ledger":
        if LEDGER.exists():
            sys.stdout.write(LEDGER.read_text())
        subprocess.run(["git", "-C", str(STATE), "log", "--oneline", "-20"])
        return 0

    roots = [Path(r).expanduser() for r in (a.root or [str(HOME / "Developer")])]
    if a.mode == "worktrees":
        cmd_worktrees(roots)
        return 0

    now = dt.datetime.now()
    run = Run(run_id=now.strftime("%Y%m%d-%H%M%S"), started=now.isoformat(timespec="seconds"), mode=a.mode,
              roots=[str(r) for r in roots], idle_hours_threshold=a.idle_hours)
    run.protected_sizes = {str(p): du(p) for p in PROTECTED if p.exists()}
    cwds = process_cwds()
    ts = now.timestamp()
    run.candidates = [classify(p, cwds, a.idle_hours, ts) for p in find_artifacts(roots)]

    if a.mode == "apply":
        if not a.yes:
            print("apply needs --yes. Run scan first and read the report.", file=sys.stderr)
            return 2
        for c in run.candidates:
            if c.decision != "rebuildable":
                continue
            if a.only and a.only not in c.path:
                c.decision, c.reason = "skip-filtered", f"--only {a.only}"
            elif a.kind and c.kind not in a.kind:
                c.decision, c.reason = "skip-filtered", f"--kind {','.join(a.kind)}"
        write_run(run)  # manifest first, then act
        act(run, a.purge, a.limit)
    out = write_run(run)
    print_report(run)
    print(f"\nmanifest: {out}\nledger:   {LEDGER}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
