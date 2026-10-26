---
name: jupyter-style-skill
description: "Apply a Jupyter Notebook-inspired visual style to an interface or document. Use only when the user explicitly asks for Jupyter style, notebook style, or names `jupyter-style-skill`; do not activate for generic coding, data science, documentation, dashboard, or notebook tasks."
---

# Jupyter Style

Create a calm, cell-oriented interface inspired by Jupyter Notebook. Reproduce the interaction language, not Jupyter branding or an exact product clone.

## Direction

- Make the working document the visual center: a narrow notebook column on a quiet neutral canvas.
- Favor utility over decoration. Use flat surfaces, thin borders, compact controls, and little or no shadow.
- Organize content as an ordered sequence of editable inputs and rendered outputs.
- Keep the interface familiar to technical users without requiring actual notebook execution semantics unless requested.

## Visual System

- Use off-white or very light gray page surfaces with white cells and cool gray borders.
- Use a restrained orange accent reminiscent of notebook workflows, plus semantic blue, green, amber, and red for selection, success, running, warning, and error states.
- Use a readable sans-serif for navigation and prose; use a dependable monospace stack for code, prompts, logs, and tabular output.
- Keep corners subtle, generally `0–4px`. Avoid glass effects, decorative gradients, oversized typography, floating card grids, and heavy shadows.
- Prefer compact spacing and information density while keeping code and output comfortably readable.

## Notebook Anatomy

- **Header:** Show a compact title, save or sync status, kernel/runtime state, and a restrained action area.
- **Menu and toolbar:** Use small, familiar controls with icons, labels or tooltips, clear disabled states, and separators between action groups.
- **Cell rail:** Reserve a narrow left gutter for execution prompts such as `In [3]:`, `In [*]:`, and `Out[3]:` when execution semantics exist.
- **Input cell:** Give the active cell a clear border or left accent. Keep inactive cells visually quiet.
- **Markdown cell:** Render as document content rather than a form field; preserve generous heading and paragraph rhythm inside the compact notebook layout.
- **Output cell:** Align output with its input, distinguish stdout, rich results, tables, charts, and errors without wrapping each in an unrelated card.
- **Status bar:** If needed, keep runtime, language, cursor, and connection information compact and secondary.

## Interaction States

- Make edit mode and command/selection mode visibly different through border color, gutter accent, or focus treatment.
- Show running cells with a stable progress state such as `[*]`; do not use distracting full-page animation.
- Keep execution order visible when it matters, but never invent execution counts for static content.
- Present errors inline with strong contrast, a concise summary, and readable monospace traceback details.
- Put cell actions near the selected cell or in the toolbar; avoid exposing every action on every inactive cell.
- Preserve keyboard focus, visible hover states, and predictable insertion points between cells.

## Responsive Behavior

- On narrow screens, collapse menus and secondary metadata before shrinking the content to illegibility.
- Reduce or hide the prompt gutter only when necessary; retain execution state in a compact accessible label.
- Allow code, tables, and tracebacks to scroll horizontally rather than forcing destructive wrapping.
- Keep primary run, stop, save, and add-cell actions reachable without covering the active cell.

## Boundaries

- Do not copy Jupyter logos, trademarks, exact assets, or pixel-identical layouts unless the user supplies and authorizes them.
- Do not add notebook kernels, code execution, persistence, or collaboration behavior solely to achieve the visual style.
- Reuse the host application's components, tokens, icon library, and accessibility conventions where possible.
- Preserve syntax highlighting already used by the project; tune its palette only when required for contrast and cohesion.
- When the user requests only a static page or document, use notebook visual cues without pretending controls are functional.

## Checks

- The notebook or working document is the first visual priority.
- Active, inactive, running, successful, and error states are distinguishable without relying only on color.
- Code, Markdown, tables, plots, logs, and tracebacks remain readable.
- Keyboard focus is visible, controls have accessible names, and contrast remains sufficient.
- Desktop and mobile layouts avoid clipped controls, overlapping prompts, and unreadably narrow code cells.
