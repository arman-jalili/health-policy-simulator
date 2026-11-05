"""ADR-008: GovernanceCompliance stays at service depth."""

from __future__ import annotations

from pathlib import Path

MODULE = Path(__file__).resolve().parents[4] / "src" / "governance_compliance"


def test_domain_contains_only_the_empty_marker() -> None:
    assert [path.name for path in (MODULE / "domain").glob("*.py")] == ["__init__.py"]


def test_no_domain_modules_exist() -> None:
    names = {path.stem for path in (MODULE / "domain").glob("*.py")}
    assert not names & {"entities", "aggregate", "aggregates", "value_objects", "events"}
