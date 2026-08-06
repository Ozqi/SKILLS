#!/usr/bin/env bash
set -euo pipefail

PSM="bytedance.mcp.xcenter_workflow_server"
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
REFRESH_SCRIPT="${XCENTER_REFRESH_SCRIPT:-${SCRIPT_DIR}/refresh_xcenter_jwt.sh}"
DO_REFRESH=1
DRY_RUN=0
SIGNAL="TERM"

usage() {
  cat <<'USAGE'
Usage: recover_xcenter_mcp.sh [options]

Refresh XCenter JWT and terminate only XCenter workflow MCP proxy processes.
This does not restart TraeX stdio transport; trigger TraeX /mcp reconnect after it runs.

Options:
  --dry-run      List matching PIDs without terminating them
  --no-refresh   Skip JWT refresh
  -h, --help     Show this help
USAGE
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --dry-run)
      DRY_RUN=1
      shift
      ;;
    --no-refresh)
      DO_REFRESH=0
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "[ERROR] unknown option: $1" >&2
      usage >&2
      exit 2
      ;;
  esac
done

refresh_jwt() {
  if [[ -x "$REFRESH_SCRIPT" ]]; then
    "$REFRESH_SCRIPT"
    return
  fi
  if [[ -f "$REFRESH_SCRIPT" ]]; then
    bash "$REFRESH_SCRIPT"
    return
  fi

  cat >&2 <<EOF
[ERROR] refresh helper not found: $REFRESH_SCRIPT
[ERROR] Use an equivalent no-token-printing JWT refresh path, then rerun with --no-refresh.
EOF
  return 1
}

cmdline_for_pid() {
  local pid="$1"
  if [[ -r "/proc/$pid/cmdline" ]]; then
    tr '\0' ' ' <"/proc/$pid/cmdline" | sed 's/[[:space:]]*$//'
  else
    echo "<unreadable>"
  fi
}

find_xcenter_pids() {
  local environ pid
  for environ in /proc/[0-9]*/environ; do
    [[ -r "$environ" ]] || continue
    if tr '\0' '\n' <"$environ" 2>/dev/null | grep -Fxq "MCP_SERVER_PSM=$PSM"; then
      pid="${environ#/proc/}"
      pid="${pid%/environ}"
      [[ "$pid" != "$$" ]] || continue
      printf '%s\n' "$pid"
    fi
  done | sort -n -u
}

terminate_pids() {
  local pids=("$@")
  local pid

  if (( ${#pids[@]} == 0 )); then
    echo "[INFO] no xcenter workflow MCP proxy processes found"
    return 0
  fi

  echo "[INFO] matched xcenter workflow MCP proxy PIDs: ${pids[*]}"
  for pid in "${pids[@]}"; do
    echo "[INFO] pid=$pid cmd=$(cmdline_for_pid "$pid")"
  done

  if (( DRY_RUN )); then
    echo "[OK] dry run complete; no processes terminated"
    return 0
  fi

  for pid in "${pids[@]}"; do
    if kill "-$SIGNAL" "$pid" 2>/dev/null; then
      echo "[OK] sent $SIGNAL to pid=$pid"
    else
      echo "[WARN] failed to signal pid=$pid; it may have exited" >&2
    fi
  done
}

main() {
  local pids_text
  local -a pids=()

  if (( DO_REFRESH )); then
    refresh_jwt
  else
    echo "[INFO] skipped JWT refresh"
  fi

  pids_text="$(find_xcenter_pids)"
  if [[ -n "$pids_text" ]]; then
    while IFS= read -r pid; do
      [[ -n "$pid" ]] && pids+=("$pid")
    done <<<"$pids_text"
  fi

  terminate_pids "${pids[@]}"

  cat <<'EOF'
[NEXT] Trigger TraeX /mcp reconnect for the XCenter workflow MCP server.
[NEXT] Then verify with a low-risk XCenter MCP call such as workflow_node_resource_list.
EOF
}

main "$@"
