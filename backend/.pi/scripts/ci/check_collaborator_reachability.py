#!/usr/bin/env python3
"""W8 gate: every collaborator assigned in ``__init__`` must actually be read.

The recurring defect in this codebase is a collaborator that is constructed, injected, unit-tested and
never called: ``BudgetGuard``, ``RetryPolicy``, ``ResolveMeasureIdentity``, ``ContradictionDetector``,
``PauseBoundary`` inputs. Proofing scripts that assert shapes (``class X exists``, ``method names``) cannot
see it. This check can: it parses every module and reports attributes assigned as ``self._x`` in
``__init__`` that are never loaded anywhere in the class.

Wired as a ratchet: known offenders are listed with the issue that removes them, so a new dead injection
fails CI immediately while the existing ones stay visible.

Usage:
    python .pi/scripts/ci/check_collaborator_reachability.py [--strict]

``--strict`` ignores the allowlist (use it to check whether the allowlist has gone stale).
"""

from __future__ import annotations

import argparse
import ast
import pathlib
import sys

SOURCE_ROOT = pathlib.Path("src")

# Attributes that are set for external readers (exception payloads, dataclass-style carriers) are not
# collaborators: the class never reads them, its consumers do.
EXEMPT_SUFFIXES = ("/domain/errors.py", "/shared/errors.py", "/application/errors.py")

_ALLOWED: dict[str, str] = {
    # key: "<module path>:<Class>.<attr>"
    "src/simulation_orchestration/application/services.py:RunSimulationJob._negotiation": (
        "#246 (Phase 4 graph lands; the gateway has no caller until then)"
    ),
    "src/simulation_orchestration/application/services.py:RunSimulationJob._checkpoint_policy": (
        "#246 (checkpoint boundary not yet consulted)"
    ),
    "src/simulation_orchestration/application/services.py:RunSimulationJob._uow": "#246 (UnitOfWork unused)",
    "src/simulation_orchestration/application/services.py:PauseOrResumeSimulation._uow": (
        "#246 (UnitOfWork unused)"
    ),
    "src/simulation_orchestration/application/services.py:RegisterPromptTemplate._clock": (
        "#246 (PromptVersioning stamps datetime.now instead)"
    ),
    "src/stakeholder_model/application/services.py:RecordHistoricalPosition._attribution_rule": (
        "#245 (attribution strength is client-supplied)"
    ),
    "src/stakeholder_model/application/services.py:RecordHistoricalPosition._corpus": "#245 (passage unverified)",
    "src/stakeholder_model/application/services.py:RecordHistoricalPosition._clock": "#246 (injected clock unused)",
    "src/stakeholder_model/application/services.py:RegisterStakeholder._clock": "#246 (injected clock unused)",
    "src/stakeholder_model/application/services.py:BindAgentPersona._clock": "#246 (injected clock unused)",
    "src/evidence_retrieval/application/services.py:AssembleEvidencePack._clock": "#246 (injected clock unused)",
    "src/evidence_corpus/infrastructure/repository/sqlalchemy.py:SqlAlchemyAuthorityRuleRepository._uow": (
        "#246 (UnitOfWork unused)"
    ),
    "src/evidence_corpus/infrastructure/indexing/memory.py:InMemoryIndexWriter.german_stopwords": (
        "#246 (stopwords configured, never applied — adapter parity)"
    ),
}


def _assigned(init: ast.FunctionDef) -> set[str]:
    names: set[str] = set()
    for node in ast.walk(init):
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if (
                    isinstance(target, ast.Attribute)
                    and isinstance(target.value, ast.Name)
                    and target.value.id == "self"
                ):
                    names.add(target.attr)
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Attribute):
            if isinstance(node.target.value, ast.Name) and node.target.value.id == "self":
                names.add(node.target.attr)
    return names


def _loaded(class_node: ast.ClassDef) -> set[str]:
    names: set[str] = set()
    for node in ast.walk(class_node):
        if (
            isinstance(node, ast.Attribute)
            and isinstance(node.ctx, ast.Load)
            and isinstance(node.value, ast.Name)
            and node.value.id == "self"
        ):
            names.add(node.attr)
    return names


def scan(root: pathlib.Path) -> list[tuple[str, int, str, str]]:
    """Return ``(path, line, class, attribute)`` for every injected-but-unread collaborator."""
    findings: list[tuple[str, int, str, str]] = []
    for path in sorted(root.rglob("*.py")):
        posix = path.as_posix()
        if posix.endswith(EXEMPT_SUFFIXES):
            continue
        try:
            tree = ast.parse(path.read_text())
        except SyntaxError:  # pragma: no cover - a syntax error is a different gate's problem
            continue
        for node in ast.walk(tree):
            if not isinstance(node, ast.ClassDef):
                continue
            init = next(
                (
                    item
                    for item in node.body
                    if isinstance(item, ast.FunctionDef) and item.name == "__init__"
                ),
                None,
            )
            if init is None:
                continue
            for attr in sorted(_assigned(init) - _loaded(node)):
                findings.append((posix, init.lineno, node.name, attr))
    return findings


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--strict", action="store_true", help="ignore the allowlist")
    parser.add_argument("--root", default=str(SOURCE_ROOT), help="source root (default: src)")
    args = parser.parse_args(argv)

    findings = scan(pathlib.Path(args.root))
    keys = {f"{path}:{cls}.{attr}" for path, _, cls, attr in findings}
    allowed = {} if args.strict else _ALLOWED

    unexplained = [f for f in findings if f"{f[0]}:{f[2]}.{f[3]}" not in allowed]
    stale = sorted(set(allowed) - keys)

    print("W8 collaborator reachability")
    print(f"  injected-but-unread: {len(findings)}")
    print(f"  allowlisted:         {len(keys & set(allowed))}")
    print(f"  unexplained:         {len(unexplained)}")
    for path, line, cls, attr in unexplained:
        print(f"    ✗ {path}:{line} {cls}.{attr}")
    if stale:
        print("  stale allowlist entries (attribute now used — remove the entry):")
        for key in stale:
            print(f"    ! {key} — {allowed[key]}")

    if unexplained:
        print("\nA collaborator assigned in __init__ and never read is not wired: give it a call site or")
        print("delete the injection. Tests that assert shapes cannot see this.")
        return 1
    if stale:
        print("\nAllowlist is stale; prune it so the ratchet stays meaningful.")
        return 1
    print("\nCollaborator reachability passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
