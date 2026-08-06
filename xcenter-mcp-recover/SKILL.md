---
name: xcenter-mcp-recover
description: Recover TraeX XCenter workflow MCP when calls fail due to stale JWT or stale stdio proxy state; refresh credentials, terminate only matching XCenter workflow MCP proxy processes, reconnect through TraeX /mcp, and verify with a low-risk MCP call.
---

# XCenter MCP Recover

Use this when TraeX XCenter workflow MCP tools fail after credentials expire, when the proxy keeps using an old JWT, or when the user asks to recover/reconnect XCenter MCP. This is for the active TraeX runtime, not legacy Trae CLI or OpenAPI fallback flows.

## Safety Rules

- Do not print JWTs, auth headers, or full token-bearing environment values.
- Do not use OpenAPI fallback. Recover the MCP path instead.
- Do not kill generic MCP proxies. Only terminate processes whose environment contains `MCP_SERVER_PSM=bytedance.mcp.xcenter_workflow_server`.
- Redact token diagnostics before sharing logs. Prefer boolean status and expiry seconds over raw values.
- Use low-risk verification: list/read/status calls only. Do not publish, write, compile, or mutate workflow state just to verify recovery.
- Shell can refresh credentials and clear stale proxy processes, but it cannot directly restart TraeX's current stdio transport. The user or agent must trigger TraeX `/mcp` reconnect after cleanup.

## Procedure

1. Refresh the XCenter JWT with the bundled helper:
   ```bash
   scripts/refresh_xcenter_jwt.sh
   ```
   The helper updates `USER_JWT_TOKEN`, `CLOUDIDE_BYTECLOUD_USER_JWT`, and `MCP_SERVER_CALL_TOOL_HEADERS` for new shells or the active tmux environment. You may override it with `XCENTER_REFRESH_SCRIPT=/path/to/refresh.sh`.

2. Terminate only stale XCenter workflow MCP proxy processes. Prefer the bundled helper:
   ```bash
   scripts/recover_xcenter_mcp.sh
   ```
   The helper refreshes JWT first, scans `/proc/*/environ`, selects only processes with `MCP_SERVER_PSM=bytedance.mcp.xcenter_workflow_server`, and sends `TERM` only to those PIDs.

3. Instruct the user or active agent to reconnect from inside TraeX:
   ```text
   /mcp
   ```
   Use the reconnect action for the XCenter workflow MCP server. Do not claim the shell command restarted the current stdio transport.

4. Verify with a minimal XCenter MCP call after reconnect. Prefer one of:
   - `workflow_node_resource_list` for a known workflow/node.
   - `workflow_node_resource_file_tree` for a known workflow/node.
   - `get_workflow_node_compile_result` only when checking existing compile status is the requested task.

5. Report only sanitized evidence: refresh succeeded, number of matching proxy PIDs terminated, `/mcp` reconnect was requested or completed, and the low-risk MCP call result. Do not include raw token material or token-bearing headers.

## Helper Notes

- The helper accepts `--dry-run` to show matching PIDs without terminating them.
- The helper accepts `--no-refresh` if credentials were already refreshed by a trusted no-token-printing command.
- If no matching PIDs are found, continue to TraeX `/mcp` reconnect; the stale state may be held by the current stdio transport rather than a visible child process.
