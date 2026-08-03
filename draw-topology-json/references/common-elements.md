# Topology Common Elements

Use this reference when a topology needs reusable semantic node types. These types describe what a node is in the system. They do not define color, stroke, draw.io XML, Mermaid syntax, or rendering style.

## Node Types

| 类型 | 用途 | 常见 label |
| --- | --- | --- |
| `service` | 在线服务、系统、核心进程、API 服务 | `UserService`, `IndexService`, `Gateway` |
| `module` | 内部模块、算子、组件、处理阶段 | `Ranker`, `Feature Join`, `build_instance Op` |
| `repo` | 代码仓、目录边界、工程边界 | `Repo: feature-center`, `package: runtime` |
| `mq` | 消息队列、异步 topic、事件通道 | `Kafka`, `RocketMQ`, `trigger topic` |
| `storage` | 通用存储、KV、对象存储、Feature Store | `Feature Store`, `Redis`, `S3` |
| `db` | 数据库、在线表、离线表、数仓表 | `MySQL`, `TBase`, `Hive Table` |
| `cache` | 缓存层、本地缓存、分布式缓存 | `Redis Cache`, `Local Cache` |
| `config` | 配置、策略、参数、规则文件 | `TCC Config`, `YAML Config`, `Strategy` |
| `external` | 外部平台、第三方服务、跨系统依赖 | `Dorado`, `MetaCenter`, `Payment Provider` |
| `function` | 函数、方法、轻量处理节点 | `ocf_read_fast`, `parse_config()` |
| `client` | 调用方、用户入口、上游客户端 | `Web Client`, `Fountain DAG`, `SDK` |
| `gateway` | 网关、代理、入口路由 | `API Gateway`, `Nginx`, `Envoy` |
| `worker` | 后台任务、消费任务、批处理任务 | `Flink Job`, `Worker`, `Cron Job` |

## Edge Types

| 关系 | 用途 | 常见 label |
| --- | --- | --- |
| `sync_call` | 同步调用、RPC、HTTP 调用 | `RPC`, `HTTP`, `call` |
| `async_event` | 异步消息、事件发送、订阅消费 | `emit`, `consume`, `publish` |
| `read` | 读取数据 | `read`, `lookup`, `scan` |
| `write` | 写入数据 | `write`, `upsert`, `append` |
| `read_write` | 同一关系包含读写 | `read/write` |
| `config` | 配置注入、参数引用、策略读取 | `config`, `load` |
| `depends_on` | 弱依赖、构建依赖、运行依赖 | `depends`, `optional` |
| `deploy` | 部署、发布、启动任务 | `deploy`, `start` |
| `trigger` | 触发、回调、变更通知 | `trigger`, `callback` |

## JSON Pattern

Use stable semantic `type` values in the topology JSON. Renderers map `type` to shapes and styles later.

```json
{
  "拓扑": "Feature Pipeline Architecture",
  "节点": [
    {
      "id": "repo",
      "名称": "Repo: feature-center",
      "类型": "repo",
      "说明": "代码仓和工程边界"
    },
    {
      "id": "client",
      "名称": "Fountain DAG",
      "类型": "client"
    },
    {
      "id": "builder",
      "名称": "build_instance Op",
      "类型": "module"
    },
    {
      "id": "mq",
      "名称": "Kafka / MQ",
      "类型": "mq"
    },
    {
      "id": "store",
      "名称": "Feature Store",
      "类型": "storage"
    },
    {
      "id": "tcc",
      "名称": "TCC Config",
      "类型": "config"
    }
  ],
  "边": [
    {
      "from": "client",
      "to": "builder",
      "关系": "sync_call",
      "label": "sample"
    },
    {
      "from": "builder",
      "to": "mq",
      "关系": "async_event",
      "label": "emit"
    },
    {
      "from": "builder",
      "to": "store",
      "关系": "read_write",
      "label": "read/write"
    },
    {
      "from": "tcc",
      "to": "builder",
      "关系": "config",
      "label": "config"
    }
  ],
  "视图": [
    {
      "id": "repo_boundary",
      "名称": "Repo 边界",
      "类型": "boundary",
      "包含节点": ["client", "builder", "mq", "store", "tcc"],
      "边界节点": "repo"
    }
  ]
}
```

## Renderer Boundary

- `类型` and `关系` are semantic contracts shared by renderers.
- `DESIGN.md` in the target drawing skill maps these semantic contracts to colors, shapes, line styles, and layout.
- Do not put color, stroke, fill, Mermaid syntax, draw.io XML, or Graphviz DOT details in the topology JSON.
- If a target renderer needs coordinates, place them in a renderer-specific profile or generated intermediate, not in the canonical topology JSON unless the user explicitly asks for fixed layout.
