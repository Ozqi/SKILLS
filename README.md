# SKILLS

Personal reusable skills for TRAE CLI, Claude Code, and related agent workflows.

每个 skill 独立放在一个目录，至少包含 `SKILL.md`。绘图类 skill 可继续拆 `DESIGN.md` 和 `references/`：`SKILL.md` 写语言/流程，`DESIGN.md` 写视觉风格，`references/` 放示例和片段。

## 分类口径

- 通用 / Agent 工作流：沟通风格、规则同步、上下文管理、跨 Agent 协作和可复用执行约束。
- 工具 / 运行环境：直接操作浏览器、终端、DSH 会话、Lark Markdown 等外部运行面。
- 编码 / 仓库协作：提交信息、代码定位链接、仓库审阅和工程协作辅助。
- 可视化 / 架构表达：拓扑事实源、Mermaid、draw.io 等图形化表达。
- 前端 / 设计 / 动效：UI/UX、动画库、React/Remotion/Apple 风格动效；当前主要登记外部链接，不复制第三方内容。
- 领域项目 / 个人约定：只在特定项目、工作域或个人习惯中复用的规则。

## 本地 Skill 索引

### 通用 / Agent 工作流

| Skill | 目录 | 标签 | 用途 |
| --- | --- | --- | --- |
| `asd-ste100` | `asd-ste100/` | `writing`、`prompt`、`controlled-language`、`lint` | 用 ASD-STE100 风格改写含歧义的英文 Agent 输出、工具说明、错误消息和跨 Agent 指令。 |
| `opencode-final-answer-style` | `opencode-final-answer-style/` | `output`、`markdown`、`cli`、`style` | 统一 coding agent 最终回复风格，保持简洁、可扫读、路径可点击。 |
| `sync-agent-rules` | `agent-sync-prompts/` | `agents`、`rules`、`sync`、`codex`、`claude` | 同步 `AGENTS.md`、`CLAUDE.md`、`.agents/`、`.claude/`、`.opencode/` 等 Agent 规则和 skill 副本。 |

### 工具 / 运行环境

| Skill | 目录 | 标签 | 用途 |
| --- | --- | --- | --- |
| `chrome-cdp-session` | `connect-chrome-cdp-session/` | `browser`、`cdp`、`login-state`、`debug` | 复用当前 Chrome 登录态做浏览器检查、CDP 连接和网页调试。 |
| `dsh-web-multi-session` | `dsh-web-multi-session/` | `dsh`、`session`、`coordination`、`web` | 检查和协调多个 DeepSeek Harness Web 会话。 |
| `tmux-skill` | `tmux-use-skill/` | `terminal`、`tmux`、`long-running`、`tui`、`ssh` | 管理长任务、TUI 检查、pane 截图、SSH 会话、定时检查和可恢复终端工作流。 |
| `lark-md-sync` | `lark-md-sync/` | `lark`、`feishu`、`markdown`、`sync` | 双向同步本地 Markdown 与飞书 Drive 原生 Markdown 文件，支持 dry-run、状态检查和三方合并。 |

### 编码 / 仓库协作

| Skill | 目录 | 标签 | 用途 |
| --- | --- | --- | --- |
| `canonical-code-link` | `canonical-code-link/` | `code-link`、`markdown`、`github`、`vscode` | 生成和审阅可点击的代码位置链接，包括本地路径、IDE 链接和 GitHub `blob` 链接。 |
| `code-commit-style` | `code-commit-style/` | `git`、`commit`、`conventional-commits` | 按 Conventional Commits 写、审阅或规范化提交信息；描述提交前先看实际 diff。 |

### 可视化 / 架构表达

| Skill | 目录 | 标签 | 用途 |
| --- | --- | --- | --- |
| `draw-topology-json` | `draw-topology-json/` | `topology`、`json`、`semantic-model`、`diagram-source` | 把复杂系统关系抽成语义拓扑 JSON，作为 Mermaid / draw.io 等渲染目标的事实源。 |
| `draw-mermaid` | `draw-mermaid/` | `mermaid`、`diagram`、`architecture`、`flowchart` | 将需求或 topology JSON 渲染为 Mermaid 图，`DESIGN.md` 维护视觉风格。 |
| `draw-drawio-xml` | `draw-drawio-xml/` | `drawio`、`xml`、`diagram`、`architecture` | 将拓扑 JSON 或自然语言关系生成 draw.io / diagrams.net 可导入 XML。 |

### 领域项目 / 个人约定

| Skill | 目录 | 标签 | 用途 |
| --- | --- | --- | --- |
| `ziqi的约定` | `ziqi的约定/` | `ziqi`、`project-conventions`、`style` | Ziqi 项目的目录、输出风格、工具使用和代码协作约定。 |

### 占位 / 待整理

| 目录 | 状态 | 处理 |
| --- | --- | --- |
| `agent-context&&skill/` | 当前没有 `SKILL.md` | 后续若补齐正文，再归入“通用 / Agent 工作流”。 |

## Skill 路由

Agent 选择 skill 时，先按“分类”和“标签”缩小候选范围，再读取对应目录下的 `SKILL.md` 确认触发条件、工作流和边界。分类用于稳定入口，标签用于表达跨分类能力；新增 skill 时应同步补齐索引行，避免只依赖目录名或全文搜索判断用途。

## 输出文风

- 终端回复：直接说明动作、结果、验证和阻塞，少铺垫，不写长篇背景。
- Wiki 正文：只沉淀可复用知识，保留来源和互链，不写聊天过程、任务状态或生成说明。
- README：面向第一次进入目录的读者，说明定位、结构、入口和维护边界。
- 报告：先给结论和风险，再列证据、范围、方法、未覆盖项和后续建议。
- 代码注释：解释模块职责、关键状态、复杂流程和副作用，不逐行翻译代码。

## Agent 上下文使用原则

Agent 的上下文窗口是有限的工作记忆：系统规则、用户指令、工具结果、已读文件和当前回复都会占用窗口。省上下文的核心不是少做事，而是减少无关内容进入窗口，优先保留当前任务需要的规则、目标文件、关键片段、决策依据和验证结果。

实践上，先用搜索定位最小相关范围，再读取局部片段；避免整仓、整页、整日志灌入上下文。长输出优先压缩为路径、行号、结论和少量原文证据。完成阶段只回传修改路径、验证命令、剩余风险和可执行补丁，不复述完整过程。

## SOP 约束

- 强约束任务应写明可执行目标、输入来源、验收标准、下一步动作和阻塞条件；需要约束 Agent 按 SOP 执行时，把 SOP 拆成不可跳过的检查点，并要求每次更新状态时同步记录当前步骤、产物路径和剩余风险。

# 优秀资源

外部项目只登记链接，不复制内容；需要长期固定版本时再考虑 git submodule。

## 前端 / 设计 / 动效

1. UI/UX Pro Max — 外部 UI/UX 设计 skill：https://github.com/nextlevelbuilder/ui-ux-pro-max-skill
2. GSAP — 前端动画库：https://github.com/greensock/GSAP
3. Remotion Skills — Remotion / React 视频最佳实践 skill：https://github.com/buainoai/remotion-skills
4. Remotion AI docs — 官方 AI 文档：https://www.remotion.dev/docs/ai/
5. Apple Design — Apple 风格 Web / React 动效 skill：https://github.com/emilkowalski/skills/blob/main/skills/apple-design/SKILL.md

## 调研 / 网络

1. Agent-Reach — 网络搜索和社交媒体路由；部分依赖 OpenCLI 连接浏览器插件调试模式，热门社媒网站高效，冷门网站能力较弱。

## 系统设计 / 架构

1. System Design Primer 中文版 — 系统设计学习资料：https://github.com/donnemartin/system-design-primer/blob/master/README-zh-Hans.md

# 方法论

- “别那么勤快”，ponytail：https://github.com/DietrichGebert/ponytail
- 拒绝形式主义代码。
- 自我认知：理解 LLM 上下文窗口特性，以及上下文过满会导致注意力涣散的问题；理解 skill 的加载原理。
- 草台班子：别人提供的接口和报错信息仅供参考，不能无条件信任；要区分大概率可靠的内容和可能有 bug 的内容。
