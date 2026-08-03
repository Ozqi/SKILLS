#!/usr/bin/env python3
"""Synchronize Codex, Claude Code, OpenCode, and skill rule files in one pass."""

from __future__ import annotations

import argparse
import filecmp
import os
import shutil
import sys
from dataclasses import dataclass
from pathlib import Path


GENERATED_MARKER = "<!-- generated-by: sync-agent-rules -->"
EXCLUDE_AGENT_SOURCES = {"notion-memory.md"}


@dataclass
class Finding:
    level: str
    path: str
    message: str


def rel(path: Path, root: Path) -> str:
    return path.relative_to(root).as_posix()


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def copy_file(src: Path, dst: Path) -> None:
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(src, dst)


def same_file(a: Path, b: Path) -> bool:
    return a.exists() and b.exists() and filecmp.cmp(a, b, shallow=False)


def newer(paths: list[Path]) -> Path:
    return max(paths, key=lambda item: item.stat().st_mtime_ns)


def find_root(path: Path) -> Path:
    path = path.resolve()
    if path.is_file():
        path = path.parent
    for item in [path, *path.parents]:
        if (item / ".git").exists():
            return item
    return Path.cwd().resolve()


def has_frontmatter(text: str) -> bool:
    return text.startswith("---\n") and "\n---\n" in text[4:]


def split_frontmatter(text: str) -> tuple[str | None, str]:
    if not has_frontmatter(text):
        return None, text
    end = text.find("\n---\n", 4)
    return text[: end + 5].rstrip() + "\n", text[end + 5 :].lstrip("\n")


def claude_wrapper(name: str, source: Path, existing: Path) -> str:
    source_s = source.as_posix()
    frontmatter = (
        "---\n"
        f"name: {name}\n"
        f"description: Follow shared agent rules from {source_s}.\n"
        "model: inherit\n"
        "---\n"
    )
    if existing.exists():
        parsed, _ = split_frontmatter(read_text(existing))
        if parsed:
            frontmatter = parsed
    return (
        frontmatter.rstrip()
        + "\n\n"
        + f"{GENERATED_MARKER}\n"
        + f"Read `{source_s}`, `AGENTS.md`, and `CLAUDE.md`, then follow the shared source of truth.\n"
    )


def opencode_wrapper(source: Path, existing: Path) -> str:
    source_s = source.as_posix()
    frontmatter = "---\n" f"description: Follow shared agent rules from {source_s}.\n" "mode: subagent\n" "---\n"
    if existing.exists():
        parsed, _ = split_frontmatter(read_text(existing))
        if parsed:
            frontmatter = parsed
    return (
        frontmatter.rstrip()
        + "\n\n"
        + f"{GENERATED_MARKER}\n"
        + f"Read `{source_s}`, `AGENTS.md`, and `CLAUDE.md`, then follow the shared source of truth.\n"
    )


def sync_group(root: Path, paths: list[Path], check: bool, findings: list[Finding]) -> None:
    existing = [root / path for path in paths if (root / path).exists()]
    if not existing:
        return
    src = newer(existing)
    for dst in [root / path for path in paths]:
        if dst == src:
            continue
        if dst.exists() and same_file(src, dst):
            continue
        if check:
            level = "drift" if dst.exists() else "missing"
            findings.append(Finding(level, rel(dst, root), f"would copy from {rel(src, root)}"))
            continue
        existed = dst.exists()
        copy_file(src, dst)
        action = "updated" if existed else "created"
        findings.append(Finding("synced", rel(dst, root), f"{action} from {rel(src, root)}"))


def skill_bases(root: Path) -> list[Path]:
    bases = [root / ".agents" / "skills", root / ".claude" / "skills"]
    opencode = root / ".opencode" / "skills"
    if opencode.exists():
        bases.append(opencode)
    return bases


def sync_skills(root: Path, check: bool, findings: list[Finding]) -> None:
    bases = skill_bases(root)
    subs: set[Path] = set()
    for base in bases:
        if not base.exists():
            continue
        for path in base.rglob("*"):
            if path.is_file():
                subs.add(path.relative_to(base))
    for sub in sorted(subs):
        sync_group(root, [base.relative_to(root) / sub for base in bases], check, findings)


def agent_sources(root: Path) -> list[Path]:
    base = root / ".agents"
    if not base.exists():
        return []
    return [path for path in sorted(base.glob("*.md")) if path.name not in EXCLUDE_AGENT_SOURCES]


def opencode_agent_dir(root: Path) -> Path | None:
    for sub in [Path(".opencode") / "agents", Path(".opencode") / "agent"]:
        path = root / sub
        if path.exists():
            return path
    return None


def sync_wrapper(root: Path, target: Path, content: str, check: bool, findings: list[Finding]) -> None:
    dst = root / target
    if dst.exists() and read_text(dst) == content:
        return
    if check:
        level = "drift" if dst.exists() else "missing"
        findings.append(Finding(level, target.as_posix(), "would regenerate wrapper"))
        return
    existed = dst.exists()
    write_text(dst, content)
    action = "updated" if existed else "created"
    findings.append(Finding("synced", target.as_posix(), f"{action} wrapper"))


def sync_agent_wrappers(root: Path, check: bool, findings: list[Finding]) -> None:
    opencode_dir = opencode_agent_dir(root)
    for source_abs in agent_sources(root):
        source = source_abs.relative_to(root)
        name = source_abs.stem
        claude_target = Path(".claude") / "agents" / f"{name}.md"
        sync_wrapper(root, claude_target, claude_wrapper(name, source, root / claude_target), check, findings)
        if opencode_dir:
            opencode_target = opencode_dir.relative_to(root) / f"{name}.md"
            sync_wrapper(root, opencode_target, opencode_wrapper(source, root / opencode_target), check, findings)


def run(args: argparse.Namespace) -> int:
    root = find_root(Path(args.root))
    findings: list[Finding] = []
    sync_group(root, [Path("AGENTS.md"), Path("CLAUDE.md")], args.check, findings)
    sync_skills(root, args.check, findings)
    sync_agent_wrappers(root, args.check, findings)

    if findings:
        for item in findings:
            print(f"{item.level}: {item.path} | {item.message}")
    else:
        print("agent rules sync ok")
    return 1 if args.check and any(item.level in {"drift", "missing"} for item in findings) else 0


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default=os.getcwd(), help="Repository root or path inside it.")
    parser.add_argument("--check", action="store_true", help="Check drift without writing files.")
    args = parser.parse_args(argv)
    try:
        return run(args)
    except Exception as exc:
        print(f"sync-agent-rules: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
