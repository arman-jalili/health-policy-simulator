"""Structural contract checks for GovernanceCompliance (contract freeze, issue #248).

The generated TDD placeholders used hyphenated identifiers and could not be imported. These
checks assert the frozen surface instead: layer depth, DTO fields, service/port signatures,
rule ids, error codes, HTTP routes, published views and the composition factory.
"""

from __future__ import annotations

import ast
import inspect
from dataclasses import fields
from pathlib import Path
from typing import Any, ClassVar, cast

import pytest

from governance_compliance.application import (
    commands,
    dto,
    errors,
    events,
    ports,
    repositories,
    rules,
)
from governance_compliance.application.services import (
    DisclosePositionProvenance,
    EnforceInstitutionOnlyOutput,
    GetPositionProvenance,
    ListAllowlist,
    ListViolations,
    RecordGovernanceViolation,
    ValidateInstitutionalAllowlist,
)
from governance_compliance.application.values import (
    AllowlistEntry,
    FigureVerdict,
    GuardDecision,
    GuardRuleId,
    InstitutionalAllowlist,
    PositionId,
    SpeakerKind,
    ViolationClass,
)
from governance_compliance.composition import (
    GovernanceComplianceContainer,
    build_container,
)
from governance_compliance.interfaces import published
from governance_compliance.interfaces.http import schemas
from governance_compliance.interfaces.http.router import router

ROOT = Path(__file__).resolve().parents[4]
MODULE = ROOT / "src" / "governance_compliance"


def _field_names(model: type[Any]) -> set[str]:
    if hasattr(model, "model_fields"):
        return set(model.model_fields)
    return {field.name for field in fields(model)}


def _signature_params(target: Any) -> set[str]:
    return set(inspect.signature(target).parameters)


class TestLayerDepth:
    def test_service_depth_has_application_and_infrastructure_modules(self) -> None:
        assert any((MODULE / "application").glob("*.py"))
        assert any((MODULE / "infrastructure").glob("*.py"))
        assert (MODULE / "interfaces").is_dir()

    def test_domain_is_an_empty_adr_008_marker(self) -> None:
        domain_modules = [
            path.name for path in (MODULE / "domain").glob("*.py") if path.name != "__init__.py"
        ]
        assert domain_modules == []

    def test_application_layer_does_not_import_frameworks_adapters_or_routers(self) -> None:
        forbidden = ("fastapi", "sqlalchemy", "pydantic", "governance_compliance.infrastructure")
        violations: list[str] = []
        for path in (MODULE / "application").glob("*.py"):
            tree = ast.parse(path.read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    names = [alias.name for alias in node.names]
                elif isinstance(node, ast.ImportFrom) and node.module:
                    names = [node.module]
                else:
                    continue
                for name in names:
                    if any(name.startswith(prefix) for prefix in forbidden):
                        violations.append(f"{path.name}: {name}")
        assert violations == []


class TestValues:
    def test_guard_decisions_are_frozen(self) -> None:
        assert [decision.value for decision in GuardDecision] == ["accept", "rewrite", "reject"]

    def test_violation_classes_are_frozen(self) -> None:
        assert {item.value for item in ViolationClass} == {
            "person_named",
            "personal_quotation",
            "institution_ambiguous",
            "unsupported_fact",
            "contradicted_figure",
        }

    def test_speaker_kinds_match_the_corpus_vocabulary(self) -> None:
        assert {item.value for item in SpeakerKind} == {"institution", "person", "anonymous"}

    def test_figure_verdicts_are_frozen(self) -> None:
        assert {item.value for item in FigureVerdict} == {
            "verified",
            "contradicted",
            "unsupported",
            "ambiguous",
            "missing",
        }

    def test_guard_rule_ids_are_frozen(self) -> None:
        assert {item.value for item in GuardRuleId} == {
            "GC-001",
            "GC-002",
            "GC-003",
            "GC-004",
            "GC-005",
        }

    def test_allowlist_empty_means_boot_failure_not_permit_all(self) -> None:
        assert InstitutionalAllowlist().is_empty is True
        allowlist = InstitutionalAllowlist(
            institutions=(
                AllowlistEntry(
                    code="bmsgpk",
                    canonical_name=(
                        "Bundesministerium für Soziales, Gesundheit, Pflege und Konsumentenschutz"
                    ),
                    short_name="BMSGPK",
                    category="ministry",
                    aliases=("Gesundheitsministerium",),
                ),
            )
        )
        assert allowlist.is_empty is False
        assert allowlist.canonical_names == (
            "Bundesministerium für Soziales, Gesundheit, Pflege und Konsumentenschutz",
        )


class TestCommandsAndDtos:
    @pytest.mark.parametrize(
        ("command", "expected"),
        [
            (
                commands.EnforceInstitutionOnlyOutputRequest,
                {
                    "text",
                    "speaker_kind",
                    "invocation_id",
                    "run_id",
                    "position_id",
                    "cited_passage_ids",
                    "reference_figure_ids",
                },
            ),
            (
                commands.DisclosePositionProvenanceRequest,
                {"position_id", "version", "requested_by"},
            ),
            (
                commands.RecordGovernanceViolationRequest,
                {
                    "run_id",
                    "invocation_id",
                    "violation_class",
                    "offending_span",
                    "rewritten_span",
                    "rule_id",
                },
            ),
            (commands.ListViolationsRequest, {"run_id", "violation_class", "limit"}),
            (commands.GetPositionProvenanceRequest, {"position_id", "version"}),
            (commands.ValidateInstitutionalAllowlistRequest, {"allowlist"}),
        ],
    )
    def test_command_fields_are_frozen(self, command: type[Any], expected: set[str]) -> None:
        assert _field_names(command) == expected

    @pytest.mark.parametrize(
        ("record", "expected"),
        [
            (
                dto.ViolationRecord,
                {
                    "violation_id",
                    "run_id",
                    "invocation_id",
                    "violation_class",
                    "offending_span",
                    "rewritten_span",
                    "rule_id",
                    "rule_version",
                    "violation_hash",
                    "detected_at",
                },
            ),
            (
                dto.GuardVerdictResult,
                {"decision", "violations", "rewritten_text", "rule_version"},
            ),
            (
                dto.ProvenanceRecord,
                {
                    "position_id",
                    "evidence_ids",
                    "argument_ids",
                    "invocation_id",
                    "prompt_version",
                    "model",
                    "disclosed_at",
                    "version",
                },
            ),
            (
                dto.ProvenanceFacts,
                {
                    "position_id",
                    "evidence_ids",
                    "argument_ids",
                    "invocation_id",
                    "prompt_version",
                    "model",
                },
            ),
            (dto.ProvenanceResult, {"record"}),
            (dto.ViolationListResult, {"items"}),
            (dto.AllowlistResult, {"institutions", "version"}),
            (dto.AllowlistValidationResult, {"valid", "institution_count", "problems"}),
        ],
    )
    def test_result_dto_fields_are_frozen(self, record: type[Any], expected: set[str]) -> None:
        assert _field_names(record) == expected


class TestServices:
    @pytest.mark.parametrize(
        "service",
        [
            EnforceInstitutionOnlyOutput,
            DisclosePositionProvenance,
            RecordGovernanceViolation,
            ListViolations,
            GetPositionProvenance,
            ListAllowlist,
        ],
    )
    def test_async_services_expose_an_async_execute(self, service: type[Any]) -> None:
        assert inspect.iscoroutinefunction(service.execute)

    def test_allowlist_validation_is_synchronous(self) -> None:
        assert not inspect.iscoroutinefunction(ValidateInstitutionalAllowlist.execute)

    @pytest.mark.parametrize(
        ("service", "expected"),
        [
            (
                EnforceInstitutionOnlyOutput,
                {"rules", "allowlist", "violations", "clock", "uow"},
            ),
            (DisclosePositionProvenance, {"facts", "store", "clock", "uow"}),
            (RecordGovernanceViolation, {"violations", "clock", "uow"}),
            (ListViolations, {"violations"}),
            (GetPositionProvenance, {"store"}),
            (ListAllowlist, {"allowlist"}),
            (ValidateInstitutionalAllowlist, set()),
        ],
    )
    def test_service_constructor_is_frozen(self, service: type[Any], expected: set[str]) -> None:
        assert _signature_params(service.__init__) == {"self", *expected}


class TestRulesAndPorts:
    @pytest.mark.parametrize(
        ("rule", "rule_id"),
        [
            (rules.PersonReferenceRule, GuardRuleId.GC_001),
            (rules.PersonalQuotationRule, GuardRuleId.GC_002),
            (rules.InstitutionAliasRule, GuardRuleId.GC_003),
            (rules.UnsupportedFactRule, GuardRuleId.GC_004),
            (rules.ContradictedFigureRule, GuardRuleId.GC_005),
        ],
    )
    def test_rule_classes_declare_their_rule_id(
        self, rule: type[Any], rule_id: GuardRuleId
    ) -> None:
        assert rule.rule_id is rule_id
        assert hasattr(rule, "evaluate")

    def test_rule_chain_is_frozen(self) -> None:
        assert _signature_params(rules.GuardRuleChain.__init__) == {"self", "rules"}
        assert _field_names(rules.GuardRuleContext) == {
            "text",
            "speaker_kind",
            "allowlist",
            "cited_passage_ids",
            "reference_figure_ids",
            "person_detector",
            "institution_resolver",
            "figure_verdicts",
        }

    @pytest.mark.parametrize(
        ("protocol", "methods"),
        [
            (ports.Clock, {"now"}),
            (ports.UnitOfWork, {"transaction"}),
            (ports.PersonNameDetector, {"detect"}),
            (ports.InstitutionResolver, {"resolve"}),
            (ports.FigureVerdictLookup, {"verdict_for"}),
            (ports.AllowlistSource, {"load"}),
            (ports.ProvenanceFactsSource, {"load"}),
            (ports.InstitutionGuard, {"execute"}),
            (ports.EventPublisher, {"publish"}),
        ],
    )
    def test_ports_declare_their_methods(self, protocol: type[Any], methods: set[str]) -> None:
        assert methods.issubset(set(dir(protocol)))

    @pytest.mark.parametrize(
        ("store", "methods"),
        [
            (repositories.ViolationStore, {"add", "get_by_hash", "list"}),
            (repositories.ProvenanceStore, {"save", "get", "list_for_position"}),
        ],
    )
    def test_repository_ports_are_frozen(self, store: type[Any], methods: set[str]) -> None:
        assert methods.issubset(set(dir(store)))

    def test_events_are_application_level_not_domain_events(self) -> None:
        assert not (MODULE / "domain" / "events.py").exists()
        assert events.GovernanceViolationRecorded.name == "GovernanceViolationRecorded"
        assert _field_names(events.GovernanceViolationRecorded) == {
            "violation_id",
            "run_id",
            "invocation_id",
            "violation_class",
            "rule_id",
            "detected_at",
        }


class TestErrors:
    @pytest.mark.parametrize(
        ("error", "code", "status"),
        [
            (errors.GovernanceViolationNotFound, "GOVERNANCE_VIOLATION_NOT_FOUND", 404),
            (errors.ProvenanceIncomplete, "PROVENANCE_INCOMPLETE", 422),
            (errors.AllowlistEmpty, "ALLOWLIST_EMPTY", 500),
            (errors.AllowlistContainsPerson, "ALLOWLIST_CONTAINS_PERSON", 500),
            (errors.GuardVerdictRequired, "GUARD_VERDICT_REQUIRED", 409),
            (errors.GuardUnavailable, "GOVERNANCE_GUARD_UNAVAILABLE", 503),
            (errors.UnknownGovernanceRule, "UNKNOWN_GOVERNANCE_RULE", 422),
        ],
    )
    def test_error_codes_and_statuses_are_frozen(
        self, error: type[Any], code: str, status: int
    ) -> None:
        assert error.code == code
        assert error.status_code == status


class TestHttpContract:
    EXPECTED: ClassVar[dict[tuple[str, str], tuple[str, str, int]]] = {
        ("POST", "/api/v1/governance/check"): (
            "enforce_institution_only_output",
            "runs:write",
            200,
        ),
        ("GET", "/api/v1/governance/violations"): ("list_violations", "runs:read", 200),
        ("GET", "/api/v1/positions/{position_id}/provenance"): (
            "get_position_provenance",
            "runs:read",
            200,
        ),
        ("POST", "/api/v1/positions/{position_id}/provenance"): (
            "disclose_position_provenance",
            "runs:write",
            201,
        ),
        ("GET", "/api/v1/governance/allowlist"): ("list_allowlist", "admin", 200),
    }

    def test_exactly_five_governance_routes_are_frozen(self) -> None:
        actual = {
            (next(iter(cast(Any, route).methods)), cast(Any, route).path): (
                cast(Any, route).name,
                (cast(Any, route).openapi_extra or {}).get("x-required-scope"),
                cast(Any, route).status_code,
            )
            for route in router.routes
        }
        assert actual == self.EXPECTED

    def test_guard_request_and_response_fields_are_frozen(self) -> None:
        assert _field_names(schemas.GuardCheckBody) == {
            "text",
            "speaker_kind",
            "invocation_id",
            "run_id",
            "position_id",
            "cited_passage_ids",
            "reference_figure_ids",
        }
        assert _field_names(schemas.GuardCheckResponse) == {
            "decision",
            "violations",
            "rewritten_text",
            "rule_version",
        }

    @pytest.mark.parametrize(
        ("schema", "expected"),
        [
            (
                schemas.ViolationItem,
                {
                    "violation_id",
                    "violation_class",
                    "offending_span",
                    "rewritten_span",
                    "rule_id",
                    "rule_version",
                    "detected_at",
                },
            ),
            (schemas.ViolationListResponse, {"items"}),
            (
                schemas.ProvenanceResponse,
                {
                    "position_id",
                    "evidence_ids",
                    "argument_ids",
                    "invocation_id",
                    "prompt_version",
                    "model",
                    "disclosed_at",
                    "version",
                },
            ),
            (schemas.DiscloseProvenanceBody, {"version", "requested_by"}),
            (
                schemas.AllowlistItem,
                {"code", "canonical_name", "short_name", "category", "aliases"},
            ),
            (schemas.AllowlistResponse, {"institutions", "version"}),
            (
                schemas.AllowlistValidationResponse,
                {"valid", "institution_count", "problems"},
            ),
        ],
    )
    def test_http_schema_fields_are_frozen(self, schema: type[Any], expected: set[str]) -> None:
        assert _field_names(schema) == expected


class TestPublishedAndComposition:
    def test_published_views_are_frozen(self) -> None:
        assert _field_names(published.GuardVerdictView) == {
            "decision",
            "violations",
            "rewritten_text",
            "rule_version",
        }
        assert _field_names(published.PositionProvenanceView) == {
            "position_id",
            "evidence_ids",
            "argument_ids",
            "invocation_id",
            "prompt_version",
            "model",
            "disclosed_at",
        }

    def test_container_fields_are_frozen(self) -> None:
        assert _field_names(GovernanceComplianceContainer) == {
            "allowlist",
            "enforce_institution_only_output",
            "disclose_position_provenance",
            "record_governance_violation",
            "validate_allowlist",
            "list_violations",
            "get_position_provenance",
            "list_allowlist",
        }

    def test_build_container_signature_is_frozen(self) -> None:
        assert _signature_params(build_container) == {
            "settings",
            "database",
            "allowlist_source",
            "figure_verdicts",
        }

    def test_published_mappers_exist(self) -> None:
        assert callable(published.to_guard_verdict_view)
        assert callable(published.to_position_provenance_view)

    def test_position_id_is_a_distinct_contract_type(self) -> None:
        assert PositionId("pos_1") == "pos_1"
