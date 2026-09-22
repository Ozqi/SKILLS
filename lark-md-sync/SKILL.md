---
name: lark-md-sync
description: Bidirectionally sync local Markdown files with Lark/Feishu Drive native Markdown files. Use when asked to track, status-check, push, pull, or merge-sync vault Markdown with Feishu/Lark Markdown via sara-lark-cli, or to manage lark-md-sync.config.json and tmp/lark-md-sync state.
---

# Lark Markdown Sync

Use this skill for controlled sync between local `.md` files and Lark/Feishu Drive native Markdown files.

Bundled commands:

```bash
lark-sync -h
lark-sync cd 'https://bytedance.larkoffice.com/wiki/xxx'
lark-sync ls
```

## Model

- Config file: `lark-md-sync.config.json` maps local directories to Lark Drive folders or Wiki nodes.
- State file: `tmp/lark-md-sync/state.json` records local Markdown paths, remote file tokens, and an optional `current` Lark target set by `lark-sync cd`.
- Base cache: `tmp/lark-md-sync/base/` stores last-known common versions for three-way merge.
- Default mode is dry-run. Local or remote writes require `--apply`.
- `RAW/` paths are refused by the script.

## Prerequisites

- Run commands from the vault root unless `--root` is supplied.
- `sara-lark-cli` must be available in `PATH`, or set `SARA_LARK_CLI=/path/to/sara-lark-cli`.
- Use the correct identity: `--as user` by default, `--as bot` only when the bot owns the target.

## Common workflows

Set the current Lark target URL in local sync state:

```bash
lark-sync cd 'https://bytedance.larkoffice.com/wiki/xxx'
lark-sync ls
```

This does not change the shell working directory and does not touch remote content; it only records the current Lark target in `tmp/lark-md-sync/state.json`. `lark-sync ls` then behaves like a lightweight remote filesystem listing for Agents: it inspects the current Lark target, prints type/title/token/url metadata, and lists child wiki nodes or Drive folder entries when the target is a container.

Create an example config:

```bash
lark-sync init-config
```

Preview the files selected by a directory mapping:

```bash
lark-sync plan-config --config lark-md-sync.config.json
```

Track an existing remote Markdown file:

```bash
lark-sync track path/to/file.md \
  --file-token <file_token> \
  --as user
```

Create or update remote Markdown from local files:

```bash
lark-sync push --config lark-md-sync.config.json
lark-sync push --config lark-md-sync.config.json --apply
```

Check drift:

```bash
lark-sync status --config lark-md-sync.config.json
lark-sync ls
```

Pull remote changes into local files:

```bash
lark-sync pull --config lark-md-sync.config.json
lark-sync pull --config lark-md-sync.config.json --apply
```

Bidirectional sync with three-way merge:

```bash
lark-sync sync --config lark-md-sync.config.json
lark-sync sync --config lark-md-sync.config.json --apply
```

Conflict policy:

```bash
lark-sync sync --config lark-md-sync.config.json --on-conflict abort
lark-sync sync --config lark-md-sync.config.json --on-conflict remote-wins --apply
lark-sync sync --config lark-md-sync.config.json --on-conflict local-wins --apply
```

## Safety rules

1. Start with `cd`, `ls`, `status`, `plan-config`, or dry-run `push` / `pull` / `sync`.
2. Use `--apply` only after confirming the exact paths and direction.
3. When both sides changed, prefer `sync --on-conflict merge`; inspect conflict markers before pushing merged content.
4. Do not delete remote files from this workflow. `untrack` only removes local state.
5. Keep `tmp/lark-md-sync/` as generated sync state/cache; do not treat it as source content.
