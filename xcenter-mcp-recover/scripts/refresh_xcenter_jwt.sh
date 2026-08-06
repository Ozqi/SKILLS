#!/usr/bin/env bash
set -euo pipefail

ENV_FILE="${XCENTER_JWT_ENV_FILE:-/tmp/xcenter_jwt_env.sh}"
TOKEN_FILE="${XCENTER_JWT_TOKEN_FILE:-/tmp/xcenter_jwt_refresh.token}"
ERR_FILE="${XCENTER_JWT_ERR_FILE:-/tmp/xcenter_jwt_refresh.err}"
HEALTH_CHECK=1
UPDATE_TMUX=1
PLUGIN_DIR="${XCENTER_PLUGIN_DIR:-/home/byteide/.trae/plugins/cache/plugins-cli/xcenter-codex/local}"
EXPIRY_SKEW_SECONDS="${XCENTER_JWT_EXPIRY_SKEW_SECONDS:-300}"

usage() {
  cat <<'USAGE'
Usage: refresh_xcenter_jwt.sh [options]

Refresh XCenter MCP JWT without printing the token.

Options:
  --env-file PATH       Env file to write. Default: /tmp/xcenter_jwt_env.sh
  --token-file PATH     Private token cache path. Default: /tmp/xcenter_jwt_refresh.token
  --plugin-dir PATH     xcenter-codex plugin root. Default: active plugin cache path
  --no-health-check     Skip MCP wrapper initialize health check
  --no-tmux             Do not update tmux global environment
  -h, --help            Show this help

After running, new shells can load the refreshed env with:
  source /tmp/xcenter_jwt_env.sh
USAGE
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --env-file)
      ENV_FILE="$2"
      shift 2
      ;;
    --token-file)
      TOKEN_FILE="$2"
      shift 2
      ;;
    --plugin-dir)
      PLUGIN_DIR="$2"
      shift 2
      ;;
    --no-health-check)
      HEALTH_CHECK=0
      shift
      ;;
    --no-tmux)
      UPDATE_TMUX=0
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

looks_like_jwt() {
  local value="${1:-}"
  [[ "$value" =~ ^[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+$ ]]
}

jwt_exp_delta() {
  local token="$1"
  python3 - "$token" <<'PY'
import base64
import json
import sys
import time

token = sys.argv[1]
try:
    payload = token.split(".")[1]
    payload += "=" * (-len(payload) % 4)
    data = json.loads(base64.urlsafe_b64decode(payload.encode()))
    exp = int(data.get("exp", 0))
except Exception as exc:
    print(f"invalid:{exc}")
    sys.exit(1)

print(exp - int(time.time()))
PY
}

sanitize_token_file() {
  local path="$1"
  local value
  value="$(tr -d '\r' <"$path" | sed -e 's/^[[:space:]]*//' -e 's/[[:space:]]*$//')"
  if ! looks_like_jwt "$value"; then
    echo "[ERROR] bytedcli did not return a valid JWT" >&2
    return 1
  fi

  local delta
  delta="$(jwt_exp_delta "$value")"
  if [[ "$delta" == invalid:* ]]; then
    echo "[ERROR] failed to parse JWT expiry: $delta" >&2
    return 1
  fi
  if (( delta <= EXPIRY_SKEW_SECONDS )); then
    echo "[ERROR] refreshed JWT is expired or too close to expiry: ${delta}s left" >&2
    return 1
  fi

  printf '%s' "$value" >"$path"
  printf '%s\n' "$delta"
}

refresh_jwt() {
  rm -f "$TOKEN_FILE" "$ERR_FILE"
  umask 077
  if ! timeout "${XCENTER_JWT_TOKEN_TIMEOUT:-15}" env \
      -u USER_JWT_TOKEN \
      -u CLOUDIDE_BYTECLOUD_USER_JWT \
      BYTEDCLI_NO_AUTO_UPGRADE=1 \
      bytedcli auth get-bytecloud-jwt-token >"$TOKEN_FILE" 2>"$ERR_FILE"; then
    echo "[ERROR] failed to refresh JWT with bytedcli" >&2
    sed -n '1,40p' "$ERR_FILE" >&2 || true
    return 1
  fi
  sanitize_token_file "$TOKEN_FILE"
}

write_env() {
  local token="$1"
  local header="x-xcenter-entrance=meta_center_cn://kv_config/byterec/entrance_config/douyin,X-Jwt-Token=${token}"

  umask 077
  cat >"$ENV_FILE" <<EOF
export USER_JWT_TOKEN='${token}'
export CLOUDIDE_BYTECLOUD_USER_JWT='${token}'
export MCP_SERVER_CALL_TOOL_HEADERS='${header}'
EOF

  if (( UPDATE_TMUX )) && command -v tmux >/dev/null 2>&1 && tmux info >/dev/null 2>&1; then
    tmux set-environment -g USER_JWT_TOKEN "$token"
    tmux set-environment -g CLOUDIDE_BYTECLOUD_USER_JWT "$token"
    tmux set-environment -g MCP_SERVER_CALL_TOOL_HEADERS "$header"
    echo "[OK] updated tmux global environment"
  else
    echo "[INFO] skipped tmux global environment update"
  fi
}

health_check() {
  local wrapper="${PLUGIN_DIR}/hooks/xcenter_mcp_proxy.sh"
  if [[ ! -x "$wrapper" && ! -f "$wrapper" ]]; then
    echo "[WARN] MCP wrapper not found: $wrapper" >&2
    return 0
  fi

  local req out err len
  req='{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"xcenter-jwt-refresh"}}}'
  len="$(printf '%s' "$req" | wc -c)"
  out="$(mktemp /tmp/xcenter_mcp_health.XXXXXX.out)"
  err="$(mktemp /tmp/xcenter_mcp_health.XXXXXX.err)"

  # The proxy may log token-bearing diagnostics. Keep raw output in private temp
  # files and only print a boolean summary.
  { printf 'Content-Length: %s\r\n\r\n' "$len"; printf '%s' "$req"; } | \
    timeout "${XCENTER_MCP_HEALTH_TIMEOUT:-30}" env \
      MCP_SERVER_PSM=bytedance.mcp.xcenter_workflow_server \
      MCP_GATEWAY_REGION=CN \
      MCP_SERVER_TOOL_ALLOW_LIST='workflow_publish,workflow_create,workflow_node_resource_file_tree,workflow_node_file_read,workflow_node_resource_file_write,workflow_node_resource_list,workflow_node_resource_add,workflow_node_compile,get_workflow_node_compile_result,workflow_task_create,workflow_operator_create' \
      bash "$wrapper" >"$out" 2>"$err" || true

  if rg -q 'Available tools|running on stdio|serverInfo|@byted/mcp-proxy' "$out" "$err"; then
    echo "[OK] xcenter MCP wrapper health check passed"
  else
    echo "[WARN] xcenter MCP wrapper health check did not confirm startup" >&2
    echo "[WARN] raw health files: $out $err" >&2
    return 1
  fi
  rm -f "$out" "$err"
}

main() {
  local delta token
  delta="$(refresh_jwt)"
  token="$(cat "$TOKEN_FILE")"
  write_env "$token"

  echo "[OK] refreshed XCenter JWT; expires in ${delta}s"
  echo "[OK] wrote env file: $ENV_FILE"
  echo "[INFO] load it in a shell with: source $ENV_FILE"

  if (( HEALTH_CHECK )); then
    health_check
  fi
}

main "$@"
