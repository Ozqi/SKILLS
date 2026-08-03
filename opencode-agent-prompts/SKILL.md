---
name: opencode-agent-prompts
description: Study OpenCode source prompts that control agent behavior, work modes, tool use, and terminal response style. Use when extracting, comparing, or adapting OpenCode prompt constraints into other agent rules or skills.
---

# OpenCode Agent Prompts

Use this skill when the task is to learn from OpenCode's agent behavior prompts, not to analyze OpenCode implementation logic.

## Source

Local source snapshot:

- `RAW/repos/opencode/`
- upstream: `https://github.com/anomalyco/opencode`
- ref: `1882c33827cf0ce5c948b69ab5a87ed8f6790cf8`
- package version observed: `1.18.11`

Read `references/opencode-prompt-map.md` first for the prompt source map and reusable constraints.

## Focus

- Main system prompts that shape coding-agent behavior.
- Model-specific prompt variants and output style constraints.
- Built-in agent prompts for exploration, compaction, title generation, summaries, and generated agents.
- Plan/build mode reminders and permission boundaries.
- Tool prompt text, especially shell/git behavior.
- Project instruction injection from `AGENTS.md`, `CLAUDE.md`, and configured instruction URLs/files.

## Workflow

1. Identify the relevant behavior domain: output style, tool use, planning, subagent delegation, instruction loading, or generated agent design.
2. Open the mapped OpenCode source prompt file from `references/opencode-prompt-map.md`.
3. Prefer quoting exact source lines from `RAW/repos/opencode/` when preserving provenance matters.
4. When adapting constraints into another agent, keep the behavior intent but avoid copying model-specific assumptions blindly.
5. If the task asks for "the original OpenCode wording", quote from the source snapshot and include file path plus line number.

## Reusable Constraints

- Keep CLI responses concise, direct, and task-focused.
- Do not add preamble or postscript unless useful or requested.
- Use tools to perform real filesystem/code changes; do not only describe changes when the user asked for execution.
- Investigate local evidence before making factual claims.
- Prefer existing codebase conventions and minimal correct changes.
- Never commit or mutate git history unless explicitly requested.
- Treat plan mode as read-only except for its allowed plan file.
- Use specialized tools for reading, editing, searching, and writing files; reserve shell for terminal operations.
- Ask clarifying questions only when the ambiguity materially changes the result and cannot be resolved from context.
