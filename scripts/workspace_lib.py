#!/usr/bin/env python3
"""Shared helpers for the rules sync, the publisher and their tests.

Small on purpose. The one non-obvious function is `deny_sync_names()`: the set of repos
the rules sync must never write into is the union of a hand-kept list and the audiences
of `scripts/publish-shared-repo.py`, parsed out of that file with `ast`. A repo an
outside reader sees must never receive the constitution, and a hand-kept list of "which
repos are read outside" gets missed the next time such a repo is created by a different
workflow. The publisher's own table is the one source of truth, so read that.
"""

from __future__ import annotations

import ast
import json
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable


def spine_root() -> Path:
    env = os.environ.get("LANE_OS_ROOT")
    if env and (Path(env).expanduser() / ".git").exists():
        return Path(env).expanduser().resolve()
    return Path(__file__).resolve().parents[1]


# ----------------------------------------------------------------- manifest
def _parse_toml_subset(text: str) -> dict[str, Any]:
    """Enough TOML for workspace.toml: strings, string arrays, booleans, integers,
    [tables] and [[arrays of tables]]. Used only when tomllib is unavailable."""
    root: dict[str, Any] = {}
    current: dict[str, Any] = root
    for raw in text.splitlines():
        line = raw.split("#", 1)[0].strip() if not raw.strip().startswith('"') else raw.strip()
        # keep '#' inside quoted strings
        if "#" in raw and '"' in raw:
            line = raw.strip()
            if line.startswith("#"):
                continue
        if not line:
            continue
        m = re.match(r"^\[\[(.+?)\]\]$", line)
        if m:
            arr = root.setdefault(m.group(1).strip(), [])
            current = {}
            arr.append(current)
            continue
        m = re.match(r"^\[(.+?)\]$", line)
        if m:
            current = root.setdefault(m.group(1).strip(), {})
            continue
        m = re.match(r"^([A-Za-z0-9_.-]+)\s*=\s*(.+)$", line)
        if not m:
            continue
        key, val = m.group(1), m.group(2).strip()
        if val.startswith("["):
            current[key] = re.findall(r'"((?:[^"\\]|\\.)*)"', val)
        elif val.startswith('"'):
            current[key] = json.loads(val.split('" ', 1)[0] if val.count('"') > 2 else val)
        elif val in ("true", "false"):
            current[key] = val == "true"
        else:
            try:
                current[key] = int(val)
            except ValueError:
                current[key] = val
    return root


def load_manifest(root: Path | None = None) -> dict[str, Any]:
    path = (root or spine_root()) / "workspace.toml"
    text = path.read_text(encoding="utf-8")
    try:
        import tomllib  # Python 3.11+
        return tomllib.loads(text)
    except ModuleNotFoundError:
        return _parse_toml_subset(text)


def workspace_roots(manifest: dict[str, Any] | None = None) -> list[Path]:
    env = os.environ.get("LANE_OS_WORKSPACE_ROOTS")
    if env:
        return [Path(p).expanduser() for p in env.split(":") if p]
    manifest = manifest or load_manifest()
    return [Path(p).expanduser() for p in manifest.get("workspace", {}).get("workspace_roots", [])]


# -------------------------------------------------------------------- repos
@dataclass(frozen=True)
class RepoRef:
    name: str
    path: Path


def discover_git_repos(manifest: dict[str, Any] | None = None) -> list[RepoRef]:
    spine = spine_root()
    out: list[RepoRef] = []
    seen: set[Path] = set()
    for root in workspace_roots(manifest):
        if not root.is_dir():
            continue
        for child in sorted(root.iterdir()):
            if child.name.startswith(".") or not (child / ".git").exists():
                continue
            real = child.resolve()
            if real == spine or real in seen:
                continue
            seen.add(real)
            out.append(RepoRef(child.name, child))
    return out


def find_repo(name: str, manifest: dict[str, Any] | None = None) -> RepoRef | None:
    for repo in discover_git_repos(manifest):
        if repo.name == name:
            return repo
    return None


def manifest_repos(manifest: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    manifest = manifest or load_manifest()
    return list(manifest.get("repos", []))


# ---------------------------------------------------------------- deny list
def published_audience_names(publisher: Path | None = None) -> set[str]:
    """Every repo scripts/publish-shared-repo.py publishes to, read straight from it.

    Parsed, never imported: executing the publisher would run its argument parsing. A
    failure to parse denies nothing extra rather than raising, because the caller's job
    is a sync, not this lookup; the sibling test asserts the parse still finds them,
    because an empty result reads as a pass everywhere else.
    """
    src = publisher or (Path(__file__).resolve().parent / "publish-shared-repo.py")
    try:
        tree = ast.parse(src.read_text(encoding="utf-8"))
    except Exception:
        return set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.Assign):
            continue
        if not any(getattr(t, "id", None) == "AUDIENCES" for t in node.targets):
            continue
        if not isinstance(node.value, ast.Dict):
            continue
        return {k.value for k in node.value.keys if isinstance(k, ast.Constant) and isinstance(k.value, str)}
    return set()


def deny_sync_names(manifest: dict[str, Any] | None = None) -> set[str]:
    manifest = manifest or load_manifest()
    hand = set(manifest.get("globals", {}).get("deny_sync", []))
    return hand | {spine_root().name} | published_audience_names()


# ------------------------------------------------------------- rules text
def generated_header(manifest: dict[str, Any] | None = None) -> str:
    manifest = manifest or load_manifest()
    return manifest["globals"]["generated_header"]


def expected_global_rules_text(manifest: dict[str, Any] | None = None) -> str:
    manifest = manifest or load_manifest()
    source = spine_root() / manifest["globals"]["source"]
    return f"{generated_header(manifest)}\n\n{source.read_text(encoding='utf-8')}"


def expected_agents_block(manifest: dict[str, Any] | None = None) -> str:
    manifest = manifest or load_manifest()
    g = manifest["globals"]
    body = (spine_root() / g["source"]).read_text(encoding="utf-8")
    return (f"{g['agents_begin']}\n{generated_header(manifest)}\n\n"
            "Edit the source in the spine, not this generated copy.\n\n"
            f"{body.rstrip()}\n{g['agents_end']}\n")


def marked_block(text: str, begin: str, end: str) -> str | None:
    i = text.find(begin)
    j = text.find(end, i + len(begin)) if i >= 0 else -1
    if i < 0 or j < 0:
        return None
    return text[i: j + len(end)]


def is_generated_rules_copy(path: Path) -> bool:
    try:
        first = path.read_text(errors="replace").splitlines()[0]
    except Exception:
        return False
    return "GENERATED from" in first and "global/CLAUDE.md" in first


def sync_target_repos(manifest: dict[str, Any] | None = None) -> list[RepoRef]:
    """Manifest repos with sync_globals, plus any discovered repo that already carries a
    generated copy, minus the deny list."""
    manifest = manifest or load_manifest()
    deny = deny_sync_names(manifest)
    by_name: dict[str, RepoRef] = {}
    for entry in manifest_repos(manifest):
        if not entry.get("sync_globals"):
            continue
        found = find_repo(entry["name"], manifest)
        if found and found.name not in deny:
            by_name[found.name] = found
    copy_rel = manifest["globals"]["sync_copy"]
    for repo in discover_git_repos(manifest):
        if repo.name in deny or repo.name in by_name:
            continue
        if (repo.path / copy_rel).is_file() and is_generated_rules_copy(repo.path / copy_rel):
            by_name[repo.name] = repo
    return sorted(by_name.values(), key=lambda r: r.name.lower())


# ------------------------------------------------------------ live sessions
def live_session_cwds() -> set[str]:
    """Repos that currently have a Claude Code session open, by resolved path.

    ~/.claude/sessions/<pid>.json is written per session and named by its PID, so
    liveness is a signal(0), not a guess about file age. Fails open: an unreadable
    session file never blocks a sync.
    """
    out: set[str] = set()
    sessions = Path.home() / ".claude" / "sessions"
    if not sessions.is_dir():
        return out
    for entry in sessions.glob("*.json"):
        try:
            pid = int(entry.stem)
        except ValueError:
            continue
        try:
            os.kill(pid, 0)
        except (ProcessLookupError, ValueError):
            continue
        except PermissionError:
            pass  # alive, owned by another user
        except Exception:
            continue
        try:
            data = json.loads(entry.read_text(errors="replace"))
        except Exception:
            continue
        cwd = data.get("cwd") or data.get("workingDirectory")
        if cwd:
            try:
                out.add(str(Path(cwd).resolve()))
            except Exception:
                out.add(str(cwd))
    return out


def git_ignored(repo: Path, rel: str) -> bool:
    import subprocess
    return subprocess.run(["git", "check-ignore", "-q", rel], cwd=repo,
                          capture_output=True).returncode == 0
