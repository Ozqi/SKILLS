# Draw.io XML Design

This file guides visual style, layout, and semantic shape mapping for draw.io / diagrams.net XML diagrams. The topology JSON remains semantic; this file controls how those semantics look.

## 图形语义映射

生成 draw.io XML 时按 `draw-topology-json/references/common-elements.md` 中的 `类型` 选择 `mxCell` 的 shape 和 default style：

| 类型 | 用途 | draw.io 形状与风格 |
| --- | --- | --- |
| `client` | 调用方、用户入口、上游客户端 | 圆角矩形，蓝色系 |
| `gateway` | 网关、代理、入口路由 | 六边形或圆角矩形，蓝色强调 |
| `service` | 在线服务、系统、核心进程 | 圆角矩形，蓝色系 |
| `module` | 内部模块、算子、组件 | 圆角矩形，绿色系 |
| `worker` | 后台任务、消费任务、批处理任务 | 圆角矩形，绿色或青色系 |
| `repo` | 代码仓、目录边界、Repo 容器 | 虚线圆角矩形，浅灰背景 |
| `mq` | Kafka、RocketMQ、消息队列、异步通道 | 平行四边形，黄色系 |
| `storage` / `db` | 数据库、KV、Feature Store、离线表 | 圆柱体，紫色系 |
| `cache` | 缓存层、本地缓存、分布式缓存 | 圆柱体或内存块形状，浅紫或蓝紫系 |
| `config` | TCC、配置文件、策略、参数 | 文档形状，橙色系 |
| `external` | 外部平台、第三方服务、跨系统依赖 | 圆角矩形，红色系 |
| `function` | 函数、方法、轻量处理节点 | 椭圆，浅蓝色系 |

Repo 或边界容器应放在后层，尺寸覆盖其内部节点，并使用 `dashed=1` 表示边界而不是普通计算节点。不要把 Repo 容器与服务节点画成同一种形状，因为读者需要快速区分代码边界和运行时组件。

## 布局规则

默认采用 left-to-right 正交布局。

- 入口、客户端、上游系统放左侧。
- 核心处理链路放中间。
- 存储、MQ、外部系统放右侧或下方。
- 配置和弱依赖放在下方，并用虚线连接。
- 节点横向间距建议 220-260 px。
- 节点纵向间距建议 120-160 px。
- 常用节点宽度 160-190 px，高度 60-80 px。
- 容器节点应比内部节点外扩至少 40 px，避免导入 draw.io 后节点贴边。

边使用正交线：`rounded=0;orthogonalLoop=1;jettySize=auto;html=1;endArrow=block;endFill=1`。

- 同步调用使用实线。
- 异步消息、配置注入、可选依赖、弱依赖使用虚线。
- `async_event`、`config`、`depends_on` 默认使用虚线。
- `sync_call`、`read`、`write`、`read_write`、`deploy`、`trigger` 默认使用实线，除非用户明确要求弱关系。
- 边标签尽量短，例如 `RPC`、`IPC`、`emit`、`read/write`、`config`。

## 风格原则

- 使用低饱和工程架构图配色，避免装饰性渐变。
- 保持语义形状稳定，不为临时美观混用形状。
- 文本优先短标签，复杂解释放到正文或图外说明。
- 样式只能改变视觉表达，不能新增、删除或改写拓扑关系。
- 用户可以直接更新本文件中的配色、形状和线型偏好；拓扑 JSON 不需要随配色变化而改动。
- 如果需要可复用的语义节点类型，更新 `draw-topology-json/references/common-elements.md`；如果只是想改颜色和形状，更新本文件。
