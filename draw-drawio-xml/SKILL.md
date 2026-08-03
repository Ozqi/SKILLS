---
name: draw-drawio-xml
description: 根据自然语言描述、JSON 拓扑或已有系统链路生成 draw.io / diagrams.net 可导入的 XML 架构图文件，支持服务、模块、Repo 容器、MQ、存储、配置、外部系统等节点语义映射，以及正交连线、虚线依赖、容器边界和低饱和工程架构图样式。适用于用户要求生成 draw XML、输出 .drawio/.xml 架构图、把拓扑转成 draw.io 文件、绘制可导入 diagrams.net 的工程架构图等场景。
---

# Draw.io XML 架构图生成

将用户的自然语言描述、表格化拓扑、JSON 拓扑或代码链路摘要，转成 draw.io / diagrams.net 可导入的 XML 文件。优先产出 `.drawio` 文件；如果用户明确要求 XML，则产出 `.xml`，两者内容都使用 draw.io XML 格式。

如果输入是复杂系统关系，优先先用 `draw-topology-json` 抽取 `topology.json`，再根据这里的规则生成 draw.io XML。`topology.json` 是事实源，draw.io XML 是目标绘图语言。

视觉风格、语义形状、配色、布局和线型读取同目录 `DESIGN.md`。常用拓扑元素的语义类型来自 `draw-topology-json/references/common-elements.md`。需要 XML 结构片段时读取 `references/xml-structure.md`。

## 输入判断

先把用户输入归一化为拓扑 JSON，再生成 XML。拓扑 JSON 包含节点和边两类对象，字段可以使用中文风格的 `节点` / `边` / `名称` / `类型` / `关系`，也可以使用脚本兼容的 `nodes` / `edges` / `label` / `type`。

节点字段建议使用：`id`、`名称`、`类型`。其中 `id` 必须稳定且唯一，`名称` 是图上展示名，`类型` 决定图形语义。也兼容英文 `label`、`type`。坐标不是拓扑事实，缺失时由 renderer 按 left-to-right 分层布局自动补齐；只有用户明确要求固定布局时才在 JSON 中写 `x`、`y`、`width`、`height`。

边字段建议使用：`from`、`to`、`关系`、`label`。其中 `from` 和 `to` 必须引用已有节点；`关系` 使用 `draw-topology-json/references/common-elements.md` 中的语义关系，例如 `sync_call`、`async_event`、`read`、`write`、`read_write`、`config`、`depends_on`、`deploy`、`trigger`。也兼容英文 `type`。

当输入是自然语言时，先抽取服务、模块、仓库、存储、消息队列、配置、外部系统和调用关系。无法确认的节点不要硬编细节，可用用户原词作为 label，并在最终说明中提示可继续补充拓扑。

## XML 生成要求

生成文件必须是 draw.io 可导入结构，顶层使用 `mxfile`，内部包含 `diagram`、`mxGraphModel`、`root`，并至少包含 id 为 `0` 和 `1` 的基础 `mxCell`。

每个节点生成一个 vertex `mxCell`，包含 `id`、`value`、`style`、`vertex="1"`、`parent="1"`，并包含 `mxGeometry`，其中 `as="geometry"`。

每条边生成一个 edge `mxCell`，包含 `source`、`target`、`style`、`edge="1"`、`parent="1"`，并包含 `mxGeometry relative="1" as="geometry"`。

所有用户可见文本写入 XML 前都要做 XML escape，避免 `&`、`<`、`>` 破坏导入。节点 id 使用稳定英文、数字、下划线或连字符，不使用空格和中文。

## 使用辅助脚本

当输入已经是 JSON 拓扑，或可以快速整理成 JSON 拓扑时，优先使用 `scripts/generate_drawio_xml.py` 生成文件，减少手写 XML 的错误。

输入 JSON 示例见 `assets/example-topology.json`。执行方式：

```bash
python3 scripts/generate_drawio_xml.py assets/example-topology.json -o architecture.drawio
```

脚本支持 `draw-topology-json` 的中文字段和英文兼容字段。节点类型包括 `service`、`module`、`repo`、`mq`、`storage`、`db`、`cache`、`external`、`config`、`function`、`client`、`gateway`、`worker`。样式默认由脚本内置映射和 `DESIGN.md` 约束决定；不要在拓扑 JSON 中写颜色。只有用户明确要求局部覆盖时，才在节点或边上追加 draw.io 原生 `style` 字符串。

## 质量检查

生成后检查 XML 至少满足这些条件：

- 文件可被 draw.io / diagrams.net 导入。
- 所有 edge 的 `source` 和 `target` 都能找到对应节点。
- 没有重复节点 id。
- 用户原始拓扑中的关键组件和关键关系都已出现。
- Repo、MQ、存储、配置等专用语义没有被统一画成普通矩形。

最终回复用户时，提供生成的 `.drawio` 或 `.xml` 文件链接，并简要说明可以直接在 draw.io / diagrams.net 中通过 Import 打开。
