# SKILLS

Personal reusable skills for TRAE CLI, Claude Code, and related agent workflows.

每个 skill 独立放在一个目录，至少包含 `SKILL.md`。绘图类 skill 可继续拆 `DESIGN.md` 和 `references/`：`SKILL.md` 写语言/流程，`DESIGN.md` 写视觉风格，`references/` 放示例和片段。

## 分类

- 工具类：直接操作外部工具、浏览器、终端、CLI、文件格式或运行环境。
- 设计类：定义表达语言、视觉风格、拓扑语义、图形生成规则。
- 开发类：辅助代码、脚本、系统、仓库或 Agent 能力开发。
- 实施经验：沉淀可复用的操作流程、排障路径、长期任务管理经验。

## Skill 索引

| Skill | 分类 | 标签 | 用途 |
|---|---|---|---|
| `chrome-cdp-session` | 工具类 / 实施经验 | `browser`、`cdp`、`login-state`、`debug` | 复用当前 Chrome 登录态做浏览器检查、CDP 连接和网页调试。 |
| `lark-md-sync` | 工具类 | `lark`、`feishu`、`markdown`、`sync` | 双向同步本地 Markdown 与飞书 Drive 原生 Markdown 文件，支持 dry-run、状态检查和三方合并。 |
| `tmux-automation` | 工具类 / 实施经验 | `terminal`、`tmux`、`long-running`、`tui`、`ssh` | 管理长任务、TUI 检查、pane 截图、SSH 会话和可恢复终端工作流。 |
| `draw-topology-json` | 设计类 | `topology`、`json`、`semantic-model`、`diagram-source` | 把复杂系统关系抽成语义拓扑 JSON，作为 Mermaid / draw.io 等渲染目标的事实源。 |
| `draw-mermaid` | 设计类 / 开发类 | `mermaid`、`diagram`、`architecture`、`flowchart` | 将需求或 topology JSON 渲染为 Mermaid 图，`DESIGN.md` 维护视觉风格。 |
| `draw-drawio-xml` | 设计类 / 开发类 | `drawio`、`xml`、`diagram`、`architecture` | 将拓扑 JSON 或自然语言关系生成 draw.io / diagrams.net 可导入 XML。 |
| `opencode-agent-prompts` | 开发类 / 实施经验 | `opencode`、`agent`、`prompt`、`style` | 学习 OpenCode 源码中控制 Agent 行为、工作模式、工具使用和终端输出风格的提示词。 |

## 标签约定

标签优先描述可复用能力，不按一次性任务命名。

- 环境：`browser`、`terminal`、`ssh`、`tui`
- 工具协议：`cdp`、`tmux`、`drawio`、`mermaid`
- 产物类型：`diagram`、`architecture`、`topology`、`xml`、`json`
- 工作方式：`debug`、`long-running`、`login-state`、`semantic-model`

## 待补

- 文风切换：区分终端回复、Wiki 正文、README、报告和代码注释的输出风格。
- Skill 路由：后续可按分类生成更稳定的索引，供 Agent 先选 skill 再读具体 `SKILL.md`。
