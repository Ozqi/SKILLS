# SKILLS

Personal reusable skills for TRAE CLI, Claude Code, and related agent workflows.

每个 skill 独立放在一个目录，至少包含 `SKILL.md`。绘图类 skill 可继续拆 `DESIGN.md` 和 `references/`：`SKILL.md` 写语言/流程，`DESIGN.md` 写视觉风格，`references/` 放示例和片段。

## 分类

- 工具类：直接操作外部工具、浏览器、终端、CLI、文件格式或运行环境。
- 设计类：定义表达语言、视觉风格、拓扑语义、图形生成规则。
- 开发类：辅助代码、脚本、系统、仓库或 Agent 能力开发。
- 实施经验：沉淀可复用的操作流程、排障路径、长期任务管理经验。

## Skill 索引

| Skill                | 分类         | 标签                                                  | 用途                                                             |
| -------------------- | ---------- | --------------------------------------------------- | -------------------------------------------------------------- |
| `chrome-cdp-session` | 工具类 / 实施经验 | `browser`、`cdp`、`login-state`、`debug`               | 复用当前 Chrome 登录态做浏览器检查、CDP 连接和网页调试。                             |
| `lark-md-sync`       | 工具类        | `lark`、`feishu`、`markdown`、`sync`                   | 双向同步本地 Markdown 与飞书 Drive 原生 Markdown 文件，支持 dry-run、状态检查和三方合并。 |
| `tmux-skill`         | 工具类 / 实施经验 | `terminal`、`tmux`、`long-running`、`tui`、`ssh`        | 管理长任务、TUI 检查、pane 截图、SSH 会话、定时检查和可恢复终端工作流。                     |
| `draw-topology-json` | 设计类        | `topology`、`json`、`semantic-model`、`diagram-source` | 把复杂系统关系抽成语义拓扑 JSON，作为 Mermaid / draw.io 等渲染目标的事实源。             |
| `draw-mermaid`       | 设计类 / 开发类  | `mermaid`、`diagram`、`architecture`、`flowchart`      | 将需求或 topology JSON 渲染为 Mermaid 图，`DESIGN.md` 维护视觉风格。           |
| `draw-drawio-xml`    | 设计类 / 开发类  | `drawio`、`xml`、`diagram`、`architecture`             | 将拓扑 JSON 或自然语言关系生成 draw.io / diagrams.net 可导入 XML。             |



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

分类摆放：

设计类，画图，前端页面：
1.

网络搜索&社交媒体，Agent-Reach
- 部分依赖openCLI链接浏览器插件调试模式操作。（总之对于热门社媒网站很高效，冷门网站很拉胯）




# 方法论



“别那么勤快”，ponytail
https://github.com/DietrichGebert/ponytail

拒绝形式主义代码：


自我认知，LLM上下文的特性，以及当上下文过满会出现注意力涣散的问题；SKILL的加载原理。

草台班子，别人提供的接口和报错信息，仅供参考，不能无条件的信任。要明辨什么是大概率不会出错的，什么是可能有BUG的。
