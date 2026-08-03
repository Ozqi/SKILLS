---
name: tmux-automation
description: Manage long-running terminal tasks, TUIs, shell sessions, SSH fan-out, and terminal screenshots through tmux. Use when the user asks to run or inspect terminal UI apps, keep commands alive after disconnect, capture pane output, coordinate multiple panes/windows/sessions, operate across SSH sessions, or debug terminal behavior with real tmux state.
---

# Tmux Automation

Use tmux as an observable, recoverable terminal task manager. This skill is for agent execution workflows, not a general tmux shortcut reference.

## Workflow

1. Classify the task: long-running command, TUI verification, pane capture, log tailing, multi-session coordination, SSH observation, or synchronized input.
2. Inspect current state before creating anything:

```bash
tmux list-sessions
tmux list-windows -a
tmux list-panes -a -F '#{session_name}:#{window_index}.#{pane_index} #{pane_id} #{pane_current_command} #{pane_current_path}'
```

3. Create named sessions, windows, and panes for agent-owned work. Include a project or task slug in names, and do not reuse unknown user sessions.
4. For TUIs or interactive programs, use a fixed-size session when layout matters. Capture real terminal content with `capture-pane`; also record pane id, size, current command, and working directory when reporting results.
5. For long-running commands, report the session/window/pane target, start command, working directory, log path if any, and the attach command the user can run.
6. For SSH or multiple hosts, default to read-only diagnosis. Before write operations, confirm target host set, synchronized input state, and rollback path.
7. When finished, preserve or clean up sessions according to the user request. Never kill existing user sessions by default.

## Command Snippets

```bash
tmux new-session -d -s <session> -c <workdir>
tmux new-window -t <session> -n <window> -c <workdir>
tmux split-window -t <session>:<window> -c <workdir>
tmux send-keys -t <target-pane> '<command>' Enter
tmux capture-pane -t <target-pane> -p -S -200
tmux display-message -p -t <target-pane> '#{pane_id} #{pane_current_path} #{pane_width}x#{pane_height} #{pane_current_command}'
tmux list-panes -a -F '#{session_name}:#{window_index}.#{pane_index} #{pane_id} #{pane_current_command} #{pane_current_path}'
```

## Safety

- Do not use tmux as a privilege escalation or unattended operations platform.
- Do not enable `synchronize-panes` by default. Multi-host synchronized input is only appropriate for read-only checks or low-risk repeated commands.
- Do not run `kill-session`, `kill-window`, or `kill-pane` against unknown sessions.
- Do not treat `capture-pane` as a complete audit log. For auditable work, redirect command output to a log file.
- Do not assume the tmux prefix key. Check live bindings with:

```bash
tmux list-keys -T prefix
```

## Related Notes

- `WIKI/古法工具/Tmux.md` keeps human-facing tmux usage, oh-my-tmux, sessionx, resurrect, continuum, and tmux-cssh notes.
- This skill keeps agent execution flow and safety boundaries.
