---
name: sync-agent-rules
description: Sync repository agent-rule and agent metadata files across Codex, Claude Code, OpenCode, and shared skill folders. Use whenever editing or reviewing AGENTS.md, CLAUDE.md, .agents/*.md, .claude/agents/*.md, .opencode/agents/*.md, .agents/skills/**, .claude/skills/**, or repository-level agent governance prompts so changes propagate immediately and drift is reported.
---

# Sync Agent Rules

## 用法

改仓库级 agent 规则或元数据后，直接运行同步脚本。一条命令处理 Codex、Claude Code、OpenCode 和 skill 副本；能同步就同步，不存在的 OpenCode 目录自动跳过。

```bash
python3 <skill-dir>/scripts/sync_agent_rules.py
```

只检查不写文件：

```bash
python3 <skill-dir>/scripts/sync_agent_rules.py --check
```

```bash
python3 <skill-dir>/scripts/sync_agent_rules.py -h
```

## 同步规则

- `AGENTS.md` 和 `CLAUDE.md` 精确同步；两边不一致时使用更新时间较新的文件覆盖较旧文件。
- `.agents/skills/**`、`.claude/skills/**` 精确同步；如果 `.opencode/skills/` 存在，也同步进去。缺失的 OpenCode skills 目录不创建。
- `.agents/<name>.md` is the shared source for long agent rules.
- `.claude/agents/<name>.md` 生成 Claude Code wrapper，保留已有 frontmatter，正文指向 `.agents/<name>.md`。
- `.opencode/agents/<name>.md` 或 `.opencode/agent/<name>.md` 存在对应目录时生成 OpenCode wrapper；没有 OpenCode 目录就跳过。
- `.agents/notion-memory.md` 这类本地记忆文件不生成 wrapper。

## 验证

同步后运行仓库自己的检查命令。没有专门命令时，至少跑：

```bash
python3 <skill-dir>/scripts/sync_agent_rules.py --check
```
