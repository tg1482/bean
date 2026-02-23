"""Git diff computation for Bean visualizations.

Compares two git states (e.g. HEAD vs main) and produces structured diff
data that the renderer can use to highlight added/removed/changed modules
and edges.
"""

from __future__ import annotations

import shutil
import subprocess
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from bean.analyzer import AnalysisResult, to_bean_data


# ── Data structures ──────────────────────────────────────────────


@dataclass
class GitDiffContext:
    base_ref: str
    base_commit: str
    head_commit: str
    changed_files: list[str]
    base_dir: Path


@dataclass
class FunctionDiff:
    name: str
    status: str  # "added", "removed", "changed", "unchanged"
    complexity: int = 0
    complexity_delta: int = 0
    lines: int = 0
    line_delta: int = 0
    params: int = 0
    param_delta: int = 0
    is_async: bool = False
    async_changed: bool = False
    decorators_added: list[str] = field(default_factory=list)
    decorators_removed: list[str] = field(default_factory=list)
    return_type: str = ""
    return_type_changed: bool = False


@dataclass
class ClassDiff:
    name: str
    status: str  # "added", "removed", "changed", "unchanged"
    methods: int = 0
    method_delta: int = 0
    fields: int = 0
    field_delta: int = 0
    methods_added: list[str] = field(default_factory=list)
    methods_removed: list[str] = field(default_factory=list)
    bases_added: list[str] = field(default_factory=list)
    bases_removed: list[str] = field(default_factory=list)


@dataclass
class ImportDiff:
    target: str
    status: str  # "added", "removed", "changed"
    names_added: list[str] = field(default_factory=list)
    names_removed: list[str] = field(default_factory=list)
    names_all: list[str] = field(default_factory=list)


@dataclass
class ModuleDiff:
    id: str
    line_delta: int
    complexity_delta: int
    functions_added: list[str]
    functions_removed: list[str]
    classes_added: list[str]
    classes_removed: list[str]
    # Rich AST-level diffs
    function_diffs: list[FunctionDiff] = field(default_factory=list)
    class_diffs: list[ClassDiff] = field(default_factory=list)
    import_diffs: list[ImportDiff] = field(default_factory=list)


@dataclass
class DiffResult:
    base_ref: str
    base_commit: str
    head_commit: str
    files_changed: int
    added_modules: list[str]
    removed_modules: list[str]
    changed_modules: dict[str, ModuleDiff]
    unchanged_modules: list[str]
    added_edges: list[dict[str, Any]]
    removed_edges: list[dict[str, Any]]


# ── Git operations ───────────────────────────────────────────────


def _run_git(args: list[str], cwd: Path) -> str:
    """Run a git command and return stdout. Raises on failure."""
    result = subprocess.run(
        ["git"] + args,
        cwd=cwd,
        capture_output=True,
        text=True,
        timeout=30,
    )
    if result.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)} failed: {result.stderr.strip()}")
    return result.stdout.strip()


def prepare_base_ref(root: Path, base_ref: str) -> GitDiffContext:
    """Reconstruct the codebase at base_ref in a temp directory.

    Returns a GitDiffContext with paths and metadata needed for diff.
    """
    root = root.resolve()

    # Validate git repo
    try:
        _run_git(["rev-parse", "--is-inside-work-tree"], root)
    except (RuntimeError, FileNotFoundError) as e:
        raise RuntimeError(f"Not a git repository or git not installed: {e}")

    # Resolve commits
    try:
        base_commit = _run_git(["rev-parse", base_ref], root)
    except RuntimeError:
        raise RuntimeError(f"Invalid git ref: {base_ref}")
    head_commit = _run_git(["rev-parse", "HEAD"], root)

    # List changed .py files between base and HEAD
    changed_raw = _run_git(
        ["diff", "--name-only", base_commit, "HEAD", "--", "*.py"], root
    )
    changed_files = [f for f in changed_raw.splitlines() if f.strip()]

    # List all .py files at base ref
    try:
        tree_raw = _run_git(["ls-tree", "-r", "--name-only", base_commit], root)
    except RuntimeError:
        tree_raw = ""
    base_py_files = [f for f in tree_raw.splitlines() if f.strip().endswith(".py")]

    # Reconstruct base in temp dir
    base_dir = Path(tempfile.mkdtemp(prefix="bean-diff-"))
    for rel_path in base_py_files:
        try:
            content = _run_git(["show", f"{base_commit}:{rel_path}"], root)
        except RuntimeError:
            continue
        out_path = base_dir / rel_path
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(content, encoding="utf-8")

    return GitDiffContext(
        base_ref=base_ref,
        base_commit=base_commit[:12],
        head_commit=head_commit[:12],
        changed_files=changed_files,
        base_dir=base_dir,
    )


def cleanup_base_ref(ctx: GitDiffContext) -> None:
    """Remove the temporary base directory."""
    if ctx.base_dir.exists():
        shutil.rmtree(ctx.base_dir, ignore_errors=True)


# ── Diff computation ─────────────────────────────────────────────


def compute_diff(
    base: AnalysisResult, head: AnalysisResult, ctx: GitDiffContext
) -> DiffResult:
    """Compare base and head analysis results to produce a structured diff."""
    base_ids = {m.id for m in base.modules}
    head_ids = {m.id for m in head.modules}

    added = sorted(head_ids - base_ids)
    removed = sorted(base_ids - head_ids)
    common = base_ids & head_ids

    # Index modules
    base_mod = {m.id: m for m in base.modules}
    head_mod = {m.id: m for m in head.modules}

    # Index functions/classes by module
    base_fns = _group_by_module(base.functions)
    head_fns = _group_by_module(head.functions)
    base_cls = _group_classes_by_module(base.classes)
    head_cls = _group_classes_by_module(head.classes)

    changed: dict[str, ModuleDiff] = {}
    unchanged: list[str] = []

    # Index imports by module
    base_imports = _group_imports_by_module(base.import_edges)
    head_imports = _group_imports_by_module(head.import_edges)

    for mid in sorted(common):
        bm = base_mod[mid]
        hm = head_mod[mid]

        b_fn_map = base_fns.get(mid, {})
        h_fn_map = head_fns.get(mid, {})
        b_cls_map = base_cls.get(mid, {})
        h_cls_map = head_cls.get(mid, {})
        b_fn_names = set(b_fn_map.keys())
        h_fn_names = set(h_fn_map.keys())
        b_cls_names = set(b_cls_map.keys())
        h_cls_names = set(h_cls_map.keys())

        line_delta = hm.line_count - bm.line_count
        complexity_delta = hm.complexity_sum - bm.complexity_sum
        fns_added = sorted(h_fn_names - b_fn_names)
        fns_removed = sorted(b_fn_names - h_fn_names)
        cls_added = sorted(h_cls_names - b_cls_names)
        cls_removed = sorted(b_cls_names - h_cls_names)

        # Per-function diffs
        function_diffs = _compute_function_diffs(b_fn_map, h_fn_map)
        class_diffs = _compute_class_diffs(b_cls_map, h_cls_map)
        import_diffs = _compute_import_diffs(
            base_imports.get(mid, {}), head_imports.get(mid, {})
        )

        any_change = (
            line_delta != 0
            or complexity_delta != 0
            or fns_added
            or fns_removed
            or cls_added
            or cls_removed
        )

        if any_change:
            changed[mid] = ModuleDiff(
                id=mid,
                line_delta=line_delta,
                complexity_delta=complexity_delta,
                functions_added=fns_added,
                functions_removed=fns_removed,
                classes_added=cls_added,
                classes_removed=cls_removed,
                function_diffs=function_diffs,
                class_diffs=class_diffs,
                import_diffs=import_diffs,
            )
        else:
            unchanged.append(mid)

    # Edge diff
    base_edge_keys = {
        (f"module:{e.source}", f"module:{e.target}"): e
        for e in base.import_edges
    }
    head_edge_keys = {
        (f"module:{e.source}", f"module:{e.target}"): e
        for e in head.import_edges
    }

    # Aggregate edges by (source, target) with names
    base_edges_agg = _aggregate_edges(base.import_edges)
    head_edges_agg = _aggregate_edges(head.import_edges)

    base_edge_set = set(base_edges_agg.keys())
    head_edge_set = set(head_edges_agg.keys())

    added_edges = []
    for key in sorted(head_edge_set - base_edge_set):
        s, t = key
        info = head_edges_agg[key]
        added_edges.append(
            {"source": s, "target": t, "names": sorted(info["names"])}
        )

    removed_edges = []
    for key in sorted(base_edge_set - head_edge_set):
        s, t = key
        info = base_edges_agg[key]
        removed_edges.append(
            {"source": s, "target": t, "names": sorted(info["names"])}
        )

    return DiffResult(
        base_ref=ctx.base_ref,
        base_commit=ctx.base_commit,
        head_commit=ctx.head_commit,
        files_changed=len(ctx.changed_files),
        added_modules=added,
        removed_modules=removed,
        changed_modules=changed,
        unchanged_modules=unchanged,
        added_edges=added_edges,
        removed_edges=removed_edges,
    )


def _group_by_module(functions: list) -> dict[str, dict[str, Any]]:
    """Group functions by module, keyed by function name."""
    result: dict[str, dict[str, Any]] = {}
    for f in functions:
        mod = f.module
        if mod not in result:
            result[mod] = {}
        result[mod][f.name] = f
    return result


def _group_classes_by_module(classes: list) -> dict[str, dict[str, Any]]:
    """Group classes by module, keyed by class name."""
    result: dict[str, dict[str, Any]] = {}
    for c in classes:
        mod = c.module
        if mod not in result:
            result[mod] = {}
        result[mod][c.name] = c
    return result


def _aggregate_edges(import_edges: list) -> dict[tuple[str, str], dict]:
    """Aggregate import edges by (source, target) module pair."""
    agg: dict[tuple[str, str], dict] = {}
    for e in import_edges:
        key = (f"module:{e.source}", f"module:{e.target}")
        if key not in agg:
            agg[key] = {"names": set()}
        agg[key]["names"].update(e.names)
    # Convert sets to lists
    for v in agg.values():
        v["names"] = list(v["names"])
    return agg


def _group_imports_by_module(import_edges: list) -> dict[str, dict[str, set]]:
    """Group import edges by source module → {target: set(names)}."""
    result: dict[str, dict[str, set]] = {}
    for e in import_edges:
        if e.source not in result:
            result[e.source] = {}
        if e.target not in result[e.source]:
            result[e.source][e.target] = set()
        result[e.source][e.target].update(e.names)
    return result


def _compute_function_diffs(
    base_fns: dict[str, Any], head_fns: dict[str, Any]
) -> list[FunctionDiff]:
    """Compute per-function diffs within a module."""
    all_names = sorted(set(base_fns.keys()) | set(head_fns.keys()))
    diffs = []
    for name in all_names:
        bf = base_fns.get(name)
        hf = head_fns.get(name)

        if hf and not bf:
            diffs.append(FunctionDiff(
                name=name, status="added",
                complexity=hf.complexity,
                lines=hf.end_lineno - hf.lineno,
                params=hf.param_count,
                is_async=hf.is_async,
                return_type=hf.return_annotation,
            ))
        elif bf and not hf:
            diffs.append(FunctionDiff(
                name=name, status="removed",
                complexity=bf.complexity,
                lines=bf.end_lineno - bf.lineno,
                params=bf.param_count,
                is_async=bf.is_async,
                return_type=bf.return_annotation,
            ))
        else:
            # Both exist — compare
            b_lines = bf.end_lineno - bf.lineno
            h_lines = hf.end_lineno - hf.lineno
            c_delta = hf.complexity - bf.complexity
            l_delta = h_lines - b_lines
            p_delta = hf.param_count - bf.param_count
            async_changed = bf.is_async != hf.is_async
            ret_changed = bf.return_annotation != hf.return_annotation

            b_decs = set(bf.decorators)
            h_decs = set(hf.decorators)
            decs_added = sorted(h_decs - b_decs)
            decs_removed = sorted(b_decs - h_decs)

            is_changed = (
                c_delta != 0 or l_delta != 0 or p_delta != 0
                or async_changed or ret_changed
                or decs_added or decs_removed
            )

            diffs.append(FunctionDiff(
                name=name,
                status="changed" if is_changed else "unchanged",
                complexity=hf.complexity,
                complexity_delta=c_delta,
                lines=h_lines,
                line_delta=l_delta,
                params=hf.param_count,
                param_delta=p_delta,
                is_async=hf.is_async,
                async_changed=async_changed,
                decorators_added=decs_added,
                decorators_removed=decs_removed,
                return_type=hf.return_annotation,
                return_type_changed=ret_changed,
            ))

    # Sort: changed first, then added, removed, unchanged
    order = {"changed": 0, "added": 1, "removed": 2, "unchanged": 3}
    diffs.sort(key=lambda d: (order.get(d.status, 4), d.name))
    return diffs


def _compute_class_diffs(
    base_cls: dict[str, Any], head_cls: dict[str, Any]
) -> list[ClassDiff]:
    """Compute per-class diffs within a module."""
    all_names = sorted(set(base_cls.keys()) | set(head_cls.keys()))
    diffs = []
    for name in all_names:
        bc = base_cls.get(name)
        hc = head_cls.get(name)

        if hc and not bc:
            diffs.append(ClassDiff(
                name=name, status="added",
                methods=hc.method_count, fields=hc.field_count,
            ))
        elif bc and not hc:
            diffs.append(ClassDiff(
                name=name, status="removed",
                methods=bc.method_count, fields=bc.field_count,
            ))
        else:
            b_methods = set(bc.methods)
            h_methods = set(hc.methods)
            b_bases = set(bc.bases)
            h_bases = set(hc.bases)
            m_added = sorted(h_methods - b_methods)
            m_removed = sorted(b_methods - h_methods)
            bases_added = sorted(h_bases - b_bases)
            bases_removed = sorted(b_bases - h_bases)
            m_delta = hc.method_count - bc.method_count
            f_delta = hc.field_count - bc.field_count

            is_changed = (
                m_delta != 0 or f_delta != 0
                or m_added or m_removed
                or bases_added or bases_removed
            )

            diffs.append(ClassDiff(
                name=name,
                status="changed" if is_changed else "unchanged",
                methods=hc.method_count,
                method_delta=m_delta,
                fields=hc.field_count,
                field_delta=f_delta,
                methods_added=m_added,
                methods_removed=m_removed,
                bases_added=bases_added,
                bases_removed=bases_removed,
            ))

    order = {"changed": 0, "added": 1, "removed": 2, "unchanged": 3}
    diffs.sort(key=lambda d: (order.get(d.status, 4), d.name))
    return diffs


def _compute_import_diffs(
    base_imports: dict[str, set], head_imports: dict[str, set]
) -> list[ImportDiff]:
    """Compute per-import-target diffs within a module."""
    all_targets = sorted(set(base_imports.keys()) | set(head_imports.keys()))
    diffs = []
    for target in all_targets:
        b_names = base_imports.get(target, set())
        h_names = head_imports.get(target, set())

        if h_names and not b_names:
            diffs.append(ImportDiff(
                target=target, status="added",
                names_added=sorted(h_names),
                names_all=sorted(h_names),
            ))
        elif b_names and not h_names:
            diffs.append(ImportDiff(
                target=target, status="removed",
                names_removed=sorted(b_names),
                names_all=sorted(b_names),
            ))
        else:
            added = sorted(h_names - b_names)
            removed = sorted(b_names - h_names)
            if added or removed:
                diffs.append(ImportDiff(
                    target=target, status="changed",
                    names_added=added,
                    names_removed=removed,
                    names_all=sorted(h_names),
                ))
    return diffs


# ── Conversion to visualization data ────────────────────────────


def to_diff_data(
    diff: DiffResult,
    base_result: AnalysisResult,
    head_result: AnalysisResult,
) -> dict[str, Any]:
    """Convert DiffResult into data dict fields to merge into BEAN_DATA."""
    base_data = to_bean_data(base_result)
    head_data = to_bean_data(head_result)

    # Module-level diff status
    added_node_ids = [f"module:{m}" for m in diff.added_modules]
    removed_node_ids = [f"module:{m}" for m in diff.removed_modules]
    unchanged_node_ids = [f"module:{m}" for m in diff.unchanged_modules]

    changed_map = {}
    for mid, mdiff in diff.changed_modules.items():
        changed_map[f"module:{mid}"] = {
            "lineDelta": mdiff.line_delta,
            "complexityDelta": mdiff.complexity_delta,
            "functionsAdded": mdiff.functions_added,
            "functionsRemoved": mdiff.functions_removed,
            "classesAdded": mdiff.classes_added,
            "classesRemoved": mdiff.classes_removed,
            "functionDiffs": [
                {
                    "name": fd.name,
                    "status": fd.status,
                    "complexity": fd.complexity,
                    "complexityDelta": fd.complexity_delta,
                    "lines": fd.lines,
                    "lineDelta": fd.line_delta,
                    "params": fd.params,
                    "paramDelta": fd.param_delta,
                    "isAsync": fd.is_async,
                    "asyncChanged": fd.async_changed,
                    "decoratorsAdded": fd.decorators_added,
                    "decoratorsRemoved": fd.decorators_removed,
                    "returnType": fd.return_type,
                    "returnTypeChanged": fd.return_type_changed,
                }
                for fd in mdiff.function_diffs
            ],
            "classDiffs": [
                {
                    "name": cd.name,
                    "status": cd.status,
                    "methods": cd.methods,
                    "methodDelta": cd.method_delta,
                    "fields": cd.fields,
                    "fieldDelta": cd.field_delta,
                    "methodsAdded": cd.methods_added,
                    "methodsRemoved": cd.methods_removed,
                    "basesAdded": cd.bases_added,
                    "basesRemoved": cd.bases_removed,
                }
                for cd in mdiff.class_diffs
            ],
            "importDiffs": [
                {
                    "target": imp.target,
                    "status": imp.status,
                    "namesAdded": imp.names_added,
                    "namesRemoved": imp.names_removed,
                    "namesAll": imp.names_all,
                }
                for imp in mdiff.import_diffs
            ],
        }

    # Counts
    total_line_delta = sum(m.line_delta for m in diff.changed_modules.values())
    total_complexity_delta = sum(
        m.complexity_delta for m in diff.changed_modules.values()
    )

    # Ghost nodes: base galaxyNodes for removed modules
    removed_id_set = set(removed_node_ids)
    base_ghost_nodes = [
        n for n in base_data.get("galaxyNodes", []) if n["id"] in removed_id_set
    ]

    # Ghost edges: base galaxyEdges that touch removed modules
    head_edge_set = {
        (e["source"], e["target"]) for e in head_data.get("galaxyEdges", [])
    }
    base_ghost_edges = [
        e
        for e in base_data.get("galaxyEdges", [])
        if (e["source"], e["target"]) not in head_edge_set
        and (e["source"] in removed_id_set or e["target"] in removed_id_set)
    ]

    return {
        "isDiff": True,
        "diffMeta": {
            "baseRef": diff.base_ref,
            "baseCommit": diff.base_commit,
            "headCommit": diff.head_commit,
            "filesChanged": diff.files_changed,
            "modulesAdded": len(diff.added_modules),
            "modulesRemoved": len(diff.removed_modules),
            "modulesChanged": len(diff.changed_modules),
            "modulesUnchanged": len(diff.unchanged_modules),
            "edgesAdded": len(diff.added_edges),
            "edgesRemoved": len(diff.removed_edges),
            "totalLineDelta": total_line_delta,
            "totalComplexityDelta": total_complexity_delta,
        },
        "diffNodes": {
            "added": added_node_ids,
            "removed": removed_node_ids,
            "changed": changed_map,
            "unchanged": unchanged_node_ids,
        },
        "diffEdges": {
            "added": diff.added_edges,
            "removed": diff.removed_edges,
        },
        "baseGalaxyNodes": base_ghost_nodes,
        "baseGalaxyEdges": base_ghost_edges,
    }
