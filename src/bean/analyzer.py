"""Static analyzer for Python codebases.

Uses the ast module to extract modules, functions, classes, imports,
edges, complexity metrics, type annotations, and entrypoints from any
Python codebase.
"""

from __future__ import annotations

import ast
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


# ── Data structures ──────────────────────────────────────────────


@dataclass
class FunctionInfo:
    id: str
    name: str
    qualname: str
    module: str
    lineno: int
    end_lineno: int
    complexity: int
    param_count: int
    param_annotations: list[str]
    return_annotation: str
    is_async: bool
    decorators: list[str]


@dataclass
class ClassInfo:
    id: str
    name: str
    module: str
    lineno: int
    end_lineno: int
    method_count: int
    field_count: int
    bases: list[str]
    decorators: list[str]
    methods: list[str]


@dataclass
class ImportEdge:
    source: str  # module that imports
    target: str  # module being imported
    names: list[str]  # specific names imported


@dataclass
class CallEdge:
    source: str  # caller function id
    target: str  # callee function id
    lineno: int


@dataclass
class EntryPoint:
    id: str
    kind: str  # "main_guard", "script", "route", "cli", "task"
    module: str
    target: str
    lineno: int
    decorators: list[str]


@dataclass
class ModuleInfo:
    id: str
    path: str
    line_count: int
    n_functions: int
    n_classes: int
    n_imports: int
    complexity_sum: int


@dataclass
class AnalysisResult:
    root: str
    is_monorepo: bool = False
    modules: list[ModuleInfo] = field(default_factory=list)
    functions: list[FunctionInfo] = field(default_factory=list)
    classes: list[ClassInfo] = field(default_factory=list)
    import_edges: list[ImportEdge] = field(default_factory=list)
    call_edges: list[CallEdge] = field(default_factory=list)
    entrypoints: list[EntryPoint] = field(default_factory=list)


# ── Complexity calculator ────────────────────────────────────────


def _cyclomatic_complexity(node: ast.AST) -> int:
    """Compute cyclomatic complexity of an AST node."""
    complexity = 1
    for child in ast.walk(node):
        if isinstance(child, (ast.If, ast.While, ast.For, ast.AsyncFor)):
            complexity += 1
        elif isinstance(child, ast.ExceptHandler):
            complexity += 1
        elif isinstance(child, ast.BoolOp):
            complexity += len(child.values) - 1
        elif isinstance(child, (ast.ListComp, ast.SetComp, ast.DictComp, ast.GeneratorExp)):
            complexity += sum(1 for _ in child.generators)
        elif isinstance(child, ast.Assert):
            complexity += 1
    return complexity


def _annotation_str(node: ast.AST | None) -> str:
    """Best-effort unparse of a type annotation node."""
    if node is None:
        return ""
    try:
        return ast.unparse(node)
    except Exception:
        return ""


def _decorator_names(decorator_list: list[ast.expr]) -> list[str]:
    """Extract decorator names."""
    names = []
    for d in decorator_list:
        try:
            names.append(ast.unparse(d))
        except Exception:
            names.append("?")
    return names


# ── AST visitors ─────────────────────────────────────────────────


class _ModuleVisitor(ast.NodeVisitor):
    """Extracts functions, classes, imports, calls, and entrypoints from a module."""

    def __init__(self, module_id: str, source_lines: int):
        self.module_id = module_id
        self.source_lines = source_lines
        self.functions: list[FunctionInfo] = []
        self.classes: list[ClassInfo] = []
        self.imports: list[ImportEdge] = []
        self.calls: list[CallEdge] = []
        self.entrypoints: list[EntryPoint] = []
        self._scope_stack: list[str] = []
        self._n_imports = 0

    def _current_qualname(self, name: str) -> str:
        if self._scope_stack:
            return ".".join(self._scope_stack) + "." + name
        return name

    def _current_func_id(self) -> str:
        if self._scope_stack:
            return f"{self.module_id}:{'.'.join(self._scope_stack)}"
        return self.module_id

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self._visit_func(node, is_async=False)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self._visit_func(node, is_async=True)

    def _visit_func(self, node: ast.FunctionDef | ast.AsyncFunctionDef, is_async: bool) -> None:
        qualname = self._current_qualname(node.name)
        func_id = f"{self.module_id}:{qualname}"

        params = []
        for arg in node.args.args + node.args.posonlyargs + node.args.kwonlyargs:
            if arg.arg == "self" or arg.arg == "cls":
                continue
            params.append(_annotation_str(arg.annotation))

        decorators = _decorator_names(node.decorator_list)

        # Detect route/CLI entrypoints from decorators
        for dec in decorators:
            if any(kw in dec for kw in (".get(", ".post(", ".put(", ".delete(", ".patch(", ".route(",
                                         ".api_route(", "app.get", "app.post", "router.get", "router.post",
                                         ".websocket(", "app.websocket")):
                self.entrypoints.append(EntryPoint(
                    id=func_id,
                    kind="route",
                    module=self.module_id,
                    target=func_id,
                    lineno=node.lineno,
                    decorators=decorators,
                ))
            elif any(kw in dec for kw in ("click.command", "click.group", "typer.command",
                                            "app.command", "cli.command")):
                self.entrypoints.append(EntryPoint(
                    id=func_id,
                    kind="cli",
                    module=self.module_id,
                    target=func_id,
                    lineno=node.lineno,
                    decorators=decorators,
                ))
            elif any(kw in dec for kw in ("celery.task", "app.task", "shared_task")):
                self.entrypoints.append(EntryPoint(
                    id=func_id,
                    kind="task",
                    module=self.module_id,
                    target=func_id,
                    lineno=node.lineno,
                    decorators=decorators,
                ))

        self.functions.append(FunctionInfo(
            id=func_id,
            name=node.name,
            qualname=qualname,
            module=self.module_id,
            lineno=node.lineno,
            end_lineno=node.end_lineno or node.lineno,
            complexity=_cyclomatic_complexity(node),
            param_count=len(params),
            param_annotations=params,
            return_annotation=_annotation_str(node.returns),
            is_async=is_async,
            decorators=decorators,
        ))

        # Visit body for nested definitions and calls
        self._scope_stack.append(node.name)
        self.generic_visit(node)
        self._scope_stack.pop()

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        qualname = self._current_qualname(node.name)
        class_id = f"{self.module_id}:{qualname}"

        bases = []
        for b in node.bases:
            try:
                bases.append(ast.unparse(b))
            except Exception:
                bases.append("?")

        methods = []
        fields = set()
        for item in ast.walk(node):
            if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)) and item in node.body:
                methods.append(item.name)
            # Detect self.x = ... assignments as fields
            if isinstance(item, ast.Assign):
                for target in item.targets:
                    if (isinstance(target, ast.Attribute)
                            and isinstance(target.value, ast.Name)
                            and target.value.id == "self"):
                        fields.add(target.attr)
            # Detect class-level annotations (dataclass fields)
            if isinstance(item, ast.AnnAssign) and item in node.body:
                if isinstance(item.target, ast.Name):
                    fields.add(item.target.id)

        self.classes.append(ClassInfo(
            id=class_id,
            name=node.name,
            module=self.module_id,
            lineno=node.lineno,
            end_lineno=node.end_lineno or node.lineno,
            method_count=len(methods),
            field_count=len(fields),
            bases=bases,
            decorators=_decorator_names(node.decorator_list),
            methods=methods,
        ))

        self._scope_stack.append(node.name)
        self.generic_visit(node)
        self._scope_stack.pop()

    def visit_Import(self, node: ast.Import) -> None:
        self._n_imports += 1
        for alias in node.names:
            self.imports.append(ImportEdge(
                source=self.module_id,
                target=alias.name,
                names=[alias.asname or alias.name],
            ))

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        if node.module is None:
            return
        self._n_imports += 1
        names = [a.name for a in node.names]
        self.imports.append(ImportEdge(
            source=self.module_id,
            target=node.module,
            names=names,
        ))

    def visit_Call(self, node: ast.Call) -> None:
        caller = self._current_func_id()
        callee = _resolve_call_target(node.func)
        if callee:
            self.calls.append(CallEdge(
                source=caller,
                target=callee,
                lineno=node.lineno,
            ))
        self.generic_visit(node)


def _resolve_call_target(node: ast.expr) -> str:
    """Best-effort extraction of call target name."""
    try:
        return ast.unparse(node)
    except Exception:
        return ""


# ── Main guard detection ─────────────────────────────────────────


def _detect_main_guard(tree: ast.Module, module_id: str) -> EntryPoint | None:
    """Check for if __name__ == '__main__' blocks."""
    for node in ast.walk(tree):
        if isinstance(node, ast.If):
            try:
                test_src = ast.unparse(node.test)
                if "__name__" in test_src and "__main__" in test_src:
                    return EntryPoint(
                        id=f"{module_id}:__main__",
                        kind="main_guard",
                        module=module_id,
                        target=f"{module_id}:__main__",
                        lineno=node.lineno,
                        decorators=[],
                    )
            except Exception:
                pass
    return None


# ── Module discovery ─────────────────────────────────────────────


def _discover_python_files(root: Path) -> list[Path]:
    """Find all .py files under root, skipping common non-source dirs."""
    skip_dirs = {
        ".git", ".hg", ".svn", "__pycache__", ".venv", "venv",
        "env", ".env", "node_modules", ".tox", ".nox", ".mypy_cache",
        ".pytest_cache", ".ruff_cache", "dist", "build", "*.egg-info",
        ".eggs", ".cache",
    }
    files = []
    for dirpath, dirnames, filenames in os.walk(root):
        # Filter out skip directories in-place
        dirnames[:] = [
            d for d in dirnames
            if d not in skip_dirs and not d.endswith(".egg-info")
        ]
        for fname in filenames:
            if fname.endswith(".py"):
                files.append(Path(dirpath) / fname)
    return sorted(files)


def _path_to_module_id(path: Path, root: Path) -> str:
    """Convert a file path to a dotted module id."""
    rel = path.relative_to(root)
    parts = list(rel.parts)
    # Remove .py extension from the last part
    if parts[-1].endswith(".py"):
        parts[-1] = parts[-1][:-3]
    # Remove __init__ — the package itself is the module
    if parts[-1] == "__init__":
        parts = parts[:-1]
    if not parts:
        return "__root__"
    return ".".join(parts)


# ── Layer inference ──────────────────────────────────────────────


def _infer_layer(module_id: str, is_monorepo: bool = False) -> str:
    """Infer a layer from the package name.

    For monorepos, uses the second-level package as the layer
    (e.g. backend-service.app.routes -> routes, wss-service.app.brainstorm -> brainstorm).
    Falls back to service name if depth is insufficient.
    """
    parts = module_id.split(".")

    # Common conventions for direct mapping
    _LAYER_MAP = {
        "api": "api", "routes": "api", "views": "api", "endpoints": "api",
        "worker": "worker", "workers": "worker", "tasks": "worker", "celery": "worker", "jobs": "worker",
        "db": "db", "database": "db", "models": "db", "orm": "db", "migrations": "db", "alembic": "db",
        "src": "core", "core": "core", "lib": "core", "utils": "core", "common": "core",
        "tests": "test", "test": "test",
        "scripts": "script", "cli": "script", "commands": "script", "manage": "script",
        "config": "config", "settings": "config", "conf": "config",
    }

    if not is_monorepo:
        return _LAYER_MAP.get(parts[0], parts[0])

    # Monorepo: try to find a meaningful layer deeper in the path
    # e.g. "wss-service.app.brainstorm.brainstorm" -> try "brainstorm", then "app", then "wss-service"
    # Skip generic package names like "app", "src", "lib"
    _GENERIC = {"app", "src", "lib", "main", "core", "common", "__init__"}
    # Use the deepest non-generic segment that isn't the filename itself
    # For "wss-service.app.brainstorm.brainstorm" -> pick "brainstorm" (the package)
    candidates = parts[1:-1] if len(parts) > 2 else parts  # skip service name and leaf module
    for p in reversed(candidates):
        if p not in _GENERIC:
            return _LAYER_MAP.get(p, p)
    # Fallback: use the service name (top-level dir)
    return parts[0]


# ── Import resolution ────────────────────────────────────────────


def _resolve_import_to_internal(
    target: str,
    known_modules: set[str],
    suffix_index: dict[str, list[str]] | None = None,
) -> str | None:
    """Try to match an import target to an internal module id."""
    if target in known_modules:
        return target
    # Try prefix matches (e.g. "db.models" when "db.models" exists)
    parts = target.split(".")
    for i in range(len(parts), 0, -1):
        candidate = ".".join(parts[:i])
        if candidate in known_modules:
            return candidate
    # Try suffix matches for monorepos (e.g. "app.models" → "backend-service.app.models")
    if suffix_index:
        matches = suffix_index.get(target, [])
        if len(matches) == 1:
            return matches[0]
        # Try progressively shorter suffixes
        for i in range(len(parts), 0, -1):
            suffix = ".".join(parts[:i])
            matches = suffix_index.get(suffix, [])
            if len(matches) == 1:
                return matches[0]
    return None


# ── Public API ───────────────────────────────────────────────────


def _detect_monorepo(root: Path) -> bool:
    """Detect if root is a monorepo (multiple service dirs, no top-level package config)."""
    has_project_file = (
        (root / "pyproject.toml").exists()
        or (root / "setup.py").exists()
        or (root / "setup.cfg").exists()
    )
    if has_project_file:
        return False
    # Count subdirectories that contain .py files
    py_subdirs = 0
    for child in root.iterdir():
        if child.is_dir() and not child.name.startswith("."):
            if any(child.rglob("*.py")):
                py_subdirs += 1
    return py_subdirs >= 2


def analyze(root: Path) -> AnalysisResult:
    """Analyze a Python codebase at the given root path."""
    root = root.resolve()
    is_monorepo = _detect_monorepo(root)
    result = AnalysisResult(root=str(root), is_monorepo=is_monorepo)
    py_files = _discover_python_files(root)

    if not py_files:
        print(f"  No Python files found under {root}")
        return result

    if is_monorepo:
        print(f"  Detected monorepo layout")
    print(f"  Found {len(py_files)} Python files")

    # First pass: parse all files, collect data
    parsed: dict[str, tuple[ast.Module, _ModuleVisitor, int]] = {}
    for path in py_files:
        module_id = _path_to_module_id(path, root)
        try:
            source = path.read_text(encoding="utf-8", errors="replace")
        except (OSError, UnicodeDecodeError):
            continue
        line_count = source.count("\n") + 1
        try:
            tree = ast.parse(source, filename=str(path))
        except SyntaxError:
            continue

        visitor = _ModuleVisitor(module_id, line_count)
        visitor.visit(tree)

        # Check for main guard
        main_ep = _detect_main_guard(tree, module_id)
        if main_ep:
            visitor.entrypoints.append(main_ep)

        parsed[module_id] = (tree, visitor, line_count)

    known_modules = set(parsed.keys())
    print(f"  Parsed {len(known_modules)} modules")

    # Build suffix index for monorepo import resolution
    # e.g. "backend-service.app.models" → indexed under "app.models", "models"
    suffix_index: dict[str, list[str]] = {}
    for mod_id in known_modules:
        parts = mod_id.split(".")
        for i in range(1, len(parts) + 1):
            suffix = ".".join(parts[-i:])
            suffix_index.setdefault(suffix, []).append(mod_id)

    # Build all function ids for call resolution
    all_func_ids: dict[str, str] = {}  # short name → full id
    all_func_qualnames: dict[str, str] = {}  # qualname → full id
    for mod_id, (_, visitor, _) in parsed.items():
        for f in visitor.functions:
            all_func_ids[f.name] = f.id
            all_func_qualnames[f.qualname] = f.id
            all_func_qualnames[f"{mod_id}.{f.name}"] = f.id

    # Second pass: resolve edges
    for mod_id, (_, visitor, line_count) in parsed.items():
        result.modules.append(ModuleInfo(
            id=mod_id,
            path=str(Path(mod_id.replace(".", "/"))),
            line_count=line_count,
            n_functions=len(visitor.functions),
            n_classes=len(visitor.classes),
            n_imports=visitor._n_imports,
            complexity_sum=sum(f.complexity for f in visitor.functions),
        ))
        result.functions.extend(visitor.functions)
        result.classes.extend(visitor.classes)
        result.entrypoints.extend(visitor.entrypoints)

        # Resolve imports to internal modules
        for imp in visitor.imports:
            internal = _resolve_import_to_internal(imp.target, known_modules, suffix_index)
            if internal and internal != mod_id:
                result.import_edges.append(ImportEdge(
                    source=mod_id,
                    target=internal,
                    names=imp.names,
                ))

        # Resolve calls — best-effort match to known functions
        for call in visitor.calls:
            target_name = call.target
            resolved = None
            # Try exact qualname match within same module
            local_qn = f"{mod_id}:{target_name}"
            if local_qn in {f.id for f in visitor.functions}:
                resolved = local_qn
            # Try as a dotted path: module.func
            elif target_name in all_func_qualnames:
                resolved = all_func_qualnames[target_name]
            # Try just the function name (last part after dot)
            else:
                short = target_name.rsplit(".", 1)[-1]
                if short in all_func_ids:
                    resolved = all_func_ids[short]

            if resolved and resolved != call.source:
                result.call_edges.append(CallEdge(
                    source=call.source,
                    target=resolved,
                    lineno=call.lineno,
                ))

    print(f"  {len(result.functions)} functions, {len(result.classes)} classes")
    print(f"  {len(result.import_edges)} import edges, {len(result.call_edges)} call edges")
    print(f"  {len(result.entrypoints)} entrypoints")

    return result


# ── Conversion to Bean data format ───────────────────────────────


def to_bean_data(result: AnalysisResult) -> dict[str, Any]:
    """Convert AnalysisResult into the data dict consumed by the renderer."""
    modules = result.modules
    functions = result.functions
    classes = result.classes
    import_edges = result.import_edges
    call_edges = result.call_edges
    entrypoints = result.entrypoints

    # Derive layers
    layers: dict[str, set[str]] = {}
    mod_layer: dict[str, str] = {}
    for m in modules:
        layer = _infer_layer(m.id, is_monorepo=result.is_monorepo)
        mod_layer[m.id] = layer
        layers.setdefault(layer, set()).add(m.id)

    # Hotspot ids (top complexity functions)
    sorted_funcs = sorted(functions, key=lambda f: f.complexity, reverse=True)
    hotspot_ids = set(f.id for f in sorted_funcs[:max(20, len(sorted_funcs) // 10)])

    # Build galaxy nodes
    galaxy_nodes = []
    ep_module_ids = set(ep.module for ep in entrypoints)
    for m in modules:
        layer = mod_layer[m.id]
        is_hotspot = any(fid in hotspot_ids for fid in
                         [f.id for f in functions if f.module == m.id])
        galaxy_nodes.append({
            "id": f"module:{m.id}",
            "label": m.id,
            "layer": layer,
            "complexity": m.complexity_sum,
            "symbolCount": m.n_functions + m.n_classes,
            "nClasses": m.n_classes,
            "nFunctions": m.n_functions,
            "nImports": m.n_imports,
            "path": m.path,
            "isHotspot": is_hotspot,
            "parent": f"layer:{layer}",
            "kind": "module",
            "isEntryPoint": m.id in ep_module_ids,
        })

    # Build galaxy edges from import edges (aggregated per module pair)
    edge_counts: dict[tuple[str, str], int] = {}
    for e in import_edges:
        key = (f"module:{e.source}", f"module:{e.target}")
        edge_counts[key] = edge_counts.get(key, 0) + 1

    galaxy_edges = [
        {"source": s, "target": t, "count": c, "confidenceCounts": {}}
        for (s, t), c in edge_counts.items()
    ]

    # Entrypoint flow data
    ep_list = []
    for ep in entrypoints:
        ep_list.append({
            "id": ep.id,
            "kind": ep.kind,
            "target": ep.target,
            "module": ep.module,
            "lineno": ep.lineno,
            "decorators": ep.decorators,
        })

    # EP nodes = all function nodes
    ep_nodes = []
    for f in functions:
        ep_nodes.append({
            "id": f.id,
            "label": f.qualname,
            "module": f.module,
            "kind": "function",
        })

    # EP edges from call edges
    ep_edges = [
        {"source": e.source, "target": e.target}
        for e in call_edges
    ]

    # Treemap hierarchy: layer → module → symbol
    treemap: dict[str, Any] = {"name": "codebase", "children": []}
    for layer_name in sorted(layers.keys()):
        layer_item: dict[str, Any] = {
            "name": layer_name,
            "layer": layer_name,
            "complexity": 0,
            "children": [],
        }
        for mod_id in sorted(layers[layer_name]):
            mod = next((m for m in modules if m.id == mod_id), None)
            if not mod:
                continue
            mod_item: dict[str, Any] = {
                "name": mod_id,
                "layer": layer_name,
                "complexity": mod.complexity_sum,
                "children": [],
            }
            # Add functions and classes as children
            for f in functions:
                if f.module == mod_id:
                    mod_item["children"].append({
                        "name": f.qualname,
                        "layer": layer_name,
                        "complexity": f.complexity,
                        "span": f.end_lineno - f.lineno,
                        "value": max(1, f.end_lineno - f.lineno),
                    })
            if not mod_item["children"]:
                mod_item["value"] = max(1, mod.line_count)
            layer_item["children"].append(mod_item)
            layer_item["complexity"] += mod.complexity_sum

        if not layer_item["children"]:
            layer_item["value"] = 1
        treemap["children"].append(layer_item)

    # Functions enriched for scatter plot
    functions_enriched = [
        {
            "id": f.id,
            "module": f.module,
            "complexity": f.complexity,
            "span": f.end_lineno - f.lineno,
            "calls": 0,
            "layer": mod_layer.get(f.module, "other"),
        }
        for f in functions
    ]

    # Count calls received per function
    call_received: dict[str, int] = {}
    for e in call_edges:
        call_received[e.target] = call_received.get(e.target, 0) + 1
    for fe in functions_enriched:
        fe["calls"] = call_received.get(fe["id"], 0)

    # Module breakdown
    mod_complexity: dict[str, dict] = {}
    for f in functions:
        mod = f.module
        if mod not in mod_complexity:
            mod_complexity[mod] = {
                "module": mod,
                "layer": mod_layer.get(mod, "other"),
                "totalComplexity": 0,
                "functionCount": 0,
                "maxComplexity": 0,
                "totalSpan": 0,
            }
        mc = mod_complexity[mod]
        mc["totalComplexity"] += f.complexity
        mc["functionCount"] += 1
        mc["maxComplexity"] = max(mc["maxComplexity"], f.complexity)
        mc["totalSpan"] += max(0, f.end_lineno - f.lineno)
    module_breakdown = sorted(
        mod_complexity.values(),
        key=lambda m: m["totalComplexity"],
        reverse=True,
    )

    # Layer matrix (cross-layer import counts)
    layer_names = sorted(layers.keys())
    layer_matrix = []
    for e in import_edges:
        src_layer = mod_layer.get(e.source, "other")
        tgt_layer = mod_layer.get(e.target, "other")
        if src_layer != tgt_layer:
            layer_matrix.append({
                "source_layer": src_layer,
                "target_layer": tgt_layer,
                "count": 1,
            })
    # Aggregate
    lm_counts: dict[tuple[str, str], int] = {}
    for lm in layer_matrix:
        key = (lm["source_layer"], lm["target_layer"])
        lm_counts[key] = lm_counts.get(key, 0) + lm["count"]
    layer_matrix_agg = [
        {"source_layer": s, "target_layer": t, "count": c}
        for (s, t), c in lm_counts.items()
    ]

    # Hotspots
    hotspots = [
        {
            "id": f.id,
            "complexity": f.complexity,
            "span": f.end_lineno - f.lineno,
            "path": f.module.replace(".", "/") + ".py",
            "lineno": f.lineno,
            "calls": call_received.get(f.id, 0),
        }
        for f in sorted_funcs[:80]
    ]

    # Type coverage stats
    typed_params = sum(1 for f in functions for a in f.param_annotations if a)
    total_params = sum(f.param_count for f in functions)
    typed_returns = sum(1 for f in functions if f.return_annotation)
    param_coverage = (typed_params / total_params * 100) if total_params > 0 else 0
    return_coverage = (typed_returns / len(functions) * 100) if functions else 0

    # Cross-layer edge count
    cross_layer = sum(
        1 for e in import_edges
        if mod_layer.get(e.source, "") != mod_layer.get(e.target, "")
    )

    quality = {
        "boundaryScore": 100,  # placeholder
        "violationCount": 0,
        "violationRate": 0,
        "crossLayerEdges": cross_layer,
        "typeCoverage": round(param_coverage, 1),
        "returnTypeCoverage": round(return_coverage, 1),
        "cohesionRate": 0,
        "serviceLikeCount": sum(1 for c in classes if any("service" in b.lower() for b in c.bases)),
        "classCount": len(classes),
        "resolutionRate": 0,
        "confidenceCounts": {},
        "packageScores": [],
        "layerMatrix": layer_matrix_agg,
        "meta": {
            "root": str(result.root),
            "module_count": len(modules),
            "function_count": len(functions),
            "class_count": len(classes),
            "total_lines": sum(m.line_count for m in modules),
        },
        "hotspots": hotspots,
        "functions": functions_enriched,
        "moduleBreakdown": module_breakdown,
    }

    # Drill levels (simplified — no group level for generic codebases)
    layer_nodes_drill = [
        {"id": f"layer:{ln}", "label": ln, "layer": ln, "complexity_sum": sum(
            m.complexity_sum for m in modules if mod_layer.get(m.id) == ln
        )}
        for ln in layer_names
    ]
    module_nodes_drill = [
        {
            "id": f"module:{m.id}",
            "label": m.id,
            "layer": mod_layer.get(m.id, "other"),
            "complexity_sum": m.complexity_sum,
            "symbol_count": m.n_functions + m.n_classes,
            "parent": f"layer:{mod_layer.get(m.id, 'other')}",
        }
        for m in modules
    ]
    symbol_nodes_drill = [
        {
            "id": f.id,
            "label": f.qualname,
            "layer": mod_layer.get(f.module, "other"),
            "complexity": f.complexity,
            "span": f.end_lineno - f.lineno,
            "parent": f"module:{f.module}",
            "kind": "function",
        }
        for f in functions
    ] + [
        {
            "id": c.id,
            "label": c.name,
            "layer": mod_layer.get(c.module, "other"),
            "complexity": 0,
            "span": c.end_lineno - c.lineno,
            "parent": f"module:{c.module}",
            "kind": "class",
        }
        for c in classes
    ]

    drill_data = {
        "layer": {
            "nodes": layer_nodes_drill,
            "edges": [],
            "parentLevel": None,
        },
        "module": {
            "nodes": module_nodes_drill,
            "edges": [{"source": e["source"], "target": e["target"], "count": e["count"]}
                      for e in galaxy_edges],
            "parentLevel": "layer",
        },
        "symbol": {
            "nodes": symbol_nodes_drill,
            "edges": [{"source": e.source, "target": e.target} for e in call_edges],
            "parentLevel": "module",
        },
    }

    # Classes enriched
    classes_enriched = [
        {
            "id": c.id,
            "name": c.name,
            "module": c.module,
            "methodCount": c.method_count,
            "fieldCount": c.field_count,
            "serviceLike": any("service" in b.lower() for b in c.bases),
            "lineno": c.lineno,
            "endLineno": c.end_lineno,
        }
        for c in classes
    ]

    return {
        "galaxyNodes": galaxy_nodes,
        "galaxyEdges": galaxy_edges,
        "entrypoints": ep_list,
        "epNodes": ep_nodes,
        "epEdges": ep_edges,
        "treemap": treemap,
        "quality": quality,
        "drillLevels": drill_data,
        "levelOrder": ["layer", "module", "symbol"],
        "classes": classes_enriched,
    }
