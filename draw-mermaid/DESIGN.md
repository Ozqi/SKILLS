# Mermaid Design Profiles

This file guides visual style for Mermaid diagrams. Use it only after the diagram semantics and Mermaid diagram type are clear.

Concrete Mermaid theme snippets live in `references/styles.md`.

## Style Rules

- Style must not add, remove, or rewrite topology facts.
- Prefer readable structure over decoration.
- Keep labels short enough to render without manual `<br/>`.
- Do not overuse emoji or decorative symbols.
- Keep punctuation ASCII in labels.
- Use `%%{init: ...}%%` before the diagram for Mermaid theme settings.
- Use `classDef` for semantic node types when the diagram contains several roles.

## Gray Whiteboard

Use for neutral technical explanation, wiki notes, and internal architecture sketches.

## White Hand-Drawn Board

Use for lightweight sketches, exploratory notes, and informal design discussion.

## Green Natural Board

Use for soft tutorial diagrams, conceptual workflows, and reading-friendly notes.

## Research Diagram

Use for paper notes, method overviews, experiment pipelines, and formal technical writing.

Research style constraints:

- Main border: `#2F5496`.
- Secondary fill: `#ED7D31`.
- Accent: `#70AD47`.
- Background: `#FFFFFF`.
- Font: Arial or Times New Roman.
- Font size: 12pt.
- Bold: only start and end nodes.
- Border width: 2px.
- Node corner radius target: 5px when the renderer supports it.
- Arrow type: standard solid arrow.
- Line width target: 1.5px when the renderer supports it.

Read `references/styles.md` when the final output needs a concrete `%%{init: ...}%%` snippet or `classDef` block.
