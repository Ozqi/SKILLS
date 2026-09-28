#!/usr/bin/env python3
"""本地 Markdown 目录与飞书在线文档的同步器。

同步模型：
1. `lark-md-sync.config.json` 只描述目录级映射：
   本地目录 `local_dir` <-> 飞书 Drive 文件夹 / Wiki 节点。
2. `tmp/lark-md-sync/state.json` 记录文件级映射：
   每个本地 `.md` <-> 一个飞书在线文档 docx/wiki URL。
3. `tmp/lark-md-sync/base/` 缓存上次两端一致的版本，用于三方 merge。

默认不写远端，也不改本地正文；只有显式传 `--apply` 才执行写入。
"""

from __future__ import annotations

SCRIPT_META = {
    "name": "lark_md_sync",
    "summary": "Bidirectionally sync local Markdown files with Lark/Feishu online docs.",
    "inputs": "CLI subcommands (cd|track|status|push|pull|sync|untrack|init-config|plan-config|list|ls), local Markdown paths, config mappings, Lark doc URLs/tokens or target folders, and a local state file.",
    "outputs": "stdout plan/status plus local state, cached base files, and optional local/remote Markdown writes.",
    "writes": "tmp/lark-md-sync/** by default; local Markdown lark_url metadata on track/push --apply; local Markdown files on pull/sync --apply; remote Lark docs on push/sync --apply.",
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
LARK_META_FIELDS = {"lark_url"}
STATE_VERSION = 1
LARK_CLI = os.environ.get("LARK_CLI", "lark-cli")


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


def split_frontmatter(text: str) -> tuple[list[str], str] | None:
    if not text.startswith("---\n"):
        return None
    end = text.find("\n---\n", 4)
    if end == -1:
        return None
    return text[4:end].splitlines(), text[end + 5 :]


def strip_lark_meta(text: str) -> str:
    parsed = split_frontmatter(text)
    if parsed is None:
        return text
    lines, body = parsed
    kept = [line for line in lines if line.split(":", 1)[0].strip() not in LARK_META_FIELDS]
    if not kept:
        return body
    return "---\n" + "\n".join(kept).rstrip() + "\n---\n" + body


def quote_yaml(value: str) -> str:
    return json.dumps(value, ensure_ascii=False)


def with_lark_meta(text: str, mapping: dict[str, Any]) -> str:
    token = str(mapping.get("file_token") or "")
    url = str(mapping.get("url") or "") or (f"https://www.feishu.cn/docx/{token}" if token else "")
    fields = {"lark_url": url}
    parsed = split_frontmatter(text)
    if parsed is None:
        lines, body = [], text
    else:
        lines, body = parsed
    kept = [line for line in lines if line.split(":", 1)[0].strip() not in LARK_META_FIELDS]
    added = [f"{key}: {quote_yaml(value)}" for key, value in fields.items() if value]
    return "---\n" + "\n".join([*kept, *added]).rstrip() + "\n---\n" + body


def write_local_with_lark_meta(path: Path, text: str, mapping: dict[str, Any]) -> None:
    write_text(path, with_lark_meta(text, mapping))


def lark_token(text: str) -> str:
    parsed = split_frontmatter(text)
    if parsed is None:
        return ""
    lines, _ = parsed
    for line in lines:
        if line.split(":", 1)[0].strip() != "lark_url" or ":" not in line:
            continue
        value = line.split(":", 1)[1].strip().strip('"\'')
        parts = [part for part in urlparse(value).path.split("/") if part]
        return parts[-1] if parts else ""
    return ""


def structural_plan(
    previous: dict[str, dict[str, str]],
    local: dict[str, str],
    remote: dict[str, str],
    new_local: list[str],
) -> list[dict[str, str]]:
    """Return structural actions; token is identity and path is mutable state."""
    actions = [{"action": "create_remote", "to": path} for path in sorted(new_local)]
    for token in sorted(set(previous) | set(local) | set(remote)):
        old = previous.get(token, {})
        old_local = old.get("local_path", "")
        old_remote = old.get("remote_path", "")
        local_path = local.get(token, "")
        remote_path = remote.get(token, "")

        if not old:
            if local_path and not remote_path:
                actions.append({"action": "conflict", "token": token, "reason": "local-token-not-found-remotely"})
            elif remote_path and not local_path:
                actions.append({"action": "pull_remote", "token": token, "to": remote_path})
            elif local_path and remote_path:
                if local_path == remote_path:
                    actions.append({"action": "adopt", "token": token, "to": local_path})
                else:
                    actions.append({"action": "conflict", "token": token, "reason": "untracked-path-mismatch"})
            continue
        if not local_path and not remote_path:
            actions.append({"action": "forget", "token": token})
            continue
        if not local_path:
            if remote_path == old_remote:
                actions.append({"action": "delete_remote", "token": token, "from": remote_path})
            else:
                actions.append({"action": "conflict", "token": token, "reason": "local-delete-vs-remote-move"})
            continue
        if not remote_path:
            if local_path == old_local:
                actions.append({"action": "delete_local", "token": token, "from": local_path})
            else:
                actions.append({"action": "conflict", "token": token, "reason": "remote-delete-vs-local-move"})
            continue

        local_moved = local_path != old_local
        remote_moved = remote_path != old_remote
        if local_moved and remote_moved:
            if local_path == remote_path:
                actions.append({"action": "repath", "token": token, "to": local_path})
            else:
                actions.append({"action": "conflict", "token": token, "reason": "both-moved"})
        elif local_moved:
            actions.append({"action": "move_remote", "token": token, "from": remote_path, "to": local_path})
        elif remote_moved:
            actions.append({"action": "move_local", "token": token, "from": local_path, "to": remote_path})
    return actions


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
        return {"version": STATE_VERSION, "files": {}, "folders": {}}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ToolError(f"invalid state JSON: {path}: {exc.msg}") from exc
    if not isinstance(data, dict):
        raise ToolError(f"state must be a JSON object: {path}")
    data.setdefault("version", STATE_VERSION)
    data.setdefault("files", {})
    data.setdefault("folders", {})
    if not isinstance(data["files"], dict):
        raise ToolError(f"state.files must be an object: {path}")
    if not isinstance(data["folders"], dict):
        raise ToolError(f"state.folders must be an object: {path}")
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
    mapping["base_sha256"] = cache_base(root, strip_lark_meta(content))
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
        for key in ("file_token", "fileToken", "document_id", "token", "obj_token", "objToken"):
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


def config_specs(root: Path, config: dict[str, Any]) -> list[dict[str, Any]]:
    specs: list[dict[str, Any]] = []
    for index, item in enumerate(config["mappings"]):
        if not isinstance(item, dict):
            raise ToolError(f"config mapping must be an object at index {index}")
        local_dir = resolve_dir_rel(root, str(item.get("local_dir") or ""))
        identity = str(item.get("identity") or config.get("identity") or "user")
        if identity not in {"user", "bot"}:
            raise ToolError(f"invalid identity in config: {identity}")
        if item.get("wiki_token"):
            target_flag, target = "--wiki-token", str(item["wiki_token"])
        elif item.get("folder_token"):
            target_flag, target = "--folder-token", str(item["folder_token"])
        elif item.get("target_url"):
            target_flag, target = "--folder-token", str(item["target_url"])
        else:
            raise ToolError("each mapping requires folder_token, wiki_token, or target_url")
        specs.append(
            {
                "mapping": str(item.get("name") or f"mapping-{index + 1}"),
                "local_dir": local_dir,
                "identity": identity,
                "target_flag": target_flag,
                "target": target,
                "preserve_subdirs": bool(item.get("preserve_subdirs", False)),
            }
        )
    return specs


def config_plan(root: Path, config: dict[str, Any]) -> list[dict[str, str]]:
    """把目录级配置展开为具体 Markdown 文件的同步计划。"""
    plan: list[dict[str, str]] = []
    for spec in config_specs(root, config):
        local_dir = str(spec["local_dir"])
        identity = str(spec["identity"])
        target_flag = str(spec["target_flag"])
        target = str(spec["target"])
        mapping = str(spec["mapping"])
        for rel in iter_markdown_under(root, local_dir):
            name = Path(rel).name
            subdir = ""
            if bool(spec["preserve_subdirs"]):
                prefix = "" if local_dir == "." else local_dir.rstrip("/") + "/"
                subdir = str(Path(rel.removeprefix(prefix)).parent)
                if subdir == ".":
                    subdir = ""
                if subdir and target_flag == "--wiki-token":
                    raise ToolError("preserve_subdirs requires a Drive folder target, not wiki_token")
            plan.append(
                {
                    "mapping": mapping,
                    "path": rel,
                    "identity": identity,
                    "target": target,
                    "target_flag": target_flag,
                    "remote_name": name,
                    "subdir": subdir,
                }
            )
    return plan


def fetch_remote(root: Path, rel: str, mapping: dict[str, Any]) -> str:
    """Fetch a Lark doc as Markdown content."""
    token = mapping.get("file_token")
    if not isinstance(token, str) or not token:
        raise ToolError(f"missing file_token in state for {rel}")
    identity = str(mapping.get("identity") or "user")
    data = lark_data(
        [
            LARK_CLI,
            "docs",
            "+fetch",
            "--as",
            identity,
            "--doc",
            str(mapping.get("url") or token),
            "--doc-format",
            "markdown",
            "--format",
            "json",
        ],
        root,
    )
    document = data.get("document") if isinstance(data, dict) else {}
    if not isinstance(document, dict) or not isinstance(document.get("content"), str):
        raise ToolError("could not read Markdown content from docs +fetch response")
    return document["content"]


def create_remote(
    root: Path,
    rel: str,
    identity: str,
    name: str,
    apply: bool,
    target: list[str],
) -> str:
    """Create a Lark doc from local Markdown; dry-run only prints command."""
    cmd = [
        LARK_CLI,
        "docs",
        "+create",
        "--as",
        identity,
        "--doc-format",
        "markdown",
        "--title",
        Path(name).stem,
        "--content",
        "@" + rel,
        "--format",
        "json",
    ]
    if len(target) == 2:
        cmd.extend(["--parent-token", folder_token(target[1])])
    if not apply:
        print("DRY-RUN create:", " ".join(cmd))
        return ""
    data = lark_data(cmd, root)
    token = find_token(data)
    if not token:
        raise ToolError("could not find document token in create response")
    return token


def folder_token(value: str) -> str:
    parsed = urlparse(value)
    parts = [part for part in parsed.path.split("/") if part]
    if "folder" in parts:
        index = parts.index("folder")
        if index + 1 < len(parts):
            return parts[index + 1]
    return value


def create_folder(root: Path, parent: str, name: str, identity: str, apply: bool) -> str:
    cmd = [
        LARK_CLI,
        "drive",
        "+create-folder",
        "--name",
        name,
        "--as",
        identity,
        "--format",
        "json",
    ]
    if parent:
        cmd.extend(["--folder-token", folder_token(parent)])
    if not apply:
        print("DRY-RUN mkdir:", " ".join(cmd))
        return ""
    data = lark_data(cmd, root)
    token = find_token(data)
    if not token:
        raise ToolError("could not find folder token in create-folder response")
    return token


def ensure_remote_subdir(root: Path, state: dict[str, Any], item: dict[str, str], apply: bool) -> list[str]:
    subdir = item.get("subdir", "")
    if not subdir:
        return [item["target_flag"], item["target"]]
    parent = item["target"]
    prefix = f"{item['mapping']}:{folder_token(parent)}"
    for part in Path(subdir).parts:
        key = f"{prefix}/{part}"
        token = state["folders"].get(key)
        if not token:
            token = create_folder(root, parent, part, item["identity"], apply)
            if apply:
                state["folders"][key] = token
        parent = token or f"<folder:{key}>"
        prefix = key
    return ["--folder-token", parent]


def move_remote(root: Path, token: str, folder: str, identity: str) -> None:
    lark_data(
        [
            LARK_CLI,
            "drive",
            "+move",
            "--file-token",
            token,
            "--type",
            "docx",
            "--folder-token",
            folder_token(folder),
            "--as",
            identity,
            "--format",
            "json",
        ],
        root,
    )


def rename_remote(root: Path, token: str, name: str, identity: str) -> None:
    lark_data(
        [
            LARK_CLI,
            "drive",
            "files",
            "patch",
            "--file-token",
            token,
            "--type",
            "docx",
            "--data",
            json.dumps({"new_title": name}, ensure_ascii=False),
            "--as",
            identity,
            "--format",
            "json",
        ],
        root,
    )


def delete_remote(root: Path, token: str, identity: str) -> None:
    lark_data(
        [
            LARK_CLI,
            "drive",
            "+delete",
            "--file-token",
            token,
            "--type",
            "docx",
            "--as",
            identity,
            "--format",
            "json",
            "--yes",
        ],
        root,
    )


def overwrite_remote(
    root: Path, rel: str, mapping: dict[str, Any], file_rel: str, apply: bool
) -> None:
    """Overwrite a Lark doc with local Markdown."""
    token = mapping.get("file_token")
    if not isinstance(token, str) or not token:
        raise ToolError(f"missing file_token in state for {rel}")
    identity = str(mapping.get("identity") or "user")
    cmd = [
        LARK_CLI,
        "docs",
        "+update",
        "--as",
        identity,
        "--doc",
        str(mapping.get("url") or token),
        "--command",
        "overwrite",
        "--doc-format",
        "markdown",
        "--content",
        "@" + (root / file_rel).resolve().relative_to(root.resolve()).as_posix(),
        "--format",
        "json",
    ]
    if not apply:
        print("DRY-RUN overwrite:", " ".join(cmd))
        return
    lark_data(cmd, root)


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
    local_sha = sha256_text(strip_lark_meta(local_content)) if local_exists else ""
    remote_content = fetch_remote(root, rel, mapping)
    remote_sha = sha256_text(strip_lark_meta(remote_content))
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
            write_local_with_lark_meta(local_path, remote, mapping)
        else:
            print(f"DRY-RUN would create local file from remote: {rel}")
    elif strip_lark_meta(read_text(local_path)) != strip_lark_meta(remote):
        print(f"{rel}: local and remote differ; using remote as initial base")
    update_mapping_base(root, mapping, remote)
    if args.apply:
        if local_path.exists():
            write_local_with_lark_meta(local_path, read_text(local_path), mapping)
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
                target = ensure_remote_subdir(root, state, item, args.apply)
                if args.apply and item.get("subdir"):
                    save_state(args.state, state)
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
                relative = (
                    str(Path(item["subdir"]) / item["remote_name"])
                    if item.get("subdir")
                    else item["remote_name"]
                )
                mapping = {
                    "file_token": token,
                    "identity": item["identity"],
                    "name": item["remote_name"],
                    "mapping": item.get("mapping", ""),
                    "relative_path": relative,
                    "remote_path": relative,
                    "tracked_at": now_iso(),
                }
                update_mapping_base(root, mapping, local)
                write_local_with_lark_meta(root / rel, local, mapping)
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
            write_local_with_lark_meta(root / rel, local, mapping)
            save_state(args.state, state)
            print(f"pushed: {rel}")
    if args.apply:
        save_state(args.state, state)
    return 0


def safe_relative_path(value: str) -> str:
    path = Path(value)
    if path.is_absolute() or ".." in path.parts:
        raise ToolError(f"unsafe relative path from Lark: {value}")
    return path.as_posix()


def state_entry_by_token(
    state: dict[str, Any], token: str
) -> tuple[str, dict[str, Any]] | tuple[None, None]:
    for local_path, mapping in state["files"].items():
        if mapping.get("file_token") == token:
            return local_path, mapping
    return None, None


def state_mapping(
    state: dict[str, Any], spec: dict[str, Any], token: str, relative_path: str
) -> tuple[str, dict[str, Any]]:
    old_key, existing = state_entry_by_token(state, token)
    local_path = mapping_local_path(spec, safe_relative_path(relative_path))
    mapping = existing or {
        "file_token": token,
        "identity": spec["identity"],
        "tracked_at": now_iso(),
    }
    if old_key and old_key != local_path:
        state["files"].pop(old_key, None)
    mapping.update(
        {
            "mapping": spec["mapping"],
            "relative_path": safe_relative_path(relative_path),
            "remote_path": safe_relative_path(relative_path),
            "name": Path(relative_path).name,
        }
    )
    mapping.pop("pending_remote_path", None)
    state["files"][local_path] = mapping
    return local_path, mapping


def target_folder_for_path(
    root: Path,
    state: dict[str, Any],
    spec: dict[str, Any],
    relative_path: str,
) -> str:
    parent = Path(safe_relative_path(relative_path)).parent.as_posix()
    if parent == ".":
        return folder_token(str(spec["target"]))
    item = {
        "mapping": str(spec["mapping"]),
        "target_flag": str(spec["target_flag"]),
        "target": str(spec["target"]),
        "identity": str(spec["identity"]),
        "subdir": parent,
    }
    return folder_token(ensure_remote_subdir(root, state, item, True)[1])


def apply_structural_actions(
    root: Path,
    state_path: Path,
    state: dict[str, Any],
    config: dict[str, Any],
    actions: list[dict[str, str]],
    allow_delete: bool,
) -> None:
    specs = {str(item["mapping"]): item for item in config_specs(root, config)}
    conflicts = [item for item in actions if item["action"] == "conflict"]
    if conflicts:
        raise ToolError("structural conflicts must be resolved before sync")
    deletes = [item for item in actions if item["action"].startswith("delete_")]
    if deletes and not allow_delete:
        raise ToolError("structural deletes require --delete together with --apply")
    move_local_sources = {
        str(state_entry_by_token(state, item["token"])[0])
        for item in actions
        if item["action"] == "move_local" and state_entry_by_token(state, item["token"])[0]
    }
    for action in actions:
        kind = action["action"]
        token = action.get("token", "")
        spec = specs[action["mapping"]]
        if kind == "adopt":
            relative = safe_relative_path(action["to"])
            local_path = mapping_local_path(spec, relative)
            _, existing = state_entry_by_token(state, token)
            mapping = existing or {
                "file_token": token,
                "identity": spec["identity"],
                "name": Path(relative).name,
            }
            remote = fetch_remote(root, local_path, mapping)
            if strip_lark_meta(read_text(root / local_path)) != strip_lark_meta(remote):
                raise ToolError(f"refusing to adopt different local and remote content: {local_path}")
        elif kind in {"pull_remote", "move_local"}:
            destination = root / mapping_local_path(spec, safe_relative_path(action["to"]))
            old_key, _ = state_entry_by_token(state, token)
            destination_rel = destination.relative_to(root).as_posix()
            if destination.exists() and destination_rel not in move_local_sources:
                if not old_key or destination != root / old_key:
                    raise ToolError(f"refusing to overwrite local path: {destination_rel}")
        elif kind == "create_remote":
            local_path = root / mapping_local_path(spec, safe_relative_path(action["to"]))
            if not local_path.exists():
                raise ToolError(f"local file disappeared before sync: {local_path.relative_to(root)}")

    for action in deletes:
        token = action["token"]
        old_key, mapping = state_entry_by_token(state, token)
        if not old_key or mapping is None:
            continue
        if action["action"] == "delete_remote":
            if file_status(root, old_key, mapping)["remote_changed"]:
                raise ToolError(f"refusing to delete remotely modified file: {old_key}")
        elif action["action"] == "delete_local" and (root / old_key).exists():
            local_sha = sha256_text(strip_lark_meta(read_text(root / old_key)))
            if local_sha != mapping.get("base_sha256"):
                raise ToolError(f"refusing to delete locally modified file: {old_key}")

    for action in actions:
        if action["action"] == "move_remote":
            spec = specs[action["mapping"]]
            _, mapping = state_entry_by_token(state, action["token"])
            if mapping is not None:
                mapping["pending_remote_path"] = safe_relative_path(action["to"])
                save_state(state_path, state)
            rename_remote(
                root,
                action["token"],
                staged_remote_name(action["token"]),
                str(spec["identity"]),
            )

    ordered_actions = sorted(
        actions,
        key=lambda item: (
            2 if item["action"] == "delete_local" else 1 if item["action"] == "move_local" else 0
        ),
    )
    staged_moves: dict[str, Path] = {}
    staged_mappings: dict[str, dict[str, Any]] = {}
    moves_staged = False

    for action in ordered_actions:
        kind = action["action"]
        if kind == "move_local" and not moves_staged:
            for pending in ordered_actions:
                if pending["action"] != "move_local":
                    continue
                old_key, mapping = state_entry_by_token(state, pending["token"])
                if not old_key or mapping is None:
                    continue
                temporary = root / MERGE_DIR / f"{safe_name(pending['token'])}.move"
                temporary.parent.mkdir(parents=True, exist_ok=True)
                (root / old_key).rename(temporary)
                staged_moves[pending["token"]] = temporary
                staged_mappings[pending["token"]] = mapping
                state["files"].pop(old_key, None)
            moves_staged = True
        spec = specs[action["mapping"]]
        token = action.get("token", "")
        if kind == "create_remote":
            relative = safe_relative_path(action["to"])
            local_path = mapping_local_path(spec, relative)
            folder = target_folder_for_path(root, state, spec, relative)
            token = create_remote(
                root,
                local_path,
                str(spec["identity"]),
                Path(relative).name,
                True,
                ["--folder-token", folder],
            )
            _, mapping = state_mapping(state, spec, token, relative)
            local = read_text(root / local_path)
            update_mapping_base(root, mapping, local)
            write_local_with_lark_meta(root / local_path, local, mapping)
        elif kind in {"pull_remote", "adopt"}:
            relative = safe_relative_path(action["to"])
            local_path, mapping = state_mapping(state, spec, token, relative)
            remote = fetch_remote(root, local_path, mapping)
            if kind == "pull_remote":
                write_local_with_lark_meta(root / local_path, remote, mapping)
            elif (root / local_path).exists():
                write_local_with_lark_meta(root / local_path, read_text(root / local_path), mapping)
            update_mapping_base(root, mapping, remote)
        elif kind == "repath":
            state_mapping(state, spec, token, safe_relative_path(action["to"]))
        elif kind == "finish_remote_move":
            relative = safe_relative_path(action["to"])
            if Path(relative).parent.as_posix() != ".":
                folder = target_folder_for_path(root, state, spec, relative)
                move_remote(root, token, folder, str(spec["identity"]))
            rename_remote(root, token, Path(relative).name, str(spec["identity"]))
            state_mapping(state, spec, token, relative)
        elif kind == "move_remote":
            relative = safe_relative_path(action["to"])
            if Path(action["from"]).parent != Path(relative).parent:
                folder = target_folder_for_path(root, state, spec, relative)
                move_remote(root, token, folder, str(spec["identity"]))
            rename_remote(root, token, Path(relative).name, str(spec["identity"]))
            state_mapping(state, spec, token, relative)
        elif kind == "move_local":
            mapping = staged_mappings.get(token)
            source = staged_moves.get(token)
            if mapping is None or source is None:
                raise ToolError(f"missing local state for remote move: {token}")
            relative = safe_relative_path(action["to"])
            new_key = mapping_local_path(spec, relative)
            destination = root / new_key
            destination.parent.mkdir(parents=True, exist_ok=True)
            source.rename(destination)
            mapping.update(
                {
                    "mapping": spec["mapping"],
                    "relative_path": relative,
                    "remote_path": relative,
                    "name": Path(relative).name,
                }
            )
            state["files"][new_key] = mapping
        elif kind == "delete_remote":
            delete_remote(root, token, str(spec["identity"]))
            old_key, _ = state_entry_by_token(state, token)
            if old_key:
                state["files"].pop(old_key, None)
        elif kind == "delete_local":
            old_key, _ = state_entry_by_token(state, token)
            if old_key and (root / old_key).exists():
                (root / old_key).unlink()
            if old_key:
                state["files"].pop(old_key, None)
        elif kind == "forget":
            old_key, _ = state_entry_by_token(state, token)
            if old_key:
                state["files"].pop(old_key, None)
        save_state(state_path, state)


def pull_or_sync(args: argparse.Namespace, sync_mode: bool) -> int:
    """pull 只更新本地；sync 会在本地变更时推送远端。"""
    root = args.root.resolve()
    state = load_state(args.state)
    if sync_mode and args.config:
        config = load_config(args.config)
        actions = structural_plan_for_config(root, config, state)
        for action in actions:
            print("STRUCTURE", json.dumps(action, ensure_ascii=False))
        if any(action["action"] == "conflict" for action in actions):
            raise ToolError("structural conflicts must be resolved before sync")
        if actions and not args.apply:
            return 0
        if actions:
            apply_structural_actions(root, args.state, state, config, actions, args.delete)
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
                write_local_with_lark_meta(local_path, remote, mapping)
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
                    write_local_with_lark_meta(local_path, local, mapping)
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
                write_local_with_lark_meta(local_path, remote, mapping)
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
                write_local_with_lark_meta(local_path, local, mapping)
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
        write_local_with_lark_meta(local_path, merged, mapping)
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
            LARK_CLI,
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
            LARK_CLI,
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
            LARK_CLI,
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
            LARK_CLI,
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


def remote_markdown_tree(
    root: Path,
    folder: str,
    identity: str,
    prefix: str = "",
    folders: dict[str, str] | None = None,
    folder_key_prefix: str = "",
) -> dict[str, dict[str, str]]:
    data = lark_data(
        [
            LARK_CLI,
            "drive",
            "files",
            "list",
            "--folder-token",
            folder_token(folder),
            "--page-all",
            "--page-limit",
            "0",
            "--as",
            identity,
            "--format",
            "json",
        ],
        root,
    )
    result: dict[str, dict[str, str]] = {}
    for item in data_items(data):
        if not isinstance(item, dict):
            continue
        name = str(item.get("name") or "")
        token = str(item.get("token") or "")
        kind = str(item.get("type") or "")
        path = f"{prefix}/{name}" if prefix else name
        if kind == "folder":
            if folders is not None and folder_key_prefix:
                folders[f"{folder_key_prefix}/{path}"] = token
            result.update(
                remote_markdown_tree(
                    root,
                    token,
                    identity,
                    path,
                    folders,
                    folder_key_prefix,
                )
            )
        elif kind in {"docx", "file"} and token:
            if kind == "file" and not name.endswith(".md"):
                continue
            file_name = name if name.endswith(".md") else f"{name}.md"
            file_path = f"{prefix}/{file_name}" if prefix else file_name
            result[token] = {"remote_path": file_path, "type": kind, "url": str(item.get("url") or "")}
    return result


def mapping_local_path(spec: dict[str, Any], relative_path: str) -> str:
    local_dir = str(spec["local_dir"])
    return relative_path if local_dir == "." else f"{local_dir.rstrip('/')}/{relative_path}"


def local_markdown_tree(
    root: Path, spec: dict[str, Any]
) -> tuple[dict[str, str], list[str]]:
    tracked: dict[str, str] = {}
    new_local: list[str] = []
    local_dir = str(spec["local_dir"])
    prefix = "" if local_dir == "." else local_dir.rstrip("/") + "/"
    for rel in iter_markdown_under(root, local_dir):
        token = lark_token(read_text(root / rel))
        path = rel.removeprefix(prefix)
        if token:
            if token in tracked:
                raise ToolError(f"duplicate lark_url token in local files: {token}")
            tracked[token] = path
        else:
            new_local.append(path)
    return tracked, new_local


def previous_tree(
    state: dict[str, Any], spec: dict[str, Any]
) -> dict[str, dict[str, str]]:
    result: dict[str, dict[str, str]] = {}
    local_dir = str(spec["local_dir"])
    prefix = "" if local_dir == "." else local_dir.rstrip("/") + "/"
    for local_path, mapping in state["files"].items():
        mapping_name = str(mapping.get("mapping") or "")
        if mapping_name and mapping_name != spec["mapping"]:
            continue
        if not mapping_name and prefix and not local_path.startswith(prefix):
            continue
        token = str(mapping.get("file_token") or "")
        if token:
            relative = str(mapping.get("relative_path") or local_path.removeprefix(prefix))
            result[token] = {
                "local_path": relative,
                "remote_path": str(mapping.get("remote_path") or relative),
                "pending_remote_path": str(mapping.get("pending_remote_path") or ""),
            }
    return result


def staged_remote_name(token: str) -> str:
    return f".lark-sync-{token}.tmp.md"


def recover_staged_remote_actions(
    previous: dict[str, dict[str, str]], remote: dict[str, str]
) -> tuple[list[dict[str, str]], set[str]]:
    actions: list[dict[str, str]] = []
    staged: set[str] = set()
    for token, path in list(remote.items()):
        if Path(path).name != staged_remote_name(token) or token not in previous:
            continue
        target = previous[token].get("pending_remote_path", "")
        if target:
            actions.append({"action": "finish_remote_move", "token": token, "to": target})
            staged.add(token)
        else:
            old_name = Path(previous[token]["remote_path"]).name
            parent = Path(path).parent
            remote[token] = old_name if parent.as_posix() == "." else (parent / old_name).as_posix()
    return actions, staged


def structural_plan_for_config(
    root: Path, config: dict[str, Any], state: dict[str, Any]
) -> list[dict[str, str]]:
    actions: list[dict[str, str]] = []
    for spec in config_specs(root, config):
        if spec["target_flag"] != "--folder-token":
            raise ToolError("structural sync requires Drive folder targets")
        local, new_local = local_markdown_tree(root, spec)
        folder_prefix = f"{spec['mapping']}:{folder_token(str(spec['target']))}"
        remote = {
            token: item["remote_path"]
            for token, item in remote_markdown_tree(
                root,
                str(spec["target"]),
                str(spec["identity"]),
                folders=state["folders"],
                folder_key_prefix=folder_prefix,
            ).items()
        }
        previous = previous_tree(state, spec)
        recovery, staged_tokens = recover_staged_remote_actions(previous, remote)
        for action in recovery:
            actions.append({**action, "mapping": str(spec["mapping"])})
        remote_by_path: dict[str, str] = {}
        for token, path in remote.items():
            if path in remote_by_path:
                raise ToolError(f"duplicate remote Markdown path: {path}")
            remote_by_path[path] = token
        unmatched: list[str] = []
        for path in new_local:
            token = remote_by_path.get(path)
            if token:
                local[token] = path
            else:
                unmatched.append(path)
        for action in structural_plan(previous, local, remote, unmatched):
            actions.append({**action, "mapping": str(spec["mapping"])})
    return actions


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
        subdir = item.get("subdir") or "."
        print(
            f"{item['mapping']}\t{item['path']}\t{item['target_flag']} {item['target']}\t{subdir}\t{item['remote_name']}"
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
        description="Sync local Markdown with Lark online docs and browse remote metadata.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""commands:
  cd <lark-url>        Set current remote target in local state; no remote write.
  ls                  Show current target meta, child nodes/files, and tracked mappings.
  track <md>          Bind local Markdown to a remote token; writes lark_url with --apply.
  untrack [md...]     Remove local mappings only; never delete remote files.
  init-config         Create lark-md-sync.config.json example.
  plan-config         Preview files selected by directory mappings.
  status [md...]      Compare local/base/remote content.
  push [md...]        Push local Markdown; preserve_subdirs creates Drive folders with --apply.
  pull [md...]        Pull remote Markdown to local; dry-run unless --apply.
  sync [md...]        Bidirectional content + move/rename/delete sync; deletes need --apply --delete.

examples:
  lark-sync cd 'https://bytedance.larkoffice.com/wiki/xxx'
  lark-sync ls
  lark-sync ls --json
  lark-sync status --config lark-md-sync.config.json
  lark-sync sync --config lark-md-sync.config.json
  lark-sync sync --config lark-md-sync.config.json --apply --delete
""",
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("cd", help="Set the current Lark target URL in local sync state.")
    p.add_argument("target")
    p.add_argument("--state", type=Path, default=DEFAULT_STATE)
    p.add_argument("--as", dest="identity", default="user", choices=["user", "bot"])

    p = sub.add_parser("track", help="Track remote Markdown and write lark_url with --apply.")
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

    p = sub.add_parser("push", help="Push local Markdown to Lark docs.")
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
    p.add_argument(
        "--delete",
        action="store_true",
        help="Allow structural deletions; only valid with --apply.",
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
