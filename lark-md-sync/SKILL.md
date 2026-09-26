---
name: lark-md-sync
description: Bidirectionally sync local Markdown files with Lark/Feishu Drive native Markdown files. Use when asked to track, status-check, push, pull, merge-sync, or browse Lark remote metadata with lark-sync cd/ls.
---

# Lark Markdown Sync

Use `lark-sync -h` as the source of truth for commands and examples.

```bash
lark-sync -h
lark-sync cd 'https://bytedance.larkoffice.com/wiki/xxx'
lark-sync ls
```

Model: `tmp/lark-md-sync/state.json` stores tracked Markdown mappings, created Drive folder tokens, and the optional current Lark target. Local tracked `.md` files carry `lark_url` in frontmatter for easy inspection. With `preserve_subdirs: true`, `push --apply` mirrors local subdirectories as Drive folders. `tmp/lark-md-sync/base/` stores three-way merge bases. Default sync operations are dry-run; local or remote content writes require `--apply`.

Safety: `cd` / `ls` are for Agent-visible remote filesystem-like browsing only. They do not mount Lark, do not change shell cwd, and do not write remote content. `RAW/` paths are refused. Do not delete remote files from this workflow; `untrack` only removes local state.
