---
name: code-commit-style
description: "Write, review, or normalize Git commit messages with Conventional Commits. Use when the user asks to commit code, name a commit, draft or revise a commit message, squash commits, review commit history, or enforce `type(scope): description` style. Inspect the actual diff before describing a commit; do not commit unless the user explicitly asks."
---

# Code Commit Style

Use Conventional Commits to make commit intent readable and machine-processable.

## Format

```text
<type>[optional scope][optional !]: <description>

[optional body]

[optional footer(s)]
```

Common types:

- `feat`: add user-visible behavior or capability.
- `fix`: correct faulty behavior.
- `docs`: change documentation only.
- `style`: change formatting without changing behavior.
- `refactor`: restructure code without adding a feature or fixing a bug.
- `perf`: improve performance.
- `test`: add or change tests.
- `build`: change build tooling or dependencies.
- `ci`: change CI configuration or workflows.
- `chore`: perform maintenance not covered above.
- `revert`: revert an earlier commit.

## Workflow

1. Read repository-specific Git and commit rules first; they override this Skill.
2. Inspect `git status`, the relevant diff, and staged diff. Never infer a commit message from filenames alone.
3. Preserve unrelated or unknown changes. Do not stage, restore, stash, or include them.
4. Identify the single primary intent. If the diff contains independent intents, recommend splitting it instead of hiding them under a vague message.
5. Choose the narrowest accurate `type` and an optional stable noun for `scope` such as `api`, `parser`, `ui`, or `docs`.
6. Write a short imperative description of what changed. Prefer concrete behavior over implementation trivia.
7. Add a body only when the reason, trade-off, migration, or non-obvious consequence matters.
8. Mark incompatible changes with `!` and explain them in a `BREAKING CHANGE:` footer.
9. Add issue or attribution trailers only when supported by repository context.
10. Before committing, show or verify the exact paths that will be included. Commit only when the user explicitly requested the commit action.

## Style Rules

- Use lowercase `type` and usually lowercase `scope`.
- Do not end the subject with a period.
- Keep the subject concise; follow a repository limit when one exists.
- Use one language consistently within a message. Match the repository's recent convention when clear.
- Describe the durable change, not the editing process: avoid `update stuff`, `misc fixes`, `WIP`, `changes`, or tool-generated narration.
- One commit should express one coherent change.
- A documentation-only knowledge-base change should normally use `docs:`.
- A PR squash message should follow the same format and summarize the PR's long-term meaning.

## Breaking Changes and Footers

```text
refactor(cache)!: replace legacy metadata format

Migrate cache metadata before starting the new version.

BREAKING CHANGE: legacy metadata files are no longer read.
Refs: #456
Reviewed-by: Alice
```

Use Git trailer-style footers. Do not invent issue IDs, reviewers, co-authors, or breaking-change claims.

## Examples

```text
feat(parser): add array parsing
fix(api): handle empty response
docs(git): document conventional commits
refactor(cache)!: replace legacy metadata format
test(sync): cover nested directory mapping
ci: run metadata checks on pull requests
```

## Review Checklist

- The message matches the actual diff.
- `type` reflects the primary intent.
- `scope` adds useful information rather than repeating the repository name.
- The subject is imperative, specific, and free of process narration.
- Breaking behavior is explicitly marked and explained.
- Unrelated changes are split or excluded.
- No unsupported metadata or attribution was invented.
