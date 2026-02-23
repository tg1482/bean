"""Bean CLI — analyze any Python codebase and generate a visualization."""

from __future__ import annotations

import argparse
import sys
import webbrowser
from pathlib import Path

from bean import __version__
from bean.analyzer import analyze, to_bean_data
from bean.render import download_d3, render_html


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="bean",
        description="Codebase visualizer for Python projects",
    )
    parser.add_argument(
        "path",
        nargs="?",
        default=".",
        help="Path to the Python project root (default: current directory)",
    )
    parser.add_argument(
        "-o", "--output",
        default=None,
        help="Output HTML file path (default: bean.html in current directory)",
    )
    parser.add_argument(
        "--no-open",
        action="store_true",
        help="Don't open the output in the browser",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"bean {__version__}",
    )

    args = parser.parse_args()

    root = Path(args.path).resolve()
    if not root.is_dir():
        print(f"Error: {root} is not a directory", file=sys.stderr)
        sys.exit(1)

    output = Path(args.output) if args.output else Path.cwd() / "bean.html"

    print(f"Bean v{__version__} — Codebase Visualizer")
    print(f"  Analyzing {root} ...")

    result = analyze(root)

    if not result.modules:
        print("  No Python modules found. Nothing to visualize.", file=sys.stderr)
        sys.exit(1)

    print("  Building visualization data ...")
    data = to_bean_data(result)

    print("  Downloading D3.js (cached) ...")
    cache_dir = Path.home() / ".cache" / "bean"
    d3_js = download_d3(cache_dir)
    print(f"  D3: {len(d3_js) // 1024}KB")

    html = render_html(data, d3_js)
    output.write_text(html, encoding="utf-8")
    size_kb = len(html) // 1024
    print(f"  Wrote {output} ({size_kb}KB)")

    if not args.no_open:
        webbrowser.open(f"file://{output.resolve()}")
