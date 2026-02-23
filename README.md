<p align="center">
  <img src="assets/logo.svg" width="80" alt="Bean logo"/>
</p>

<h1 align="center">Bean</h1>

<p align="center">
  <strong>See your Python codebase.</strong><br/>
  Radial architecture graphs, diff visualization, trace explorer, and quality dashboards — all from a single command.
</p>

<p align="center">
  <img src="assets/radial-view.png" width="700" alt="Bean radial architecture view"/>
</p>

## Install

```bash
pip install -e .
```

## Usage

```bash
# Visualize any Python project
bean /path/to/project

# Compare against a git ref
bean --diff main /path/to/project
bean --diff HEAD~3 .

# Options
bean -o output.html .        # custom output path
bean --no-open .             # don't auto-open browser
```

## Views

**Radial** — Concentric dependency graph. Modules arranged by depth, colored by layer, sized by symbol count. Click to inspect functions, classes, imports.

**Diff** — Compare two git states. Added modules glow green, removed fade red, changed modules show per-function AST diffs with complexity/line/param deltas.

**Trace** — Pick an entrypoint and watch its call chain animate left-to-right, depth by depth.

**Data** — Data type cards (dataclasses, Pydantic, SQLAlchemy) with fields and transformation edges.

**Quality** — Complexity scatter plot, module breakdown bars, layer dependency heatmap, hotspot rankings.

## How it works

Bean uses Python's `ast` module to statically analyze your codebase — no runtime, no dependencies. It extracts modules, functions, classes, imports, call edges, complexity metrics, and type annotations, then renders everything into a single self-contained HTML file with D3.js.

For diff mode, it reconstructs the base ref in a temp directory via `git show`, runs analysis on both states, and computes structural diffs at the function/class/import level.

## Requirements

- Python 3.10+
- Git (for `--diff` mode)
- No dependencies
