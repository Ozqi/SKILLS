#!/usr/bin/env python3
"""本地 Markdown 目录与飞书 Drive 原生 Markdown 文件的同步器。

同步模型：
1. `lark-md-sync.config.json` 只描述目录级映射：
   本地目录 `local_dir` <-> 飞书 Drive 文件夹 / Wiki 节点。
2. `tmp/lark-md-sync/state.json` 记录文件级映射：
   每个本地 `.md` <-> 一个飞书原生 Markdown 文件 token。
3. `tmp/lark-md-sync/base/` 缓存上次两端一致的版本，用于三方 merge。

默认不写远端，也不改本地正文；只有显式传 `--apply` 才执行写入。
"""

from __future__ import annotations

SCRIPT_META = {
    "name": "lark_md_sync",
    "summary": "Bidirectionally sync local Markdown files with Lark Drive native Markdown files via sara-lark-cli.",
    "inputs": "CLI subcommands (cd|track|status|push|pull|sync|untrack|init-config|plan-config|list|ls), local Markdown paths, config mappings, Lark file tokens or target folders, and a local state file.",
    "outputs": "stdout plan/status plus local state, cached base files, and optional local/remote Markdown writes.",
    "writes": "tmp/lark-md-sync/** by default; local Markdown files on pull/sync --apply; remote Lark Markdown files on push/sync --apply.",
    "idempotent": True,
    "safe_to_autorun": False,
}

import argparse
import hashlib
import json
import os
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from urllib.parse import urlparse
from pathlib import Path
from typing import Any

DEFAULT_STATE = Path("tmp/lark-md-sync/state.json")
DEFAULT_CONFIG = Path("lark-md-sync.config.json")
BASE_DIR = Path("tmp/lark-md-sync/base")
FETCH_DIR = Path("tmp/lark-md-sync/fetch")
MERGE_DIR = Path("tmp/lark-md-sync/merge")
STATE_VERSION = 1
LARK_CLI = os.environ.get("SARA_LARK_CLI", "sara-lark-cli")
META_CLI = os.environ.get("LARK_CLI", "lark-cli")


class ToolError(Exception):
    """User-facing error without traceback."""


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def safe_name(rel: str) -> str:
    digest = hashlib.sha256(rel.encode("utf-8")).hexdigest()[:16]
    stem = Path(rel).name.replace("/", "_")
    return f"{digest}-{stem}"


def read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except FileNotFoundError as exc:
        raise ToolError(f"local file not found: {path}") from exc
    except UnicodeDecodeError as exc:
        raise ToolError(f"local file is not valid UTF-8 Markdown: {path}") from exc


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def resolve_rel(root: Path, value: str) -> str:
    path = Path(value)
    resolved = path if path.is_absolute() else root / path
    resolved = resolved.resolve()
    try:
        rel = resolved.relative_to(root.resolve()).as_posix()
    except ValueError as exc:
        raise ToolError(f"path is outside vault root: {value}") from exc
    if rel == "RAW" or rel.startswith("RAW/"):
        raise ToolError(f"refusing to sync immutable raw source path: {rel}")
    if not rel.endswith(".md"):
        raise ToolError(f"only .md files are supported: {rel}")
    return rel


def resolve_dir_rel(root: Path, value: str) -> str:
    path = Path(value)
    resolved = path if path.is_absolute() else root / path
    resolved = resolved.resolve()
    try:
        rel = resolved.relative_to(root.resolve()).as_posix()
    except ValueError as exc:
        raise ToolError(f"directory is outside vault root: {value}") from exc
    if rel == "RAW" or rel.startswith("RAW/"):
        raise ToolError(f"refusing to sync immutable raw source directory: {rel}")
    return "." if rel == "" else rel


def iter_markdown_under(root: Path, local_dir: str) -> list[str]:
    base = root if local_dir == "." else root / local_dir
    if not base.exists():
        raise ToolError(f"local_dir does not exist: {local_dir}")
    if not base.is_dir():
        raise ToolError(f"local_dir is not a directory: {local_dir}")
    out: list[str] = []
    for path in sorted(base.rglob("*.md")):
        rel_parts = path.relative_to(base).parts
        if any(part.startswith(".") for part in rel_parts):
            continue
        out.append(path.relative_to(root).as_posix())
    return out


def load_state(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"version": STATE_VERSION, "files": {}}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ToolError(f"invalid state JSON: {path}: {exc.msg}") from exc
    if not isinstance(data, dict):
        raise ToolError(f"state must be a JSON object: {path}")
    data.setdefault("version", STATE_VERSION)
    data.setdefault("files", {})
    if not isinstance(data["files"], dict):
        raise ToolError(f"state.files must be an object: {path}")
    return data


def load_config(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise ToolError(f"config file not found: {path}")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ToolError(f"invalid config JSON: {path}: {exc.msg}") from exc
    if not isinstance(data, dict):
        raise ToolError(f"config must be a JSON object: {path}")
    mappings = data.get("mappings")
    if not isinstance(mappings, list):
        raise ToolError("config.mappings must be a list")
    return data


def save_state(path: Path, state: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def base_path(sha: str) -> Path:
    return BASE_DIR / f"{sha}.md"


def cache_base(root: Path, content: str) -> str:
    sha = sha256_text(content)
    path = root / base_path(sha)
    if not path.exists():
        write_text(path, content)
    return sha


def read_base(root: Path, mapping: dict[str, Any]) -> str | None:
    sha = mapping.get("base_sha256")
    if not isinstance(sha, str) or not sha:
        return None
    path = root / base_path(sha)
    if not path.exists():
        return None
    return read_text(path)


def update_mapping_base(root: Path, mapping: dict[str, Any], content: str) -> None:
    mapping["base_sha256"] = cache_base(root, content)
    mapping["updated_at"] = now_iso()


def run_cmd(cmd: list[str], root: Path) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env.setdefault("LARKSUITE_CLI_NO_UPDATE_NOTIFIER", "1")
    env.setdefault("LARKSUITE_CLI_NO_SKILLS_NOTIFIER", "1")
    try:
        return subprocess.run(
            cmd,
            cwd=root,
            env=env,
            check=True,
            text=True,
            capture_output=True,
        )
    except FileNotFoundError as exc:
        raise ToolError(f"command not found: {cmd[0]}") from exc
    except subprocess.CalledProcessError as exc:
        message = (exc.stderr or exc.stdout or "").strip()
        raise ToolError(
            f"command failed ({exc.returncode}): {' '.join(cmd)}\n{message}"
        ) from exc


def parse_json_stdout(result: subprocess.CompletedProcess[str]) -> dict[str, Any]:
    text = (result.stdout or "").strip()
    if not text:
        return {}
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ToolError(f"{LARK_CLI} returned non-JSON output: {text[:300]}") from exc
    if isinstance(data, dict):
        return data
    raise ToolError(f"{LARK_CLI} JSON output was not an object")


def lark_data(cmd: list[str], root: Path) -> Any:
    data = parse_json_stdout(run_cmd(cmd, root))
    if data.get("ok") is False:
        raise ToolError(str(data.get("error") or data))
    return data.get("data", {})


def find_token(value: Any) -> str | None:
    if isinstance(value, dict):
        for key in ("file_token", "fileToken", "token", "obj_token", "objToken"):
            item = value.get(key)
            if isinstance(item, str) and item:
                return item
        for item in value.values():
            token = find_token(item)
            if token:
                return token
    elif isinstance(value, list):
        for item in value:
            token = find_token(item)
            if token:
                return token
    return None


def config_plan(root: Path, config: dict[str, Any]) -> list[dict[str, str]]:
    """把目录级配置展开为具体 Markdown 文件的同步计划。"""
    plan: list[dict[str, str]] = []
    for index, item in enumerate(config["mappings"]):
        if not isinstance(item, dict):
            raise ToolError(f"config mapping must be an object at index {index}")
        local_dir = resolve_dir_rel(root, str(item.get("local_dir") or ""))
        identity = str(item.get("identity") or config.get("identity") or "user")
        if identity not in {"user", "bot"}:
            raise ToolError(f"invalid identity in config: {identity}")
        if item.get("wiki_token"):
            target_flag = "--wiki-token"
            target = str(item["wiki_token"])
        elif item.get("folder_token"):
            target_flag = "--folder-token"
            target = str(item["folder_token"])
        elif item.get("target_url"):
            # sara-lark-cli markdown +create 会把 Drive 文件夹 URL 归一成 folder token。
            target_flag = "--folder-token"
            target = str(item["target_url"])
        else:
            raise ToolError(
                "each mapping requires folder_token, wiki_token, or target_url"
            )

        mapping = str(item.get("name") or f"mapping-{index + 1}")
        for rel in iter_markdown_under(root, local_dir):
            name = Path(rel).name
            if bool(item.get("preserve_subdirs", False)):
                prefix = "" if local_dir == "." else local_dir.rstrip("/") + "/"
                name = rel.removeprefix(prefix).replace("/", "__")
            plan.append(
                {
                    "mapping": mapping,
                    "path": rel,
                    "identity": identity,
                    "target": target,
                    "target_flag": target_flag,
                    "remote_name": name,
                }
            )
    return plan


def fetch_remote(root: Path, rel: str, mapping: dict[str, Any]) -> str:
    """读取远端 Markdown 到 tmp 缓存，并返回内容。"""
    file_token = mapping.get("file_token")
    if not isinstance(file_token, str) or not file_token:
        raise ToolError(f"missing file_token in state for {rel}")
    identity = str(mapping.get("identity") or "user")
    out_rel = FETCH_DIR / safe_name(rel)
    out_path = root / out_rel
    out_path.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        LARK_CLI,
        "markdown",
        "+fetch",
        "--as",
        identity,
        "--file-token",
        file_token,
        "--output",
        out_rel.as_posix(),
        "--overwrite",
        "--format",
        "json",
    ]
    run_cmd(cmd, root)
    return read_text(out_path)


def create_remote(
    root: Path,
    rel: str,
    identity: str,
    name: str,
    apply: bool,
    target: list[str],
) -> str:
    """创建远端 Markdown 文件；无 --apply 时只打印将执行的 CLI 命令。"""
    cmd = [
        LARK_CLI,
        "markdown",
        "+create",
        "--as",
        identity,
        "--file",
        rel,
        "--name",
        name,
        "--format",
        "json",
    ]
    cmd.extend(target)
    if not apply:
        print("DRY-RUN create:", " ".join(cmd))
        return ""
    data = parse_json_stdout(run_cmd(cmd, root))
    token = find_token(data)
    if not token:
        raise ToolError("could not find file token in create response")
    return token


def overwrite_remote(
    root: Path, rel: str, mapping: dict[str, Any], file_rel: str, apply: bool
) -> None:
    """覆盖远端 Markdown 文件；所有远端写入都集中经过这个函数。"""
    file_token = mapping.get("file_token")
    if not isinstance(file_token, str) or not file_token:
        raise ToolError(f"missing file_token in state for {rel}")
    identity = str(mapping.get("identity") or "user")
    cmd = [
        LARK_CLI,
        "markdown",
        "+overwrite",
        "--as",
        identity,
        "--file-token",
        file_token,
        "--file",
        (root / file_rel).resolve().relative_to(root.resolve()).as_posix(),
        "--format",
        "json",
    ]
    if not apply:
        print("DRY-RUN overwrite:", " ".join(cmd))
        return
    run_cmd(cmd, root)


def requested_targets(
    root: Path, state: dict[str, Any], args: argparse.Namespace
) -> list[str]:
    config_path = getattr(args, "config", None)
    if config_path:
        paths = [item["path"] for item in config_plan(root, load_config(config_path))]
        if args.paths:
            requested = {resolve_rel(root, item) for item in args.paths}
            return [path for path in paths if path in requested]
        return paths
    if args.paths:
        return [resolve_rel(root, item) for item in args.paths]
    return sorted(state["files"].keys())


def file_status(root: Path, rel: str, mapping: dict[str, Any]) -> dict[str, Any]:
    local_path = root / rel
    local_exists = local_path.exists()
    local_content = read_text(local_path) if local_exists else ""
    local_sha = sha256_text(local_content) if local_exists else ""
    remote_content = fetch_remote(root, rel, mapping)
    remote_sha = sha256_text(remote_content)
    base_sha = str(mapping.get("base_sha256") or "")
    return {
        "path": rel,
        "local_exists": local_exists,
        "local_sha256": local_sha,
        "remote_sha256": remote_sha,
        "base_sha256": base_sha,
        "local_changed": bool(local_sha and local_sha != base_sha),
        "remote_changed": bool(remote_sha != base_sha),
        "remote_content": remote_content,
        "local_content": local_content,
    }


def print_status(status: dict[str, Any]) -> None:
    rel = status["path"]
    if not status["local_exists"]:
        print(f"{rel}: missing-local remote_changed={status['remote_changed']}")
    elif status["local_changed"] and status["remote_changed"]:
        print(f"{rel}: both-changed")
    elif status["local_changed"]:
        print(f"{rel}: local-changed")
    elif status["remote_changed"]:
        print(f"{rel}: remote-changed")
    else:
        print(f"{rel}: clean")


def merge_contents(
    root: Path, rel: str, local: str, base: str, remote: str
) -> tuple[str, bool]:
    """用 git merge-file 做 local/base/remote 三方合并。"""
    MERGE_DIR.mkdir(parents=True, exist_ok=True)
    prefix = safe_name(rel)
    with tempfile.TemporaryDirectory(prefix=prefix + "-", dir=root / MERGE_DIR) as tmp:
        tmp_path = Path(tmp)
        local_path = tmp_path / "local.md"
        base_path_ = tmp_path / "base.md"
        remote_path = tmp_path / "remote.md"
        local_path.write_text(local, encoding="utf-8")
        base_path_.write_text(base, encoding="utf-8")
        remote_path.write_text(remote, encoding="utf-8")
        result = subprocess.run(
            [
                "git",
                "merge-file",
                "-p",
                str(local_path),
                str(base_path_),
                str(remote_path),
            ],
            cwd=root,
            text=True,
            capture_output=True,
        )
        if result.returncode not in (0, 1):
            raise ToolError(f"git merge-file failed for {rel}: {result.stderr.strip()}")
        return result.stdout, result.returncode == 1


def track(args: argparse.Namespace) -> int:
    """绑定已有远端 Markdown 文件；远端当前内容成为初始 base。"""
    root = args.root.resolve()
    state = load_state(args.state)
    rel = resolve_rel(root, args.path)
    mapping = {
        "file_token": args.file_token,
        "identity": args.identity,
        "name": args.name or Path(rel).name,
        "tracked_at": now_iso(),
    }
    remote = fetch_remote(root, rel, mapping)
    local_path = root / rel
    if not local_path.exists():
        if not args.pull_initial:
            raise ToolError(
                f"local file does not exist; use --pull-initial to create it from remote: {rel}"
            )
        if args.apply:
            write_text(local_path, remote)
        else:
            print(f"DRY-RUN would create local file from remote: {rel}")
    elif read_text(local_path) != remote:
        print(f"{rel}: local and remote differ; using remote as initial base")
    update_mapping_base(root, mapping, remote)
    if args.apply:
        state["files"][rel] = mapping
        save_state(args.state, state)
        print(f"tracked: {rel}")
    else:
        print(f"DRY-RUN would track {rel} -> {args.file_token}")
    return 0


def untrack(args: argparse.Namespace) -> int:
    state = load_state(args.state)
    changed = False
    for path in args.paths:
        rel = resolve_rel(args.root.resolve(), path)
        if rel in state["files"]:
            changed = True
            if args.apply:
                state["files"].pop(rel, None)
                print(f"untracked: {rel}")
            else:
                print(f"DRY-RUN would untrack: {rel}")
    if changed and args.apply:
        save_state(args.state, state)
    return 0


def status_cmd(args: argparse.Namespace) -> int:
    root = args.root.resolve()
    state = load_state(args.state)
    targets = requested_targets(root, state, args)
    records: list[dict[str, Any]] = []
    for rel in targets:
        mapping = state["files"].get(rel)
        if not mapping:
            print(f"{rel}: untracked")
            continue
        record = file_status(root, rel, mapping)
        records.append({k: v for k, v in record.items() if not k.endswith("_content")})
        print_status(record)
    if args.json:
        print(json.dumps(records, ensure_ascii=False, indent=2))
    return 0


def push(args: argparse.Namespace) -> int:
    """本地推远端；配置模式下会遍历 local_dir 下所有 Markdown。"""
    root = args.root.resolve()
    state = load_state(args.state)
    if args.config:
        items = config_plan(root, load_config(args.config))
        if args.paths:
            requested = {resolve_rel(root, item) for item in args.paths}
            items = [item for item in items if item["path"] in requested]
    else:
        items = []
        for raw in args.paths:
            rel = resolve_rel(root, raw)
            items.append(
                {
                    "path": rel,
                    "identity": args.identity,
                    "remote_name": args.name or Path(rel).name,
                    "target_flag": "",
                    "target": "",
                }
            )

    for item in items:
        rel = item["path"]
        local = read_text(root / rel)
        mapping = state["files"].get(rel)
        if not mapping:
            if args.config:
                target = [item["target_flag"], item["target"]]
            else:
                target = []
                if args.folder_token:
                    target.extend(["--folder-token", args.folder_token])
                if args.wiki_token:
                    target.extend(["--wiki-token", args.wiki_token])
            token = create_remote(
                root,
                rel,
                item["identity"],
                item["remote_name"],
                args.apply,
                target,
            )
            if args.apply:
                mapping = {
                    "file_token": token,
                    "identity": item["identity"],
                    "name": item["remote_name"],
                    "tracked_at": now_iso(),
                }
                update_mapping_base(root, mapping, local)
                state["files"][rel] = mapping
                save_state(args.state, state)
                print(f"created remote and tracked: {rel}")
            continue
        record = file_status(root, rel, mapping)
        if record["remote_changed"]:
            raise ToolError(
                f"remote changed since last sync; pull or sync before push: {rel}"
            )
        overwrite_remote(root, rel, mapping, rel, args.apply)
        if args.apply:
            update_mapping_base(root, mapping, local)
            save_state(args.state, state)
            print(f"pushed: {rel}")
    if args.apply:
        save_state(args.state, state)
    return 0


def pull_or_sync(args: argparse.Namespace, sync_mode: bool) -> int:
    """pull 只更新本地；sync 会在本地变更时推送远端。"""
    root = args.root.resolve()
    state = load_state(args.state)
    targets = requested_targets(root, state, args)
    for rel in targets:
        mapping = state["files"].get(rel)
        if not mapping:
            print(f"{rel}: untracked")
            continue
        record = file_status(root, rel, mapping)
        local_path = root / rel
        remote = record["remote_content"]
        local = record["local_content"]
        base = read_base(root, mapping)

        if not record["local_changed"] and not record["remote_changed"]:
            print(f"{rel}: clean")
            continue

        if record["remote_changed"] and not record["local_changed"]:
            if args.apply:
                write_text(local_path, remote)
                update_mapping_base(root, mapping, remote)
                save_state(args.state, state)
                print(f"pulled: {rel}")
            else:
                print(f"DRY-RUN would pull: {rel}")
            continue

        if record["local_changed"] and not record["remote_changed"]:
            if sync_mode:
                overwrite_remote(root, rel, mapping, rel, args.apply)
                if args.apply:
                    update_mapping_base(root, mapping, local)
                    save_state(args.state, state)
                    print(f"pushed: {rel}")
            else:
                print(f"{rel}: local changed; pull skipped")
            continue

        if args.on_conflict == "abort":
            print(f"{rel}: both changed; abort")
            continue
        if args.on_conflict == "remote-wins":
            if args.apply:
                write_text(local_path, remote)
                update_mapping_base(root, mapping, remote)
                save_state(args.state, state)
                print(f"remote wins: {rel}")
            else:
                print(f"DRY-RUN remote wins: {rel}")
            continue
        if args.on_conflict == "local-wins":
            if not sync_mode:
                print(
                    f"{rel}: both changed; local wins requested in pull mode, remote unchanged"
                )
                continue
            overwrite_remote(root, rel, mapping, rel, args.apply)
            if args.apply:
                update_mapping_base(root, mapping, local)
                save_state(args.state, state)
                print(f"local wins: {rel}")
            continue
        if base is None:
            print(f"{rel}: both changed; missing base cache; abort")
            continue

        merged, conflicted = merge_contents(root, rel, local, base, remote)
        if not args.apply:
            print(f"DRY-RUN would merge {rel}; conflicted={conflicted}")
            continue
        write_text(local_path, merged)
        if conflicted:
            print(f"merged with conflict markers; remote not overwritten: {rel}")
            continue
        merged_rel = (MERGE_DIR / f"{safe_name(rel)}.merged.md").as_posix()
        write_text(root / merged_rel, merged)
        if sync_mode:
            overwrite_remote(root, rel, mapping, merged_rel, True)
        update_mapping_base(root, mapping, merged)
        save_state(args.state, state)
        print(f"merged cleanly: {rel}")

    if args.apply:
        save_state(args.state, state)
    return 0


def infer_target(value: str, identity: str = "user") -> dict[str, str]:
    target = value.strip()
    if not target:
        raise ToolError("empty Lark target")
    parsed = urlparse(target)
    parts = [part for part in parsed.path.split("/") if part]
    kind = "url" if parsed.scheme and parsed.netloc else "token"
    token = ""
    for marker, marker_kind in (
        ("wiki", "wiki"),
        ("docx", "docx"),
        ("docs", "docs"),
        ("folder", "folder"),
        ("file", "file"),
    ):
        if marker in parts:
            index = parts.index(marker)
            if index + 1 < len(parts):
                kind = marker_kind
                token = parts[index + 1]
                break
    return {
        "target": target,
        "kind": kind,
        "token": token,
        "identity": identity,
        "updated_at": now_iso(),
    }


def cd_cmd(args: argparse.Namespace) -> int:
    state = load_state(args.state)
    current = infer_target(args.target, args.identity)
    state["current"] = current
    save_state(args.state, state)
    label = current["token"] or current["target"]
    print(f"current\t{current['kind']}\t{label}")
    return 0


def data_items(data: Any) -> list[Any]:
    if isinstance(data, list):
        return data
    if not isinstance(data, dict):
        return []
    for key in ("items", "files", "nodes", "children"):
        value = data.get(key)
        if isinstance(value, list):
            return value
    for value in data.values():
        items = data_items(value)
        if items:
            return items
    return []


def item_field(item: Any, *names: str) -> str:
    if not isinstance(item, dict):
        return ""
    for name in names:
        value = item.get(name)
        if isinstance(value, str) and value:
            return value
        if isinstance(value, bool):
            return str(value).lower()
        if isinstance(value, int):
            return str(value)
    return ""


def inspect_current(root: Path, current: dict[str, Any]) -> dict[str, Any]:
    target = str(current.get("target") or "")
    identity = str(current.get("identity") or "user")
    return lark_data(
        [
            META_CLI,
            "drive",
            "+inspect",
            "--url",
            target,
            "--as",
            identity,
            "--format",
            "json",
        ],
        root,
    )


def wiki_children(root: Path, current: dict[str, Any], page_size: int) -> list[Any]:
    target = str(current.get("target") or "")
    identity = str(current.get("identity") or "user")
    node = lark_data(
        [
            META_CLI,
            "wiki",
            "+node-get",
            "--node-token",
            target,
            "--as",
            identity,
            "--format",
            "json",
        ],
        root,
    )
    if not node.get("has_child"):
        return []
    data = lark_data(
        [
            META_CLI,
            "wiki",
            "+node-list",
            "--space-id",
            str(node["space_id"]),
            "--parent-node-token",
            str(node["node_token"]),
            "--page-size",
            str(page_size),
            "--as",
            identity,
            "--format",
            "json",
        ],
        root,
    )
    return data_items(data)


def folder_children(root: Path, token: str, identity: str, page_size: int) -> list[Any]:
    data = lark_data(
        [
            META_CLI,
            "drive",
            "files",
            "list",
            "--folder-token",
            token,
            "--page-size",
            str(page_size),
            "--as",
            identity,
            "--format",
            "json",
        ],
        root,
    )
    return data_items(data)


def remote_listing(root: Path, current: dict[str, Any], page_size: int) -> dict[str, Any]:
    meta = inspect_current(root, current)
    identity = str(current.get("identity") or "user")
    kind = str(meta.get("type") or current.get("kind") or "")
    token = str(meta.get("token") or current.get("token") or "")
    children: list[Any] = []
    wiki_node = meta.get("wiki_node") if isinstance(meta.get("wiki_node"), dict) else {}
    if wiki_node and wiki_node.get("node_token"):
        children = wiki_children(root, current, page_size)
    elif kind == "folder" and token:
        children = folder_children(root, token, identity, page_size)
    return {"meta": meta, "children": children}


def print_remote_listing(listing: dict[str, Any]) -> None:
    meta = listing["meta"]
    title = str(meta.get("title") or "")
    kind = str(meta.get("type") or "")
    token = str(meta.get("token") or "")
    url = str(meta.get("url") or meta.get("input_url") or "")
    print(f"remote\t{kind}\t{token}\t{title}\t{url}")
    for child in listing["children"]:
        title = item_field(child, "title", "name")
        kind = item_field(child, "obj_type", "type", "file_type")
        token = item_field(child, "node_token", "token", "file_token", "obj_token")
        has_child = item_field(child, "has_child")
        print(f"child\t{kind}\t{token}\t{title}\t{has_child}")


def list_cmd(args: argparse.Namespace) -> int:
    root = args.root.resolve()
    state = load_state(args.state)
    current = state.get("current")
    result: dict[str, Any] = {"current": current if isinstance(current, dict) else None, "tracked": state["files"]}
    if isinstance(current, dict) and current.get("target") and not args.no_remote:
        result["remote"] = remote_listing(root, current, args.page_size)
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    if isinstance(current, dict) and current.get("target"):
        print(
            f"current\t{current.get('kind', '')}\t{current.get('token', '')}\t{current.get('target', '')}"
        )
    if "remote" in result:
        print_remote_listing(result["remote"])
    for rel, mapping in sorted(state["files"].items()):
        print(
            f"tracked\t{rel}\t{mapping.get('file_token', '')}\t{mapping.get('identity', 'user')}"
        )
    return 0


def write_config_example(path: Path, overwrite: bool = False) -> None:
    if path.exists() and not overwrite:
        raise ToolError(
            f"config already exists: {path}; pass --overwrite to replace it"
        )
    content = {
        "version": 1,
        "identity": "user",
        "mappings": [
            {
                "name": "public-posts",
                "local_dir": "Post",
                "target_url": "https://example.feishu.cn/drive/folder/<folder_token>",
                "preserve_subdirs": True,
            }
        ],
    }
    write_text(path, json.dumps(content, ensure_ascii=False, indent=2) + "\n")


def init_config(args: argparse.Namespace) -> int:
    write_config_example(args.config, overwrite=args.overwrite)
    print(f"wrote: {args.config}")
    return 0


def plan_config(args: argparse.Namespace) -> int:
    root = args.root.resolve()
    plan = config_plan(root, load_config(args.config))
    for item in plan:
        print(
            f"{item['mapping']}\t{item['path']}\t{item['target_flag']} {item['target']}\t{item['remote_name']}"
        )
    if args.json:
        print(json.dumps(plan, ensure_ascii=False, indent=2))
    return 0


def add_common(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--root", type=Path, default=Path.cwd(), help="Vault root. Defaults to cwd."
    )
    parser.add_argument(
        "--state", type=Path, default=DEFAULT_STATE, help="Sync state JSON path."
    )
    parser.add_argument(
        "--apply", action="store_true", help="Execute writes. Default is dry-run."
    )


def add_config(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--config", type=Path, default=None, help="Directory mapping config JSON."
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog=os.environ.get("LARK_MD_SYNC_PROG"),
        description="Lark Markdown sync and read-only remote navigator for Agents.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""commands:
  cd <lark-url>        Set current remote target in local state; no remote write.
  ls                  Show current target meta, child nodes/files, and tracked mappings.
  track <md>          Bind a local Markdown file to an existing remote Markdown token.
  untrack [md...]     Remove local mappings only; never delete remote files.
  init-config         Create lark-md-sync.config.json example.
  plan-config         Preview files selected by directory mappings.
  status [md...]      Compare local/base/remote content.
  push [md...]        Push local Markdown to Lark; dry-run unless --apply.
  pull [md...]        Pull remote Markdown to local; dry-run unless --apply.
  sync [md...]        Bidirectional sync with merge/conflict policy; dry-run unless --apply.

examples:
  lark-sync cd 'https://bytedance.larkoffice.com/wiki/xxx'
  lark-sync ls
  lark-sync ls --json
  lark-sync status --config lark-md-sync.config.json
  lark-sync push --config lark-md-sync.config.json --apply
""",
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("cd", help="Set the current Lark target URL in local sync state.")
    p.add_argument("target")
    p.add_argument("--state", type=Path, default=DEFAULT_STATE)
    p.add_argument("--as", dest="identity", default="user", choices=["user", "bot"])

    p = sub.add_parser("track", help="Track an existing remote Markdown file.")
    add_common(p)
    p.add_argument("path")
    p.add_argument("--file-token", required=True)
    p.add_argument("--as", dest="identity", default="user", choices=["user", "bot"])
    p.add_argument("--name", default="")
    p.add_argument(
        "--pull-initial",
        action="store_true",
        help="Create local file from remote if missing.",
    )

    p = sub.add_parser(
        "untrack", help="Remove local mapping without deleting either side."
    )
    add_common(p)
    p.add_argument("paths", nargs="*")

    p = sub.add_parser("list", aliases=["ls"], help="List tracked mappings and current Lark target metadata.")
    p.add_argument("--root", type=Path, default=Path.cwd())
    p.add_argument("--state", type=Path, default=DEFAULT_STATE)
    p.add_argument("--page-size", type=int, default=50)
    p.add_argument("--json", action="store_true")
    p.add_argument("--no-remote", action="store_true", help="Only print local sync state; do not query Lark metadata.")

    p = sub.add_parser("init-config", help="Write an example directory mapping config.")
    p.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    p.add_argument("--overwrite", action="store_true")

    p = sub.add_parser(
        "plan-config", help="Preview files selected by a directory mapping config."
    )
    p.add_argument("--root", type=Path, default=Path.cwd())
    p.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    p.add_argument("--json", action="store_true")

    p = sub.add_parser("status", help="Compare local, base, and remote content.")
    p.add_argument("paths", nargs="*")
    p.add_argument("--root", type=Path, default=Path.cwd())
    p.add_argument("--state", type=Path, default=DEFAULT_STATE)
    add_config(p)
    p.add_argument("--json", action="store_true")

    p = sub.add_parser("push", help="Push local Markdown to Lark Markdown.")
    add_common(p)
    add_config(p)
    p.add_argument("paths", nargs="*")
    p.add_argument("--as", dest="identity", default="user", choices=["user", "bot"])
    p.add_argument("--folder-token", default="")
    p.add_argument("--wiki-token", default="")
    p.add_argument("--name", default="")

    p = sub.add_parser("pull", help="Pull remote Markdown to local Markdown.")
    add_common(p)
    add_config(p)
    p.add_argument("paths", nargs="*")
    p.add_argument(
        "--on-conflict",
        choices=["merge", "local-wins", "remote-wins", "abort"],
        default="merge",
    )

    p = sub.add_parser("sync", help="Bidirectionally sync local and remote Markdown.")
    add_common(p)
    add_config(p)
    p.add_argument("paths", nargs="*")
    p.add_argument(
        "--on-conflict",
        choices=["merge", "local-wins", "remote-wins", "abort"],
        default="merge",
    )

    args = parser.parse_args(argv)
    try:
        if args.cmd == "cd":
            return cd_cmd(args)
        if args.cmd == "track":
            return track(args)
        if args.cmd == "untrack":
            return untrack(args)
        if args.cmd in {"list", "ls"}:
            return list_cmd(args)
        if args.cmd == "init-config":
            return init_config(args)
        if args.cmd == "plan-config":
            return plan_config(args)
        if args.cmd == "status":
            return status_cmd(args)
        if args.cmd == "push":
            return push(args)
        if args.cmd == "pull":
            return pull_or_sync(args, sync_mode=False)
        if args.cmd == "sync":
            return pull_or_sync(args, sync_mode=True)
    except ToolError as exc:
        print(f"lark-md-sync: {exc}", file=sys.stderr)
        return 2
    raise AssertionError(args.cmd)


if __name__ == "__main__":
    raise SystemExit(main())
