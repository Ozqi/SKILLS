# OpenCode Prompt Map

Source snapshot:

- local path: `RAW/repos/opencode/`
- upstream: `https://github.com/anomalyco/opencode`
- ref: `1882c33827cf0ce5c948b69ab5a87ed8f6790cf8`
- package version observed in `packages/opencode/package.json`: `1.18.11`

This map is for studying prompts that control agent behavior and working style. Do not treat it as an implementation guide for OpenCode internals.

## Prompt Assembly

- `RAW/repos/opencode/packages/opencode/src/session/system.ts`
  - `provider(model)` chooses model-specific system prompt files.
  - `environment(...)` injects model id, working directory, workspace root, git status, platform, and date.
  - `skills(...)` injects available skill names/descriptions and tells the model to load matching skills with the skill tool.
  - `mcp(...)` injects MCP server instructions when permitted.
- `RAW/repos/opencode/packages/opencode/src/agent/agent.ts`
  - Defines native agents: `build`, `plan`, `general`, `explore`, `compaction`, `title`, `summary`.
  - Merges default permissions, user config permissions, and per-agent overrides.
  - `build` is the default primary agent; `plan` denies edit tools except allowed plan files; `explore` is a read/search-focused subagent.
- `RAW/repos/opencode/packages/opencode/src/session/instruction.ts`
  - Loads global `AGENTS.md` and optionally `~/.claude/CLAUDE.md`.
  - Loads project-level `AGENTS.md`, `CLAUDE.md`, or deprecated `CONTEXT.md`; first matching instruction type wins instead of stacking every ancestor.
  - Loads configured local or remote instructions, rendered as `Instructions from: <path-or-url>`.
  - When a read file has nearby nested instructions, attaches them once per assistant message.
- `RAW/repos/opencode/CONTEXT.md`
  - Describes the V2 context model: System Context, Context Source, Baseline System Context, Mid-Conversation System Message, Context Epoch, Prompt Promotion, and Safe Provider-Turn Boundary.

## Main System Prompt Files

- `RAW/repos/opencode/packages/opencode/src/session/prompt/default.txt`
  - General OpenCode prompt for many models.
  - Strong output style block: concise, direct, CLI-oriented, no unnecessary preamble/postamble, fewer than 4 lines unless detail is requested.
  - Proactivity: act when asked, but do not surprise users; answer approach questions before taking action.
  - Coding behavior: read existing code, follow conventions, minimal changes, check libraries exist, verify when possible, never commit unless explicitly asked.
- `RAW/repos/opencode/packages/opencode/src/session/prompt/trinity.txt`
  - Very similar to `default.txt`; useful as the compact output-style source.
  - Original output-style wording includes:

```text
You should be concise, direct, and to the point.
IMPORTANT: You should minimize output tokens as much as possible while maintaining helpfulness, quality, and accuracy.
IMPORTANT: You should NOT answer with unnecessary preamble or postamble (such as explaining your code or summarizing your action), unless the user asks you to.
IMPORTANT: Keep your responses short, since they will be displayed on a command line interface. You MUST answer concisely with fewer than 4 lines (not including tool use or code generation), unless user asks for detail.
```

- `RAW/repos/opencode/packages/opencode/src/session/prompt/codex.txt`
  - OpenCode prompt variant aligned with Codex-style engineering behavior.
  - Emphasizes shared workspace collaboration, senior-engineer judgment, minimal correct changes, apply_patch for manual edits, dirty-worktree hygiene, review stance, concise final answers, and progress updates.
- `RAW/repos/opencode/packages/opencode/src/session/prompt/meta.txt`
  - Muse Spark prompt variant.
  - Emphasizes short concise responses, factual/objective technical info, evidence before synthesis, active corrections across turns, TodoWrite usage, subagents for split tasks, parallel tool calls, and plan-mode read-only behavior.
- `RAW/repos/opencode/packages/opencode/src/session/prompt/gpt.txt`
  - General AI agent prompt: default to taking action with tools when a request could be a task, same-language response, inspect code before changes, minimal changes, no git mutations unless explicitly requested, concise and accurate.
- `RAW/repos/opencode/packages/opencode/src/session/prompt/anthropic.txt`
  - Claude-oriented prompt.
  - Uses TodoWrite very frequently, Task for codebase exploration, OpenCode docs WebFetch for OpenCode questions, and professional objectivity.
- `RAW/repos/opencode/packages/opencode/src/session/prompt/beast.txt`
  - High-autonomy variant: keep working until solved, extensive research, strong testing/iteration requirements.
  - Treat as an aggressive contrast case rather than a default style template.
- `RAW/repos/opencode/packages/opencode/src/session/prompt/gemini.txt`, `kimi.txt`, `copilot-gpt-5.txt`
  - Additional model-specific variants; inspect when adapting prompts for those providers.

## Plan And Build Mode

- `RAW/repos/opencode/packages/opencode/src/session/prompt/plan.txt`
  - Strict read-only reminder. Forbids file edits, system changes, and write-shaped shell commands.
- `RAW/repos/opencode/packages/opencode/src/session/prompt/plan-mode.txt`
  - Full plan-mode workflow:
  - Phase 1: understand request and use up to 3 explore agents in parallel.
  - Phase 2: design with up to 1 general/plan agent.
  - Phase 3: review plans and read critical files.
  - Phase 4: write concise final plan to the allowed plan file.
  - Phase 5: call `plan_exit`; do not ask "is this plan okay" with the question tool.
- `RAW/repos/opencode/packages/opencode/src/session/prompt/build-switch.txt`
  - Reminder that mode changed from plan to build and edits/tools are allowed.
- `RAW/repos/opencode/packages/opencode/src/session/prompt/plan-reminder-anthropic.txt`
  - Claude-specific plan reminder, similar to `plan-mode.txt`.

## Built-In Agent Prompts

- `RAW/repos/opencode/packages/opencode/src/agent/generate.txt`
  - Agent generator prompt.
  - Requires extracting core intent, designing an expert persona, writing comprehensive instructions, optimizing for performance, and producing JSON with `identifier`, `whenToUse`, and `systemPrompt`.
  - Tells generated agent prompts to be specific, include quality controls, and function as an autonomous operational manual.
- `RAW/repos/opencode/packages/opencode/src/agent/prompt/explore.txt`
  - File search specialist.
  - Uses glob/grep/read/bash for exploration, adapts thoroughness, returns absolute paths, avoids emojis, and must not create files or modify system state.
- `RAW/repos/opencode/packages/opencode/src/agent/prompt/compaction.txt`
  - Anchored context summarizer.
  - Summarizes only provided history, preserves still-true details, removes stale details, keeps exact structure, paths, and identifiers, and does not answer the conversation.
- `RAW/repos/opencode/packages/opencode/src/agent/prompt/title.txt`
  - One-line title generator, same language as user, <= 50 chars, no explanations, no tool names.
- `RAW/repos/opencode/packages/opencode/src/agent/prompt/summary.txt`
  - PR-description-style conversation summary, 2-3 sentences, changes not process, no tests/build mention, first person.

## Tool Prompt Sources

- `RAW/repos/opencode/packages/opencode/src/tool/shell/shell.txt`
  - Shell tool top-level prompt.
  - Terminal operations only; do not use shell for reading, writing, editing, searching, or finding files when specialized tools exist.
  - Git and GitHub rules: only commit/amend/push/PR when explicitly requested; inspect status/diff/log before commit; never force-push or use interactive git unless explicitly requested.
- `RAW/repos/opencode/packages/opencode/src/tool/shell/prompt.ts`
  - Renders shell-specific command guidance.
  - Enforces quoting paths with spaces, workdir instead of `cd`, no output-truncating commands, parallel shell calls for independent commands, sequential chaining for dependent commands, and no shell output as communication.

## Repo-Local OpenCode Config

- `RAW/repos/opencode/.opencode/agent/duplicate-pr.md`
  - Hidden primary GitHub PR duplicate detector; only `github-pr-search` tool enabled.
- `RAW/repos/opencode/.opencode/agent/triage.md`
  - Hidden primary GitHub issue triage agent; only `github-triage` tool enabled; assigns owner team only.
- `RAW/repos/opencode/.opencode/command/*.md`
  - Slash-command prompts. Useful examples:
  - `changelog.md`: user-facing changelog generation, verify real diffs before writing entries.
  - `commit.md`: commit/push command prompt with diff/status injection and explicit conflict boundary.
  - `learn.md`: extract non-obvious learnings into nearest `AGENTS.md`.
  - `rmslop.md`: remove AI slop such as extra comments, abnormal defensive checks, `any` casts, and unnecessary emojis.
  - `translate.md`: preserve technical artifacts and locale glossary while translating docs/UI copy.

## Reusable Behavior Lessons

- Split prompt layers by responsibility:
  - identity and global behavior,
  - runtime environment,
  - available skills/MCP instructions,
  - project instruction files,
  - tool-specific usage policy,
  - mode-specific reminders,
  - per-agent prompt and permissions.
- Use permission boundaries, not just prose:
  - `plan` denies edit tools except the plan file.
  - `explore` denies broad write capability and is optimized for read/search.
  - hidden utility agents deny all tools when no tools are needed.
- Keep output constraints concrete:
  - same language as user when required,
  - concise CLI output,
  - no emojis unless requested,
  - no preamble/postscript unless useful,
  - cite files as `file_path:line_number`.
- Keep execution constraints concrete:
  - inspect before editing,
  - follow local conventions,
  - make minimal changes,
  - verify with discovered project commands,
  - never commit unless explicitly requested,
  - preserve dirty worktree changes that are not yours.
- Keep evidence flow durable:
  - load `AGENTS.md`/`CLAUDE.md` as explicit instruction sources,
  - render context changes as mid-conversation system messages at safe provider-turn boundaries,
  - keep compaction anchored and structured.
