---
name: lark-md-sync
description: Bidirectionally sync local Markdown files with Lark/Feishu online docs. Use when asked to track, status-check, push, pull, merge-sync, or browse Lark remote metadata with lark-sync cd/ls.
---

# Lark Markdown Sync

Use `lark-sync -h` as the source of truth for commands and examples.

```bash
lark-sync -h
lark-sync cd 'https://bytedance.larkoffice.com/wiki/xxx'
lark-sync ls
```

## Model and safety

- `tmp/lark-md-sync/state.json` stores tracked mappings, remote folder tokens, previous paths, and the optional current Lark target.
- Local tracked `.md` files carry `lark_url` in frontmatter. With `preserve_subdirs: true`, remote folders mirror local subdirectories.
- Operations are dry-run by default. Content/structure writes require `--apply`; structural deletion additionally requires `--delete`.
- Remote content overwrite is disabled by default for existing docs. Use `push --write-mode overwrite --apply` or `sync --write-mode overwrite --apply` only when you accept that Lark `docs +update --command overwrite` may drop or detach comments, images, attachments, and rich blocks.
- `cd` / `ls` only provide an Agent-visible remote filesystem-like view. They do not mount Lark or change shell cwd.
- `RAW/` paths are refused. `untrack` only removes local state.

## Format boundary

Lark Markdown import/export preserves content structure, not every visual detail. Treat the following as reliable enough for round-trip: headings, paragraphs, emphasis, basic nested lists, quotes, fenced code, dividers, basic GFM tables, links, network images, and basic formulas. Lark may normalize whitespace, list markers, code fence length/language casing, and document-title/H1 representation.

Lark-only rich blocks may remain as DocxXML fragments or lose presentation in Markdown: callouts, Todo block attributes, columns, whiteboards, embedded Sheets/Base, mentions (`<cite>`), attachments, buttons/reminders, colors/backgrounds, underline/alignment, synced blocks, comments, and review history. Preserve residual XML instead of silently dropping it.

Obsidian-only syntax is not native Lark Markdown: `[[wikilink]]`, `![[embed]]`, `> [!callout]`, `==highlight==`, `%%comment%%`, block IDs, YAML frontmatter, and local attachment paths. Do not claim these are lossless. Warn or apply an explicit downgrade; never guess missing URLs or upload local assets implicitly.

## Normalization behavior

The CLI uses a small deterministic Markdown view for comparison and uploads:

1. Upload body content without YAML frontmatter; `lark_url` stays local-only.
2. Remove the first H1 from the upload view only when it exactly equals frontmatter `title`, avoiding duplicate titles.
3. On pull and remote-wins, preserve existing local frontmatter and replace only the body.
4. Content comparison ignores local frontmatter and an exact duplicate title H1 / remote title H1, but must not ignore list depth, code contents, table cells, links, formulas, or residual XML.
5. Keep Lark-exported escaping (`\\`, `\[`, `\|`, and similar) unchanged.
6. Warn for local images/embeds, callouts, highlights, comments, and unsupported rich blocks.
7. Do not downgrade `[[Page|Text]]` to guessed URLs unless a verified mapping exists.
