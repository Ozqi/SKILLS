---
name: tmux-skill
description: 通过 tmux 管理长任务、TUI、SSH 和可恢复终端。创建任务窗口时默认复用用户当前 session，并沿用 tmux 配置的默认 shell。Use for tmux sessions, windows, panes, terminal inspection, long-running commands, TUI verification, SSH workspaces, and agent notifications.
---

# tmux 自动化

把 tmux 用作可观察、可恢复的终端任务管理器。短命令和普通文件操作继续使用当前环境的专用工具。

## 适用场景

- 长任务、开发服务、构建测试和日志 watcher。
- TUI 运行、键盘驱动和真实终端截图。
- SSH、多 pane 工作台和断线恢复。
- 命令结束后通知另一个 CLI Agent pane。

## 层级与用户可见性

层级固定为 `server > session > window > pane`：

- 一个 tmux server 管理多个 session。
- 一个 client 同时连接并展示一个 session。
- 当前 session 内的 window 是用户可切换的页签；pane 是 window 内的分屏。
- 其他 session 需要 `switch-client` 或重新 attach 后才能看到。

用户需要查看新任务时，默认在其当前 session 创建 window；需要同屏观察时，在目标 window 创建 pane。新 session 只用于用户明确要求、当前没有 session，或任务需要独立生命周期的场景。

## Agent 工作流

1. 创建前查看 client、session、window 和 pane：

```bash
tmux list-clients -F '#{client_name} session=#{client_session} flags=#{client_flags}'
tmux list-sessions -F '#{session_name} attached=#{session_attached} windows=#{session_windows}'
tmux list-windows -a
tmux list-panes -a -F '#{session_name}:#{window_index}.#{pane_index} #{pane_id} #{pane_current_command} #{pane_current_path}'
```

2. 从 attached client 的 `client_session` 选择用户可见 session。只有一个 attached client 时直接使用；存在多个 client 时优先选择当前 focused client，仍不明确就询问用户。
3. `TMUX_PANE` 表示 Agent 进程所在 pane，可能位于后台 session。它只用于定位 Agent 自身，不能推断用户当前可见 session。
4. 默认在所选 session 创建 window。需要用户立即看到时不加 `-d`：

```bash
session=<chosen-client-session>
tmux new-window -t "${session}:" -n <window> -c <workdir>
```

5. 创建 window 或 pane 时省略 `bash`、`zsh`、`sh` 等 shell-command，沿用 tmux 的 `default-command` / `default-shell`。先创建默认 shell，再用 `send-keys` 启动任务。
6. 只有用户明确要求、当前没有 session，或任务需要独立生命周期时才创建新 session。
7. 报告 `session:window.pane`、工作目录、日志、ETA 和下次检查时间。

## 检查节奏

- 30 秒内：优先直接执行；需要 TUI 时短等后截图一次。
- 30 秒至 5 分钟：启动后 10-30 秒首次检查。
- 5-30 分钟：1-3 分钟首次检查，之后每 3-10 分钟检查。
- 更久或耗时不确定：先确认日志、停止方式和资源风险，每 10-30 分钟检查。
- 超过预估时间且日志无变化时，先 `capture-pane` 和检查日志，再决定停止或调整。

## 常用命令

```bash
# 查看
tmux list-clients -F '#{client_name} session=#{client_session} flags=#{client_flags}'
tmux list-sessions
tmux list-windows -a
tmux list-panes -a -F '#{session_name}:#{window_index}.#{pane_index} #{pane_id} #{pane_current_command} #{pane_current_path}'
tmux display-message -p -t <target-pane> '#{pane_id} #{pane_current_path} #{pane_width}x#{pane_height} #{pane_current_command}'

# 在用户可见 session 创建；省略 shell-command
tmux new-window -t <session>: -n <window> -c <workdir>
tmux split-window -t <session>:<window> -c <workdir>
tmux split-window -h -t <target-pane> -c <workdir>
tmux select-layout -t <session>:<window> tiled

# 输入和控制
tmux send-keys -t <target-pane> '<command>' Enter
tmux send-keys -t <target-pane> C-c

# 截图和日志
tmux capture-pane -t <target-pane> -p -S -200
tmux pipe-pane -t <target-pane> -o 'cat >> /tmp/<task>.pane.log'

# 给 CLI Agent pane 发短通知。优先 paste-buffer，少用 send-keys 塞长文本。
tmux set-buffer -b agent-msg -- '<short message>'
tmux paste-buffer -t <agent-pane> -b agent-msg
tmux send-keys -t <agent-pane> Enter

# 接管和分离
tmux attach -t <session>
tmux switch-client -t <session>
tmux detach-client -s <session>
```

## 典型用法

### 在用户可见 session 启动长任务

```bash
session=<chosen-client-session>
pane="$(tmux new-window -P -F '#{pane_id}' -t "${session}:" -n <task> -c <workdir>)"
tmux send-keys -t "$pane" '<command> 2>&1 | tee /tmp/<task>.log' Enter
tmux capture-pane -t "$pane" -p -S -120
```

```text
target: <session>:<window>.<pane>
workdir: <workdir>
log: /tmp/<task>.log
eta: <预计耗时>
next-check: <下次检查时间或间隔>
```

### CLI Agent 触发通知

命令结束后把状态写入事件文件，再向 Agent pane 发送短消息。日志保留在文件中：

```bash
printf 'task=%s\nexit=%s\nlog=%s\n' "$name" "$status" "$log" > "$event"
tmux set-buffer -b agent-msg -- "任务 $name 结束，事件=$event，请读取处理。"
tmux paste-buffer -t "$agent_pane" -b agent-msg
tmux send-keys -t "$agent_pane" Enter
```

Agent 忙碌时先写事件文件，待其空闲后再投递。高频任务再考虑 listener。

### TUI 真实屏幕验证

```bash
session=<chosen-client-session>
pane="$(tmux new-window -P -F '#{pane_id}' -t "${session}:" -n <task>-tui -c <workdir>)"
tmux send-keys -t "$pane" '<run-tui-command>' Enter
tmux display-message -p -t "$pane" '#{pane_id} #{pane_width}x#{pane_height} #{pane_current_command}'
tmux capture-pane -t "$pane" -p -S -80
```

依赖鼠标、滚动或键盘输入时，用 `send-keys` 分步驱动并多次截图。完整记录写入日志。

### 多 pane 开发工作台

```bash
session=<chosen-client-session>
tmux new-window -t "${session}:" -n server -c <workdir>
tmux split-window -h -t "${session}:server" -c <workdir>
tmux new-window -t "${session}:" -n logs -c <workdir>
```

### SSH 与多主机

默认在用户可见 session 创建 `ssh` window 并按主机分 pane。同步输入只用于明确、低风险的只读命令：

```bash
tmux setw -t <session>:<window> synchronize-panes on
tmux setw -t <session>:<window> synchronize-panes off
```

### 会话恢复

tmux 支持 SSH 断线和终端关闭后的恢复。机器重启后的布局恢复依赖 `tmux-resurrect` / `tmux-continuum`；应用状态仍需自行落盘。

## 安全规则

- 默认复用用户可见 session，不创建额外 session。
- 默认复用 tmux 的 `default-shell`，不硬编码 `bash`。
- 禁止对未知 session/window/pane 执行 kill 操作。
- `synchronize-panes` 默认关闭；生产 SSH 和多主机写操作先确认。
- `capture-pane` 只表示当前终端画面；审计内容显式写日志。
- prefix、插件、主题和按键绑定以实时配置为准。
