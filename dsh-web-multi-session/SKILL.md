---
name: dsh-web-multi-session
description: Inspect and coordinate multiple DeepSeek Harness Web sessions. Use when the user wants to list or read sessions, check another Agent task, monitor several conversations, send a message to another session, or connect external automation to a DSH session.
---

# DSH Web Multi-Session

用于在同一个 DSH workspace 内操作多个普通 Session：

- 查找 Session，读取最近消息、历史事件和任务状态；
- 向另一个 Session 排队消息，或在明确要求时 steer 正在运行的任务；
- 让本机定时器、脚本或 CI 通过 DSH Web API 向指定 Session 投递通知；
- 区分“已投递、运行中、完成、失败和状态未知”。

## 什么时候使用

用户要求查看其他 DSH 会话、了解另一个 Agent 在做什么、跨 Session 传话、监控多个任务，或让外部自动化通知 DSH 窗口时使用。

## 怎么做

1. 优先使用 `session_list`、`session_search`、`session_messages`、`session_event_*` 和 `send_session_message`。
2. 直接子 Agent 使用 `list_agents`、`send_message`、`interrupt_agent`，不要当普通 Session 操作。
3. 外部进程无法调用 Agent 工具时，才使用认证后的本机 DSH Web API；默认使用 `queue`。
4. `steer`、cancel、修改队列、批量消息和无关历史读取必须先获得明确授权。

只读取完成任务所需的最小内容。不要记录或传播 DSH token、Cookie、无关 Session 内容和敏感信息。API 接受消息只表示已投递，不表示目标已经处理或完成。
