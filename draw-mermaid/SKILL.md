---
name: draw-mermaid
description: Generate Mermaid diagrams from requirements or from a topology JSON fact source. Use for flowcharts, sequence diagrams, state diagrams, class diagrams, architecture diagrams, dependency graphs, data flows, DAGs, code-call graphs, and module interaction diagrams. SKILL.md guides Mermaid language usage; DESIGN.md guides visual style.
---

# Mermaid 绘图

## 使用场景

当用户要求画 Mermaid、流程图、时序图、状态图、类图、架构图、依赖图、数据流图、DAG、函数调用图，或者要求把 `topology.json` 渲染成 Mermaid 时，使用这个 Skill。

如果输入是复杂系统关系，优先先用 `draw-topology-json` 抽取 `topology.json`，再根据这里的规则渲染 Mermaid。`topology.json` 是事实源，Mermaid 只是目标绘图语言。

视觉风格、配色、字体、线型和板绘风 / 科研风等样式要求读取同目录 `DESIGN.md`。

需要 Mermaid 代码片段作为起点时，读取 `references/examples.md`。

## 流程

1. 分析需求，识别节点、事件、过程、动作、模块、数据存储和交互关系。
2. 判断 Mermaid 图类型：
   - `graph TD` / `flowchart TD`：控制流、数据流、依赖图、DAG、组件拓扑。
   - `graph LR` / `flowchart LR`：代码调用 fanout、pipeline、横向依赖链路。
   - `sequenceDiagram`：模块、服务、用户、队列之间的时序交互。
   - `stateDiagram-v2`：状态机、生命周期、重试、循环、动态更新状态。
   - `classDiagram`：数据结构、对象关系、继承、字段、方法。
3. 如果存在 `topology.json`，只按其中的节点、边、视图和分组渲染，不新增、删除或改写拓扑事实。
4. 如果用户指定风格，或图要进入文档、论文、汇报材料，读取 `DESIGN.md` 选择样式。
5. 输出 Mermaid 代码块；如果用户要求解释，再在代码块外用短句说明图类型。

## 语法约束

- Mermaid 标签不要使用中文标点。使用 ASCII 标点，例如 `,`, `.`, `:`, `(`, `)`, `/`, `-`。
- 不使用 `<br/>` 换行。标签过长时拆节点、缩短名称或使用 note。
- 不过度使用 emoji 或装饰符号。
- 节点 id 尽量稳定并使用 ASCII；函数名、类名、模块名优先保留原始代码名称。
- 可以在标签中使用中文业务描述，帮助读者理解业务逻辑。
- 从 `topology.json` 渲染时，`视图` 或分组优先映射为 `subgraph`。
- Mermaid 代码块内部只放 Mermaid 语法，不混入解释文字。

## 图类型要点

- 普通流程图：默认 `graph TD`，强调从上到下的控制流或数据流。
- 横向代码调用图：用 `graph LR`，适合函数调用、依赖 fanout、pipeline 展开。
- 状态图：用 `stateDiagram-v2`，适合状态流转、生命周期、循环和重试。
- 时序图：用 `sequenceDiagram`，适合模块、服务、用户、队列之间按时间展开的交互。
- 类图：用 `classDiagram`，适合数据结构、对象模型、继承、字段和方法。

横向代码调用图的约定：

- 节点 id 直接用函数名。
- 标签使用中文功能描述加斜体函数名。
- 函数名对应代码，中文描述对应业务含义。
- 需要完整代码片段时读取 `references/examples.md`。

## 参考

- Mermaid 中文语法文档: https://mermaid.nodejs.cn/syntax/sankey.html
