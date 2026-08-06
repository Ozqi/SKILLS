---
name: tmux-skill
description: 通过 tmux 管理长时间运行命令、TUI、Shell 会话、SSH 多主机、终端截图、定时检查、CLI Agent 触发通知和可恢复 Agent 工作台。Use when the user asks to run or inspect terminal UI apps, keep commands alive after disconnect, capture pane output, coordinate sessions/windows/panes, operate across SSH sessions, schedule periodic checks for long-running commands, notify an agent pane after commands finish, or debug terminal behavior with real tmux state.
---

# tmux 自动化

把 tmux 当作可观察、可恢复的终端任务管理器。它适合承载长任务、TUI、远程 SSH、日志观察和需要人工接管的 CLI Agent 会话。短命令、一次性文件读写和普通搜索仍优先使用当前环境的专用工具。

## 适用场景

- 长时间运行：开发服务器、训练/构建/测试、日志 tail、持续 watcher。
- TUI 验证：Bubble Tea、curses、终端全屏应用、交互式调试。
- 可恢复工作台：用户可能断开 SSH、本地终端可能关闭、任务需要稍后继续看。
- 多 pane 协作：一个 pane 跑服务，一个 pane 跑测试，一个 pane 看日志。
- SSH 多主机：并排查看多台机器状态，谨慎使用同步输入。
- Agent 观测：需要通过 `capture-pane` 看真实终端屏幕，或让用户用 `tmux attach` 接管。
- Agent 触发：命令窗口执行结束后，通过事件文件和 listener pane 通知另一个 CLI Agent pane。

## 基本模型

- **server**：tmux 后台服务。
- **session**：一组工作区，例如一个项目或一次排查。
- **window**：session 内的页签，例如 `agent`、`server`、`tests`、`logs`。
- **pane**：window 内的分屏终端。
- **target**：常用写法为 `<session>:<window>.<pane>`，也可以用 pane id，例如 `%3`。

默认 prefix 通常是 `Ctrl-b`。如果需要把 prefix 发给嵌套 tmux 或远端 tmux，常见按法是 `Ctrl-b Ctrl-b`。不要假设用户配置；先查实时绑定。

```bash
tmux list-keys -T prefix
```

## Agent 工作流

1. 先分类：长命令、TUI、pane 截图、日志观察、多 session 协调、SSH 观察、同步输入。
2. 估算耗时：区分秒级、分钟级、十分钟级、小时级和不确定任务；派发命令前心里要有大致运行时间。
3. 长时间或高风险任务先审慎检查命令、工作目录、输入输出、日志路径、资源占用和停止方式，再派发到 tmux。
4. 创建前先看现有状态，避免复用不明来源的用户 session：

```bash
tmux list-sessions
tmux list-windows -a
tmux list-panes -a -F '#{session_name}:#{window_index}.#{pane_index} #{pane_id} #{pane_current_command} #{pane_current_path}'
```

5. 新建 agent 自己的 session/window/pane。命名带项目或任务 slug，例如 `md-docusaurus`、`5hagent-tui`。
6. TUI 或布局敏感任务使用固定尺寸，例如 120x40；报告时记录 pane id、尺寸、当前命令和工作目录。
7. 长任务要给出 session/window/pane、启动命令、工作目录、日志路径、预计耗时、首次检查时间、后续检查间隔和用户 attach 命令。
8. SSH 或多主机默认做只读诊断。涉及写操作前确认主机集合、同步输入状态和回滚办法。
9. 结束时按用户要求保留或清理。默认保留 agent 创建的长期 session，方便人工接管。

## 时间观念和检查节奏

Agent 下发命令后要主动管理时间。不要把长任务丢进 tmux 后立即反复查看，也不要长期不看。

- **秒级任务**（约 0-30 秒）：优先直接执行；需要 TUI 或保活时放 tmux，短等后抓一次 pane。
- **分钟级任务**（约 30 秒-5 分钟）：放 tmux 时先等一个合理启动窗口，例如 10-30 秒；再检查是否正常进入执行状态。
- **十分钟级任务**（约 5-30 分钟）：派发前确认日志、停止方式和资源风险；设置首次检查点，例如 1-3 分钟；后续按 3-10 分钟间隔检查。
- **小时级或不确定任务**：派发前做更严格检查，必要时先跑 dry-run、小样本或只读诊断；设置较长定时检查，例如 10-30 分钟；报告预计完成窗口和人工接管方式。
- **卡住判断**：超过预估时间较多、日志长时间无变化、CPU/IO 明显异常、重复输出同一错误时，先 capture-pane 和查看日志，再决定是否停止或调整。
- **检查记录**：长任务报告里写清“已启动时间、上次检查时间、下次建议检查时间、当前状态、最近日志摘要”。
- **定时检查任务**：如果环境支持等待、提醒或计划任务，给自己设置下一次检查；如果只能返回给用户，就明确写出 `next-check`，避免短时间密集轮询。

长任务派发前最小检查清单：

```text
command: 是否确认命令、参数和目标环境
workdir: 是否在正确目录
log: 是否有日志或 tee 文件
stop: 如何安全停止，是否可 C-c
risk: 是否涉及生产、删除、覆盖、批量写入或高资源占用
eta: 预计耗时和首次检查点
```

## 常用命令

```bash
# 查看
tmux list-sessions
tmux list-windows -a
tmux list-panes -a -F '#{session_name}:#{window_index}.#{pane_index} #{pane_id} #{pane_current_command} #{pane_current_path}'
tmux display-message -p -t <target-pane> '#{pane_id} #{pane_current_path} #{pane_width}x#{pane_height} #{pane_current_command}'

# 创建和布局
tmux new-session -d -s <session> -c <workdir>
tmux new-session -d -s <session> -n <window> -x 120 -y 40 -c <workdir>
tmux new-window -t <session> -n <window> -c <workdir>
tmux split-window -t <session>:<window> -c <workdir>
tmux split-window -h -t <target-pane> -c <workdir>
tmux select-layout -t <session>:<window> tiled
tmux rename-window -t <session>:<window> <name>

# 输入和控制
tmux send-keys -t <target-pane> '<command>' Enter
tmux send-keys -t <target-pane> C-c
tmux send-keys -t <target-pane> C-d

# 截图和上下文
tmux capture-pane -t <target-pane> -p -S -200
tmux capture-pane -t <target-pane> -p -S -2000 > /tmp/<task>.pane.txt
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

### 长任务放后台

```bash
tmux new-session -d -s <task> -n run -c <workdir>
tmux send-keys -t <task>:run.0 '<command> 2>&1 | tee /tmp/<task>.log' Enter
tmux capture-pane -t <task>:run.0 -p -S -120
```

报告给用户：

```text
tmux attach -t <task>
log: /tmp/<task>.log
pane: <task>:run.0
eta: <预计耗时>
next-check: <下次检查时间或间隔>
```

### CLI Agent 触发通知

CLI Agent 没有 API 时，把通知当作终端输入。默认只做一件事：命令结束后写事件文件，再给 Agent pane 粘贴一句短消息。

规则：

- 日志和状态写文件；不要把大段输出塞进 Agent 输入框。
- 通知只放事件文件路径和动作请求。
- 用 `paste-buffer` 粘贴，用 `send-keys Enter` 提交。
- 频繁、多任务、需要重试时，再加 listener pane；默认先不用。

最小 wrapper：

```bash
notify_agent_event() {
  agent_pane="$1"
  shift
  name="$1"
  shift
  log="/tmp/${name}.log"
  event="/tmp/${name}.event"

  start=$(date +%s)
  "$@" 2>&1 | tee "$log"
  status=${PIPESTATUS[0]}
  end=$(date +%s)

  cat > "$event" <<EOF
task=$name
exit=$status
duration=$((end-start))s
workdir=$(pwd)
log=$log
next_action=请读取事件和日志，检查结果并决定下一步。
EOF

  tmux set-buffer -b agent-msg -- "任务 $name 结束，事件=$event，请读取处理。"
  tmux paste-buffer -t "$agent_pane" -b agent-msg
  tmux send-keys -t "$agent_pane" Enter

  return "$status"
}
```

使用：

```bash
notify_agent_event dev:agent.0 build npm run build
```

如果 Agent 正在忙，直接通知可能插入到不合适的时机。需要更稳时，先只写事件文件，等 Agent 空闲后人工或 listener 再投递。FIFO 不做默认方案；没有 reader 时会阻塞命令结束流程。

### TUI 真实屏幕验证

```bash
tmux new-session -d -s <task>-tui -n ui -x 120 -y 40 -c <workdir>
tmux send-keys -t <task>-tui:ui.0 '<run-tui-command>' Enter
tmux display-message -p -t <task>-tui:ui.0 '#{pane_id} #{pane_width}x#{pane_height} #{pane_current_command}'
tmux capture-pane -t <task>-tui:ui.0 -p -S -80
```

如果 TUI 依赖鼠标、滚动或键盘输入，使用 `send-keys` 分步驱动并多次截图。截图只代表当前屏幕；需要完整记录时写日志或保存应用输出。

### 多 pane 开发工作台

```bash
tmux new-session -d -s <project> -n agent -c <workdir>
tmux new-window -t <project> -n server -c <workdir>
tmux new-window -t <project> -n logs -c <workdir>
tmux split-window -h -t <project>:server.0 -c <workdir>
tmux select-layout -t <project>:server tiled
```

推荐 window 命名：

- `agent`：CLI Agent 或交互式任务。
- `server`：本地开发服务。
- `tests`：测试、构建、watcher。
- `logs`：日志、监控、tail。
- `ssh`：远端诊断。

### SSH 与多主机

```bash
tmux new-session -d -s <task>-ssh -n hosts
tmux send-keys -t <task>-ssh:hosts.0 'ssh host1' Enter
tmux split-window -h -t <task>-ssh:hosts.0
tmux send-keys -t <task>-ssh:hosts.1 'ssh host2' Enter
tmux select-layout -t <task>-ssh:hosts tiled
```

同步输入只在明确、低风险、可预期的场景启用，常用于 `hostname`、`uptime`、`df -h` 这类只读检查：

```bash
tmux setw -t <session>:<window> synchronize-panes on
tmux setw -t <session>:<window> synchronize-panes off
```

批量删除、重启、发布、覆盖配置前关闭同步输入并逐台确认。

### 会话恢复

tmux 可以抵抗 SSH 断线和本地终端关闭。机器重启后的布局恢复依赖 `tmux-resurrect` / `tmux-continuum` 等插件；它们通常恢复 session、window、pane、路径、部分命令和可选屏幕内容。进程内存状态、网络连接和运行时上下文需要应用自己落盘。

## 安全规则

- 不把 tmux 当提权、无人值守运维或绕过审批的平台。
- 不默认启用 `synchronize-panes`。
- 不对未知 session/window/pane 执行 `kill-session`、`kill-window`、`kill-pane`。
- 不把 `capture-pane` 当完整审计日志；需要审计时显式写日志文件。
- 不假设 prefix、插件、主题和用户 key binding。
- 不把长任务混进用户已有 session；新建带任务名的 agent-owned session。
- 高风险命令、生产 SSH、多主机写操作和 destructive git 操作先确认。
