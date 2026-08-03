---
name: topology-json-writing
description: 当需要复杂架构拓扑、组件关系图、数据流图、依赖图、执行拓扑、DAG、数据链路、生产消费关系时，考虑用 JSON 风格结构描述。（这里的 JSON 是解释性拓扑描述，不是代码、接口 schema 或严格机器协议）；可以使用中文字段、中文说明和业务术语。默认优先表达拓扑结构，核心元素包括节点、边、视图/框选范围，不要退化成简单线性流程图。若用户要求渲染到 Mermaid、draw.io、Graphviz 等具体绘图语言，先保留拓扑 JSON 作为事实源，再切到对应绘图目标 skill。
---

# 拓扑 JSON 表达

## 目的

把 JSON 当作一种可读的架构图 / 拓扑图表达格式。

除非用户明确要求，否则这里的 JSON 不是代码生成、不是 API schema，也不是严格序列化协议。它是一种比字符画更稳定、更容易修改的结构化说明格式。

默认先表达“复杂拓扑”，再在需要时补充线性链路。不要把所有系统关系都简化成从 A 到 B 到 C 的流程图。

拓扑事实、绘图语言和视觉风格必须分层：`topology.json` 只保证语义和拓扑关系正确；Mermaid、draw.io、Graphviz 等具体绘图语言由对应 `draw-<target>/SKILL.md` 指引；白板风、科研风、配色、字体和线型等视觉风格由对应 `draw-<target>/DESIGN.md` 指引。

需要复用数据库、消息队列、服务、配置、外部系统、函数等常见拓扑元素时，读取 `references/common-elements.md`，优先复用其中的 `类型` 和 `关系`。

## 规则

- JSON 代码块可以是解释性的，不需要像生产代码一样抽象。
- 字段名可以用中文，也可以用英文；优先选择对读者最清楚的表达。
- value 可以包含中文说明、短解释、例子和业务术语。
- 拓扑核心元素是 `节点`、`边`、`视图`。`视图` 类似图上的框框，用来圈选一组节点/边，表达某个观察范围或子图。
- 常用字段可以包括 `名称`、`角色`、`负责人`、`输入`、`输出`、`触发源`、`消费者`、`写入方`、`读取方`、`依赖`、`下一步`、`证据`、`说明`、`包含节点`、`包含边`、`边界`。
- 优先识别 `节点`、`边`、`视图`、`分组`、`平面`、`读写关系`、`触发关系`、`依赖关系`、`所有权`、`证据`。
- 图结构优先用 `节点` 和 `边` 表达；线性链路只是拓扑中的一种视图，不应作为默认表达。
- 同一个节点可以有多条入边和出边；同一个系统可以同时是上游、下游、控制面组件或执行面组件。
- `视图` 不是 FeatureBank 的 `FeatureView`；除非上下文明确指 FeatureBank，否则这里的 view 指“拓扑观察视图 / 框选范围”。
- 一个 `视图` 可以圈选节点，也可以圈选边；可以有重叠视图，例如“特征生产视图”和“索引同步视图”同时包含 TBase 节点。
- 不要为了像代码而过度 schema 化；能讲清楚关系比形式严谨更重要。
- 能用 JSON 表达清楚时，避免用 `A -> B -> C` 这种字符画箭头。
- JSON 内不要写注释；需要解释时用 `说明`、`备注`、`证据` 等字段。
- 单个 JSON 块保持聚焦。控制面、数据面、运行时、存储、证据可以拆成多个块。
- 如果用户问“谁驱动谁”“谁读谁”“谁写谁”，优先显式写 `关系` 或 `边`，不要只写步骤。
- 不要把布局、颜色、形状、Mermaid 语法、draw.io XML 细节塞进 `topology.json`；这些属于目标绘图 skill。
- 从 JSON 生成具体绘图语言时，先读拓扑事实源，再读目标绘图 skill 的 `SKILL.md`；需要风格约束时再读同目录 `DESIGN.md`。
- 绘图语言和样式只能控制画法，不能新增、删除或改写拓扑关系。
- `类型` 和 `关系` 是跨绘图目标复用的语义 contract，例如 `db`、`storage`、`mq`、`service`、`config`、`sync_call`、`async_event`、`read_write`。
- 需要新增常用语义类型时，优先更新 `references/common-elements.md`；不要把某个渲染器的颜色、形状或 XML 片段写入拓扑 JSON。

## 文件分层

推荐将拓扑事实、绘图语言和视觉风格拆开：

```json
{
  "文件分层": {
    "topology.json": {
      "职责": "唯一拓扑事实源",
      "包含": ["节点", "边", "视图", "节点属性", "节点类型", "关系类型", "证据"],
      "不包含": ["布局", "颜色", "形状", "目标格式语法"]
    },
    "draw-mermaid/SKILL.md": {
      "职责": "Mermaid 绘图语言指引",
      "包含": ["图类型选择", "Mermaid 语法约束", "topology.json 到 Mermaid 的映射规则", "输出格式"]
    },
    "draw-mermaid/DESIGN.md": {
      "职责": "Mermaid 视觉风格指引",
      "包含": ["主题", "配色", "字体", "边框", "线型", "适用场景"]
    },
    "draw-drawio-xml/SKILL.md": {
      "职责": "draw.io XML 绘图语言指引",
      "包含": ["mxfile 结构", "mxCell 节点和边映射", "JSON 拓扑到 .drawio 的生成流程"]
    },
    "draw-drawio-xml/DESIGN.md": {
      "职责": "draw.io XML 视觉风格指引",
      "包含": ["语义形状映射", "低饱和工程配色", "正交布局", "实线和虚线关系"]
    },
    "draw-graphviz/SKILL.md": {
      "职责": "Graphviz 绘图语言指引",
      "包含": ["DOT 语法", "节点和边映射", "布局引擎选择"]
    }
  }
}
```

基本原则：

- `topology.json` 只管“对不对”，不管“好不好看”。
- `draw-<target>/SKILL.md` 只管“用什么绘图语言怎么画”。
- `draw-<target>/DESIGN.md` 只管“画成什么风格”。
- 不同目标格式使用不同绘图 skill。
- 布局失败时调整目标绘图 skill 的规则或本次渲染配置，不修改 `topology.json` 的节点和边。
- 如果用户只要求写拓扑，优先只给 `topology.json`；如果用户要求生成 Mermaid / draw.io / Graphviz，再切到对应目标绘图 skill。

## 推荐结构

复杂拓扑优先：

```json
{
  "拓扑": "TBase 更新、ViewEngine 消费与 Index 写入",
  "节点": [
    {
      "id": "producer_job",
      "名称": "DataCenter / UnificPipeline 生产任务",
      "类型": "Flink 生产任务",
      "角色": ["消费业务事件", "生产特征", "写 TBase"]
    },
    {
      "id": "tbase",
      "名称": "TBase 宽表",
      "类型": "在线宽表存储",
      "角色": ["承接特征物化结果", "产生 change trigger"]
    },
    {
      "id": "trigger_topic",
      "名称": "TBase change trigger topic",
      "类型": "消息通道",
      "携带信息": ["row_key", "trigger_timestamp"]
    },
    {
      "id": "view_engine",
      "名称": "ViewEngine Flink 任务",
      "类型": "Flink 消费任务",
      "角色": ["消费 trigger", "回查宽表", "写下游 sink"]
    },
    {
      "id": "index_service",
      "名称": "IndexService / online FeatureView",
      "类型": "在线索引或在线特征视图",
      "角色": ["承接 ViewEngine 写入结果"]
    }
  ],
  "视图": [
    {
      "id": "feature_production_view",
      "名称": "特征生产视图",
      "说明": "圈选从上游生产任务到 TBase 物化的子图。",
      "包含节点": ["producer_job", "tbase"],
      "包含边": ["producer_job->tbase"],
      "边界": "到 TBase 宽表写入完成为止，不包含 ViewEngine 写 Index。"
    },
    {
      "id": "index_sync_view",
      "名称": "索引同步视图",
      "说明": "圈选 TBase 变更触发 ViewEngine 并写下游的子图。",
      "包含节点": ["tbase", "trigger_topic", "view_engine", "index_service"],
      "包含边": [
        "tbase->trigger_topic",
        "trigger_topic->view_engine",
        "view_engine->tbase",
        "view_engine->index_service"
      ],
      "边界": "从 TBase change trigger 开始，到在线索引/在线视图写入完成为止。"
    }
  ],
  "边": [
    {
      "id": "producer_job->tbase",
      "from": "producer_job",
      "to": "tbase",
      "关系": "写入",
      "写入节点": "FeatureBankSink / TBASE_SINK"
    },
    {
      "id": "tbase->trigger_topic",
      "from": "tbase",
      "to": "trigger_topic",
      "关系": "变更后产生 trigger"
    },
    {
      "id": "trigger_topic->view_engine",
      "from": "trigger_topic",
      "to": "view_engine",
      "关系": "触发消费"
    },
    {
      "id": "view_engine->tbase",
      "from": "view_engine",
      "to": "tbase",
      "关系": "按 row_key 回查",
      "说明": "ViewEngine 是读取方，不是 TBase 写入方"
    },
    {
      "id": "view_engine->index_service",
      "from": "view_engine",
      "to": "index_service",
      "关系": "写入",
      "写入节点": "FeatureBankV2OnlineSink"
    }
  ],
  "结论": [
    "TBase 更新由上游生产任务驱动",
    "Index 写入由 TBase change trigger 驱动 ViewEngine 后完成",
    "ViewEngine 不驱动 TBase 更新"
  ]
}
```

多平面拓扑：

```json
{
  "系统": "datacenter_view_engine",
  "视图": [
    {
      "id": "control_plane_view",
      "名称": "控制面视图",
      "包含分组": ["控制面", "配置面"],
      "说明": "描述谁生成配置、注册任务、管理元数据。"
    },
    {
      "id": "execution_plane_view",
      "名称": "执行面视图",
      "包含分组": ["执行面"],
      "说明": "描述 Flink JM/TM 和 unific_pipeline_runtime 如何执行任务。"
    },
    {
      "id": "packaging_view",
      "名称": "打包下发视图",
      "包含节点": ["user_config", "src/main/resources", "datacenter_view_engine*.jar", "Dorado", "Flink JobManager / TaskManager"],
      "说明": "描述配置如何进入 jar，以及 jar 如何被任务平台部署执行。"
    }
  ],
  "分组": {
    "控制面": {
      "组件": ["DataCenter", "XCenter", "Dorado"],
      "职责": ["生成配置", "注册任务", "部署任务", "管理元数据"]
    },
    "执行面": {
      "组件": ["Flink JobManager", "Flink TaskManager", "unific_pipeline_runtime"],
      "职责": ["消费 source", "执行 operator", "写 sink"]
    },
    "配置面": {
      "组件": ["user_config", "src/main/resources", "FeatureBank / MetaCenter"],
      "职责": ["提供 DAG JSON", "提供 source SQL", "运行时解析目标 schema"]
    }
  },
  "跨分组关系": [
    {
      "from": "DataCenter / XCenter",
      "to": "user_config",
      "关系": "维护配置"
    },
    {
      "from": "user_config",
      "to": "datacenter_view_engine*.jar",
      "关系": "构建期打包进 resources"
    },
    {
      "from": "Dorado",
      "to": "Flink JobManager / TaskManager",
      "关系": "部署并启动任务"
    },
    {
      "from": "unific_pipeline_runtime",
      "to": "FeatureBank / MetaCenter",
      "关系": "运行时读取目标 view / table 元数据"
    }
  ],
  "说明": "这是拓扑说明 JSON，不是代码接口。"
}
```

目标绘图 skill 分工：

- `draw-mermaid/SKILL.md`：决定 flow / sequence / state / class 等 Mermaid 图类型，约束 Mermaid 语法和 `topology.json` 到 Mermaid 的映射。
- `draw-mermaid/DESIGN.md`：维护 Mermaid 可选风格，例如板绘风、科研绘图风、配色、字体和线型。
- `draw-drawio-xml/SKILL.md`：把自然语言、表格化拓扑或 `topology.json` 生成 draw.io / diagrams.net 可导入 XML。
- `draw-drawio-xml/DESIGN.md`：维护 draw.io XML 的语义形状、低饱和工程配色、正交布局和线型约束。
- 未来新增 Graphviz、TikZ 等目标时，按同样结构拆成独立 `draw-<target>/SKILL.md` 和 `draw-<target>/DESIGN.md`。

## 修改文档时

如果文档里已有字符画链路，例如：

```text
A -> B -> C
```

应改成 JSON 结构，保留原有含义，并尽量补充角色、触发源、读取方、写入方、证据等标签。
