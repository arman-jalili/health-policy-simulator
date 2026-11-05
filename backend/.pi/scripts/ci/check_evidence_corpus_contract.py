#!/usr/bin/env python3
"""Deterministic proofing checks for the EvidenceCorpus contract.

Every frozen contract has at least one mechanical check here, so a refactor that silently drops a
route, an enum member, an event payload, a port implementation or the authority rubric fails CI
instead of a review.

Usage: python3 .pi/scripts/ci/check_evidence_corpus_contract.py [--json]
Exit:  0 = conformant, 1 = violation.
"""

from __future__ import annotations

import argparse
import dataclasses
import importlib
import inspect
import json
import sys
from pathlib import Path
from typing import Any

import os

REPO_ROOT = Path(__file__).resolve().parents[3]

# The project targets Python 3.12+ (StrEnum, PEP 695). Re-exec inside .venv when an older
# interpreter invoked this script directly, so the proofing result never depends on which python3
# happens to be first on PATH.
_VENV_PYTHON = REPO_ROOT / ".venv" / "bin" / "python"
if sys.version_info < (3, 11) and _VENV_PYTHON.is_file() and os.environ.get("_HPS_REEXEC") != "1":
    os.environ["_HPS_REEXEC"] = "1"
    os.execv(str(_VENV_PYTHON), [str(_VENV_PYTHON), *sys.argv])
SRC = REPO_ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

EXPECTED_ENDPOINTS: dict[str, set[str]] = {
    "/api/v1/corpus/documents": {"post"},
    "/api/v1/corpus/ingestion-runs": {"post"},
    "/api/v1/corpus/ingestion-runs/{run_id}": {"get"},
    "/api/v1/documents/{document_id}": {"get"},
    "/api/v1/passages/{passage_id}": {"get"},
    "/api/v1/corpus/snapshots": {"post"},
    "/api/v1/corpus/snapshots/{snapshot_id}": {"get"},
    "/api/v1/corpus/authority-rules": {"get"},
}

EXPECTED_ENUMS: dict[str, set[str]] = {
    "AuthorityTier": {
        "official_statistics",
        "legislation",
        "scientific_study",
        "institutional_statement",
        "press_report",
        "other",
    },
    "SourceType": {
        "official_statistics",
        "legislation",
        "scientific_study",
        "institutional_statement",
        "press_report",
        "other",
        "unknown",
    },
    "SpeakerKind": {"institution", "person", "anonymous"},
    "ClaimType": {"quantitative", "legal", "causal", "qualitative"},
    "ArticleSection": {"headline", "standfirst", "body", "caption", "quotation"},
    "ExtractionMethod": {"native", "ocr"},
    "RunStatus": {"running", "completed", "failed"},
    "IngestionOutcome": {"accepted", "quarantined", "failed"},
}

PORTS = [
    ("evidence_corpus.domain.repositories", "DocumentRepository"),
    ("evidence_corpus.domain.repositories", "ArticleRepository"),
    ("evidence_corpus.domain.repositories", "PassageRepository"),
    ("evidence_corpus.domain.repositories", "IngestionRunRepository"),
    ("evidence_corpus.domain.repositories", "CorpusSnapshotRepository"),
    ("evidence_corpus.domain.repositories", "AuthorityRuleRepository"),
    ("evidence_corpus.application.ports", "ExtractionPort"),
    ("evidence_corpus.application.ports", "OcrPort"),
    ("evidence_corpus.application.ports", "IndexWriterPort"),
    ("evidence_corpus.application.events", "EventPublisher"),
]

REQUIRED_ADAPTERS = {
    "DocumentRepository": "evidence_corpus.infrastructure.memory",
    "ArticleRepository": "evidence_corpus.infrastructure.memory",
    "PassageRepository": "evidence_corpus.infrastructure.memory",
    "IngestionRunRepository": "evidence_corpus.infrastructure.memory",
    "CorpusSnapshotRepository": "evidence_corpus.infrastructure.memory",
    "AuthorityRuleRepository": "evidence_corpus.infrastructure.memory",
    "ExtractionPort": "evidence_corpus.infrastructure.extraction.pymupdf",
    "OcrPort": "evidence_corpus.infrastructure.extraction.ocr",
    "IndexWriterPort": "evidence_corpus.infrastructure.indexing.memory",
    "EventPublisher": "evidence_corpus.infrastructure.events",
}


def _import(path: str) -> Any:
    return importlib.import_module(path)


def check_endpoints(app: Any | None = None) -> list[str]:
    errors: list[str] = []
    if app is None:
        from shared.app import create_app
        from shared.config import Settings

        settings = Settings(
            _env_file=None,
            database_url="postgresql+asyncpg://ci:ci@localhost:5432/ci",
        )
        app = create_app(settings)

    paths = app.openapi().get("paths", {})
    for path, methods in EXPECTED_ENDPOINTS.items():
        if path not in paths:
            errors.append(f"endpoint missing from OpenAPI: {path}")
            continue
        available = {method.lower() for method in paths[path]}
        for method in methods - available:
            errors.append(f"method missing: {method.upper()} {path}")
    return errors


def check_enums() -> list[str]:
    errors: list[str] = []
    values = _import("evidence_corpus.domain.values")
    entities = _import("evidence_corpus.domain.entities")
    for name, expected in EXPECTED_ENUMS.items():
        enum_cls = getattr(values, name, None) or getattr(entities, name, None)
        if enum_cls is None:
            errors.append(f"enum missing: {name}")
            continue
        actual = {str(member.value) for member in enum_cls}
        if actual != expected:
            errors.append(f"{name} members drifted: {sorted(actual ^ expected)}")
    return errors


def check_authority_rules() -> list[str]:
    errors: list[str] = []
    values = _import("evidence_corpus.domain.values")
    rules = values.AUTHORITY_RULES
    if set(rules) != set(values.ClaimType):
        errors.append("authority rubric does not cover every claim type")
    for claim_type, order in rules.items():
        if values.SourceType.UNKNOWN in order:
            errors.append(f"{claim_type}: UNKNOWN must never appear in the rubric")
        if order[0] is values.SourceType.PRESS_REPORT:
            errors.append(f"{claim_type}: press must not outrank authoritative sources")
        if order[-1] is not values.SourceType.OTHER:
            errors.append(f"{claim_type}: OTHER must rank last")
    return errors


def check_events() -> list[str]:
    errors: list[str] = []
    events = _import("evidence_corpus.domain.events")
    for name, value in vars(events).items():
        if not dataclasses.is_dataclass(value) or not inspect.isclass(value):
            continue
        if value.__module__ != events.__name__:
            continue
        event_name = getattr(value, "name", None)
        if not isinstance(event_name, str):
            errors.append(f"{name}: domain event has no name")
        elif event_name != name:
            errors.append(f"{name}: event name {event_name!r} does not match the class")
        fields = {field.name for field in dataclasses.fields(value)}
        if not fields:
            errors.append(f"{name}: event payload is empty")
    if not any(dataclasses.is_dataclass(value) for value in vars(events).values()):
        errors.append("no domain events declared")
    return errors


def check_error_codes() -> list[str]:
    errors: list[str] = []
    errors_module = _import("evidence_corpus.domain.errors")
    codes: list[str] = []
    for name, value in vars(errors_module).items():
        if not inspect.isclass(value) or name.startswith("_"):
            continue
        code = getattr(value, "code", None)
        if isinstance(code, str):
            codes.append(code)
            if not code.isupper():
                errors.append(f"{name}: error code {code!r} is not UPPER_SNAKE_CASE")
    duplicates = {code for code in codes if codes.count(code) > 1}
    if duplicates:
        errors.append(f"duplicate error codes: {sorted(duplicates)}")
    if len(codes) < 5:
        errors.append("expected the corpus error vocabulary to be declared")
    return errors


def _protocol_methods(protocol: type) -> set[str]:
    return {
        name
        for name, value in vars(protocol).items()
        if not name.startswith("_") and callable(value)
    }


def check_port_implementations() -> list[str]:
    errors: list[str] = []
    for module_path, name in PORTS:
        module = _import(module_path)
        protocol = getattr(module, name, None)
        if protocol is None:
            errors.append(f"port missing: {name}")
            continue
        adapter_path = REQUIRED_ADAPTERS[name]
        adapter_module = _import(adapter_path)
        required = _protocol_methods(protocol)
        implemented = False
        for candidate in vars(adapter_module).values():
            if not inspect.isclass(candidate):
                continue
            methods = {
                attr for attr, value in vars(candidate).items() if callable(value)
            }
            if required and required <= methods:
                implemented = True
                break
        if not implemented:
            errors.append(
                f"{name}: no implementation of {sorted(required)} in {adapter_path}"
            )
    return errors


def check_invariants() -> list[str]:
    errors: list[str] = []
    entities = _import("evidence_corpus.domain.entities")
    for method in (
        "record_extraction",
        "add_article",
        "classify",
        "is_citable",
        "publishable_passages",
        "drain_events",
    ):
        if not hasattr(entities.Document, method):
            errors.append(f"Document.{method} missing")
    for method in ("add_passage", "publishable_passages", "passage_count"):
        if not hasattr(entities.Article, method):
            errors.append(f"Article.{method} missing")

    # Contract stubs must not survive in the domain or application layers. Infrastructure
    # adapters may still be placeholders (document persistence is in-memory for the prototype),
    # but the domain and use cases may never depend on a stub.
    for layer in ("domain", "application"):
        sources = "\n".join(
            path.read_text(encoding="utf-8")
            for path in (SRC / "evidence_corpus" / layer).rglob("*.py")
        )
        if "is a frozen stub" in sources:
            errors.append(f"a frozen contract stub is still reachable in {layer}/")
    return errors


def run_all(app: Any | None = None) -> list[str]:
    checks = [
        ("endpoints", lambda: check_endpoints(app)),
        ("enums", check_enums),
        ("authority rubric", check_authority_rules),
        ("events", check_events),
        ("error codes", check_error_codes),
        ("ports", check_port_implementations),
        ("invariants", check_invariants),
    ]
    errors: list[str] = []
    for label, check in checks:
        problems = check()
        errors.extend(f"[{label}] {problem}" for problem in problems)
    return errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="EvidenceCorpus contract proofing")
    parser.add_argument("--json", action="store_true", dest="as_json")
    args = parser.parse_args(argv)

    errors = run_all()
    if args.as_json:
        print(json.dumps({"errors": errors}, indent=2))
    else:
        print("============================================")
        print("  EvidenceCorpus Contract Proofing")
        print("============================================")
        for error in errors:
            print(f"  FAIL  {error}")
        print()
        print(f"  Checks: 7  Failed: {len(errors)}")
        if not errors:
            print("  Contract proofs hold.")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
