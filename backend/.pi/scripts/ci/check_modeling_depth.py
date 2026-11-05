#!/usr/bin/env python3
"""ADR-008 modeling-depth validator.

ADR-008 makes modeling depth a property of the subdomain type and requires it to be checkable
mechanically:

    tactical (core)         aggregates, invariants, events  -> domain/ application/ infrastructure/ interfaces/
    service  (supporting)   application service + contract  -> no domain/ layer at all
    adapter  (generic)      narrow port + ACL               -> interfaces/ infrastructure/ only

The truth for depth per context lives in `.pi/architecture/modeling-depth.json`, which is a
projection of the ADR. This script fails when:

  * a context present under src/ is not declared in the manifest,
  * a declared context misses a layer its depth requires (or has one it forbids),
  * a required layer contains no Python module,
  * an architecture module document has no matching manifest entry.

Contexts that are declared but not yet built are reported as pending, not as failures — the
roadmap builds contexts phase by phase.

Usage:
  python3 .pi/scripts/ci/check_modeling_depth.py [--src src] [--json]
Exit: 0 = conformant, 1 = violations.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_SRC = "src"
DEFAULT_MANIFEST = ".pi/architecture/modeling-depth.json"
MODULES_DIR = ".pi/architecture/modules"
SKIPPED_MODULES = {"module-template"}
SHARED_DIRS = {"shared", "common", "config", "lib"}


class Report:
    def __init__(self) -> None:
        self.passed: list[str] = []
        self.failed: list[str] = []
        self.pending: list[str] = []

    def ok(self, message: str) -> None:
        self.passed.append(message)

    def fail(self, message: str) -> None:
        self.failed.append(message)

    def skip(self, message: str) -> None:
        self.pending.append(message)


def load_manifest(path: Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise SystemExit(f"modeling-depth manifest not found: {path}") from None
    except json.JSONDecodeError as error:
        raise SystemExit(f"modeling-depth manifest is invalid JSON: {error}") from None


def python_modules(directory: Path) -> list[Path]:
    return sorted(p for p in directory.rglob("*.py") if p.name != "__init__.py")


def check_context(
    repo: Path,
    src: str,
    context: str,
    depth: str,
    rules: dict[str, Any],
    report: Report,
) -> None:
    context_dir = repo / src / context
    if not context_dir.is_dir():
        report.skip(f"{context} ({depth}) — not built yet")
        return

    problems: list[str] = []

    for layer in rules.get("required_layers", []):
        layer_dir = context_dir / layer
        if not layer_dir.is_dir():
            problems.append(f"missing required layer {layer}/")
        elif layer in rules.get("requires_python_in", []) and not python_modules(layer_dir):
            problems.append(f"layer {layer}/ contains no Python modules")

    for layer in rules.get("forbidden_layers", []):
        layer_dir = context_dir / layer
        if layer_dir.is_dir() and python_modules(layer_dir):
            problems.append(f"layer {layer}/ is excluded for {depth} contexts")

    if problems:
        for problem in problems:
            report.fail(f"{context} ({depth}) — {problem}")
    else:
        report.ok(f"{context} ({depth}) — layers match declared depth")


def check_undeclared(repo: Path, src: str, declared: dict[str, str], report: Report) -> None:
    src_dir = repo / src
    if not src_dir.is_dir():
        return
    for candidate in sorted(p for p in src_dir.iterdir() if p.is_dir()):
        if candidate.name in SHARED_DIRS or candidate.name in declared:
            continue
        if candidate.name.startswith((".", "__")):
            continue
        report.fail(
            f"{candidate.name} — context directory is not declared in modeling-depth.json"
        )


def check_module_documents(repo: Path, declared: dict[str, str], report: Report) -> None:
    modules_dir = repo / MODULES_DIR
    if not modules_dir.is_dir():
        return
    documented = {
        path.stem.replace("-", "_")
        for path in modules_dir.glob("*.md")
        if path.stem not in SKIPPED_MODULES
    }
    for missing in sorted(documented - set(declared)):
        report.fail(f"{missing} — module document has no declared modeling depth")
    for orphan in sorted(set(declared) - documented):
        report.fail(f"{orphan} — declared depth has no module document under {MODULES_DIR}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate ADR-008 modeling depth")
    parser.add_argument("--src", default=DEFAULT_SRC)
    parser.add_argument("--manifest", default=DEFAULT_MANIFEST)
    parser.add_argument("--json", action="store_true", dest="as_json")
    args = parser.parse_args(argv)

    repo = REPO_ROOT
    manifest = load_manifest(repo / args.manifest)
    depths: dict[str, dict[str, Any]] = manifest.get("depths", {})
    contexts: dict[str, str] = manifest.get("contexts", {})
    report = Report()

    for context, depth in sorted(contexts.items()):
        rules = depths.get(depth)
        if rules is None:
            report.fail(f"{context} — declares unknown depth {depth!r}")
            continue
        check_context(repo, args.src, context, depth, rules, report)

    check_undeclared(repo, args.src, contexts, report)
    check_module_documents(repo, contexts, report)

    if args.as_json:
        print(
            json.dumps(
                {
                    "passed": report.passed,
                    "failed": report.failed,
                    "pending": report.pending,
                },
                indent=2,
            )
        )
    else:
        print("============================================")
        print("  ADR-008 Modeling Depth Check")
        print("============================================")
        for message in report.failed:
            print(f"  FAIL  {message}")
        for message in report.pending:
            print(f"  SKIP  {message}")
        print()
        print(
            f"  Passed: {len(report.passed)}  Failed: {len(report.failed)}  "
            f"Not built: {len(report.pending)}"
        )
        if not report.failed:
            print("  Modeling depth conforms to ADR-008.")

    return 1 if report.failed else 0


if __name__ == "__main__":
    sys.exit(main())
