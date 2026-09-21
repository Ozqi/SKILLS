---
name: canonical-code-link
description: "Create and review canonical code-location links in Markdown: workspace-relative VS Code/Cursor/Trae-style `#Lx[-Ly]` links, local VS Code protocol links, and GitHub `blob/<ref>/path#Lx-Ly` browser links. Use when users ask for clickable file/line/range links, IDE jump links, Markdown code citations, or GitHub source links."
---

# Canonical Code Link

Create stable, clickable links to source code locations. Prefer the smallest link that works in the target renderer.

## Decision Order

1. **Markdown inside a checked-out workspace / VS Code / Cursor / Trae**: use workspace-relative Markdown links with GitHub-style line fragments.
2. **Markdown rendered outside the editor but should open local VS Code**: use the VS Code protocol URL.
3. **Markdown should open code in a browser on GitHub**: use the GitHub `blob/<ref>` URL with line fragments.

If the target environment is ambiguous, ask whether the user wants local editor jump links or browser GitHub links.

## Format A: Local Workspace Markdown Links

Use this for repo notes, AI responses, review plans, and Markdown files opened in VS Code/Cursor/Trae.

```markdown
[file/path.ts](file/path.ts)
[file/path.ts:10](file/path.ts#L10)
[descriptive text](file/path.ts#L10-L20)
```

Rules:

- Use workspace-relative paths with `/` separators.
- Use 1-based line numbers: first line is `#L1`.
- Use `#Lstart-Lend` for a contiguous range.
- Encode spaces and special URL characters in the link target only: `[My File.ts](My%20File.ts#L10)`.
- Do not wrap the link itself in backticks.
- Link only to files that exist when the workspace is available; verify with file tools if needed.
- For repository Markdown, prefer this over `file://`, `vscode://`, `cursor://`, or absolute paths.

Good:

```markdown
The parser entry point is [parseRequest](src/parser.ts#L42-L68).
See [src/config/defaults.ts](src/config/defaults.ts).
```

Bad:

```markdown
`src/parser.ts#L42`
[src/parser.ts](src/parser.ts)#L42
[src/parser.ts#L42](src/parser.ts#L42)
[file](file:///Users/me/project/src/parser.ts#L42)
```

## Format B: Markdown to Local VS Code

Use this when the Markdown is rendered by a browser, external note app, issue tracker, or another app and the click should launch local VS Code.

```markdown
[label](vscode://file/{absolute-path}:line:column)
```

Examples:

```markdown
[Open in VS Code](vscode://file/Users/bytedance/Proj/md/src/parser.ts:42:1)
[Windows file](vscode://file/c:/myProject/src/parser.ts:42:1)
[VS Code Insiders](vscode-insiders://file/Users/me/project/src/parser.ts:42:1)
```

Rules:

- Use an absolute local path.
- Include line and column when known: `:line:column`.
- Encode spaces in the URL path.
- Do not commit machine-specific `vscode://file/...` links into portable repo documentation unless the user explicitly wants local-machine-only links.
- `file://...#L10` is less reliable for editor jumps; prefer `vscode://file/...:10:1` for external-to-VS-Code links.

## Format C: Markdown to GitHub Browser Source

Use this when the link should open code on GitHub in a browser.

```markdown
[label](https://github.com/{owner}/{repo}/blob/{ref}/{path}#Lline)
[label](https://github.com/{owner}/{repo}/blob/{ref}/{path}#Lstart-Lend)
```

Examples:

```markdown
[parser.ts line 42](https://github.com/acme/project/blob/main/src/parser.ts#L42)
[request parser range](https://github.com/acme/project/blob/1a2b3c4/src/parser.ts#L42-L68)
```

Rules:

- Use a commit SHA for durable citations: `blob/<commit>/<path>#L10-L20`.
- Use a branch name such as `main` only when the link should track moving code.
- Use `/blob/`, not `/tree/`, for files.
- URL-encode path segments with spaces or special characters.
- For private repositories, only create links if the audience has access.

## Optional Editor Protocol Variants

Only use these when the user asks for a specific editor target:

```markdown
[Open in Cursor](cursor://file/Users/me/project/src/parser.ts:42:1)
[Open in Trae](trae://file/Users/me/project/src/parser.ts:42:1)
[Open in Trae CN](trae-cn://file/Users/me/project/src/parser.ts:42:1)
```

Prefer Format A for portable project Markdown unless a custom protocol is explicitly needed.

## Workflow

1. Identify target: workspace Markdown, local VS Code protocol, or GitHub browser.
2. Resolve the file path:
   - workspace Markdown: path relative to the workspace root or current Markdown file, whichever the renderer expects;
   - VS Code protocol: absolute local path;
   - GitHub: repository-relative path under `blob/<ref>/`.
3. Verify the line range when possible; do not invent line numbers.
4. Encode URL target path characters, but keep display text human-readable.
5. Emit one link per non-contiguous range.

## Quick Templates

```markdown
<!-- Local workspace / IDE Markdown -->
[<label>](<relative/path>#L<start>-L<end>)

<!-- External Markdown to local VS Code -->
[<label>](vscode://file/<absolute/path>:<line>:<column>)

<!-- Markdown to GitHub browser -->
[<label>](https://github.com/<owner>/<repo>/blob/<ref>/<relative/path>#L<start>-L<end>)
```

## References

- VS Code URL handler: https://code.visualstudio.com/docs/configure/command-line#_opening-vs-code-with-urls
- VS Code/Copilot canonical Markdown file links: https://github.com/microsoft/vscode-copilot-chat/pull/1803
- VS Code Markdown range link support: https://github.com/microsoft/vscode/pull/296821
