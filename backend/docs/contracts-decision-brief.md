# DecisionBrief — Frozen Contracts

**Issue:** #331 (Contract Freeze, epic #330) · **Module:** `.pi/architecture/modules/decision-brief.md`
**Status:** Frozen. Implementation issues may fill method bodies but may not rename, remove or
re-type a member listed here without a new freeze entry.

All interfaces are stubs: bodies raise `NotImplementedError` naming the implementing issue. The
module is **not** wired into `shared/app.py` yet — mounting, `app.state` binding and the runtime
path belong to the wiring and runtime-integration issues.

## Layers

| Layer | Files | Owns |
|---|---|---|
| Domain | `domain/values.py`, `entities.py`, `projections.py`, `decision_brief.py`, `errors.py`, `events.py`, `repositories.py`, `services.py` | Aggregate, VOs, disclosure vocabulary, events, gate predicates |
| Application | `application/commands.py`, `dto.py`, `ports.py`, `services.py` | Use-case requests/results, ACL ports, publication/versioning services |
| Infrastructure | `infrastructure/acl.py`, `infrastructure/repository/{ports.py}` | Upstream ACL adapters, citation resolver, provenance gate, repository adapters |
| Interfaces | `interfaces/http/{router,schemas,deps}.py`, `interfaces/renderer.py` | Concrete REST controller, wire schemas, JSON renderer |

Domain imports no outer layer and no other bounded context. Upstream published views are mapped to
`domain/projections.py` shapes by `infrastructure/acl.py`.

## Domain vocabulary (frozen)

| Type | Kind | Fields / members |
|---|---|---|
| `SectionKind` | enum | `question_summary`, `actors_involved`, `negotiation_history`, `conflict_analysis`, `compromise_proposals`, `consensus_analysis`, `open_disputes`, `impact` (ordinals 1–8 in `SECTION_ORDINAL`) |
| `EvidenceStatus` | enum | `evidenced`, `narrative`, `unsupported` |
| `BriefStatus` | enum | `draft`, `validating`, `blocked`, `published`, `superseded` |
| `OutcomeKind` | enum | `recommendation`, `blocked`, `open_dispute` |
| `BriefVersion` | VO | `number:int`, `run_id:RunId`, `snapshot_ref:str`, `generated_at:datetime`, `previous_version:int\|None`, `reason:str\|None` |
| `SimulationDisclaimer` | VO | `text:str`, `model_reference:str`, `prompt_version:str` |
| `CitationReference` | VO | `passage_id:PassageId`, `provenance:CitationProvenance\|None`, `quote:str\|None`, `is_resolved()` |
| `CitationProvenance` | VO | `outlet:str`, `published_on:date`, `medium:str`, `page_from:int`, `page_to:int`, `source_uri:str` |
| `CitedStatement` | VO | `text:str`, `status:EvidenceStatus`, `citations:tuple[CitationReference,...]`, `claim_ids:tuple[str,...]` |
| `ActorSummary` | VO | `institution:str`, `goals`, `constraints`, `adopted_positions` |
| `PositionStance` / `PositionTimeline` | VO | `round_no:int`, `stance:str`, `rationale:str\|None` / `actor:str`, `stances:tuple[PositionStance,...]` |
| `BriefComponentSlot` | VO | `kind:SectionKind`, `ordinal:int`, `completed:bool` |
| `TopicOutcome` | VO | `topic:str`, `kind:OutcomeKind`, `blocking_stakeholders`, `reason:str\|None` |
| `BriefSection` | entity | `kind:SectionKind`, `ordinal:int`, `statements:tuple[CitedStatement,...]` |
| `RejectedProposalRecord` | entity | `measure:str`, `blocking_stakeholders`, `reasons` |
| `DecisionBrief` | aggregate | `id`, `run_id`, `version`, `sections`, `rejected_proposals`, `disclaimer`, `outcomes`, `status`, `events` |

`REQUIRED_SECTIONS` is exactly the eight `SectionKind` members. `DEFAULT_DISCLAIMER_TEXT` is the
fixed disclosure wording.

Construction invariants (#333) — a value that exists is valid; violations raise `ValueError`:

| Type | Rejected form |
|---|---|
| `BriefSection`, `BriefComponentSlot` | ordinal that is not the kind's frozen ordinal |
| `CitedStatement` | blank text |
| `CitationReference` | blank passage id; blank quote when present |
| `CitationProvenance` | blank outlet/source URI; `page_from < 1`; `page_to < page_from` |
| `RejectedProposalRecord` | blank measure; no blocking stakeholder |
| `SimulationDisclaimer` | blank text, model or prompt reference |
| `BriefVersion` | number `< 1`; blank snapshot; naive `generated_at`; successor without an earlier `previous_version` and a reason; reason on version 1 |
| `ActorSummary` / `PositionStance` / `PositionTimeline` | blank institution/actor/stance; `round_no < 1` |
| `TopicOutcome` | blank topic; `blocked` without naming a blocker |

### Aggregate surface

```text
missing_sections() -> frozenset[SectionKind]           # implemented: required - present
unresolved_citations() -> tuple[CitationReference,...]  # implemented: reading order
citation_count() -> int                                # implemented: publication payload
is_published() -> bool                                 # implemented
assert_statement_evidence(statement) -> None           # implemented: evidenced needs a citation
assert_rejected_proposals_disclosed(measures) -> None   # implemented (#332): run disclosure gate
publish() -> None                                      # implemented (#332): all gates, then freeze
assert_immutable() -> None                             # implemented (#332): published guard
supersede_by(successor, *, reason) -> DecisionBrief    # stub: lineage issue
```

`publish()` runs its gates in reading order and only then freezes: completeness →
`IncompleteBrief`; statement evidence → `StatementWithoutCitation`; citation integrity →
`CitationResolutionFailed` + `UnresolvedCitation`; disclaimer → `BriefBlockedByMissingDisclosure` +
`DisclosureMissing`. A blocked attempt leaves the brief in `BriefStatus.BLOCKED` with its audit
events, never partially published.

Rejected-proposal completeness needs the run, so the use case calls
`assert_rejected_proposals_disclosed(run_rejected_measures)` before `publish()` (additive member,
recorded in #332; an empty run list is a legitimate "no refusals" result).

Repositories (`domain/repositories.py`): `get(brief_id)`, `save(brief)`, `versions_for_run(run_id)`
— all async. Table/column layout is **out of bounds**.

## Domain projections (input contracts, frozen)

`RunProjection{run_id, question, actors, timelines, history, conflicts, compromises,
rejected_proposals, blocked_topics, claim_verdicts, log_position, snapshot_ref}` and
`ConsensusProjection{run_id, statements, majority, minority, unresolved, packages, impact,
log_position}`. Supporting records: `HistoryEntry`, `ConflictRecord`, `CompromiseRecord`,
`ClaimVerdictProjection`, `ConsensusStatement`, `ReproductionInput`.

## Application contracts (frozen)

Requests: `PublishDecisionBriefRequest{run_id, requested_by}`, `VersionDecisionBriefRequest{brief_id,
reason, requested_by}`, `GetDecisionBriefRequest{brief_id}`, `ListBriefVersionsRequest{run_id}`,
`ListCitationsRequest{brief_id, section}`.

Results: `BriefResult{brief, citation_count}`, `BriefListResult{items}`, `CitationListResult{brief_id,
section, citations}`, `CitationResolution{resolved, unresolved, is_complete}`.

Services (`application/services.py`, every one exposes `execute(request)` and `collaborators()`):

| Service | Collaborators |
|---|---|
| `PublishDecisionBrief` | `briefs, history, consensus, citations, provenance, projection, disclaimer, events, clock, ids, uow` |
| `VersionDecisionBrief` | `briefs, events, clock, ids, uow` |
| `GetDecisionBrief` | `briefs` |
| `ListBriefVersions` | `briefs` |
| `ListCitations` | `briefs` |

Ports (`application/ports.py`): `Clock`, `UnitOfWork`, `IdFactory`, `EventPublisher`,
`RunHistorySource.load(run_id) -> RunProjection|None`, `ConsensusSource.load(run_id) ->
ConsensusProjection|None`, `CitationResolver.resolve(passage_ids) -> CitationResolution`,
`ProvenanceDisclosureGate.assert_disclosed(run_id) -> None`.

Service classification (`domain/services.py::SERVICE_CLASSIFICATION`):
application = the five use cases; domain = `BriefProjectionBuilder`, `ReproductionChecker`,
`OutcomeHonestyPolicy`; infrastructure = `CitationResolver`, `ProvenanceDisclosureGate`;
interfaces = `BriefRenderer`.

Classification is machine-checked (#334): a test resolves each classified name to the file that
defines it and fails when the declared layer is not the owning layer, when a port is not an
application-layer runtime protocol, or when an infrastructure-classified port has no adapter with a
matching method signature.

Implemented services: `GetDecisionBrief`, `ListBriefVersions` and `ListCitations` read through
`DecisionBriefRepository` (`BriefNotFound` for unknown ids; `BriefNotPublished` before publishing).
`PublishDecisionBrief`, `VersionDecisionBrief` and `DecisionBrief.supersede_by` remain stubs owned by
their gate issues.

## API contract (frozen)

All routes are under `/api/v1` and declare `x-required-scope` (enforced, not decorative).

| Method | Path | Request | Response | Status | Scope |
|---|---|---|---|---|---|
| POST | `/runs/{run_id}/brief` | — | `BriefResponse` | 201 | `briefs:publish` |
| GET | `/briefs/{brief_id}` | — | `BriefResponse` | 200 | `runs:read` |
| GET | `/runs/{run_id}/briefs` | — | `BriefVersionListResponse` | 200 | `runs:read` |
| POST | `/briefs/{brief_id}:version` | `VersionBriefBody{reason: min 1 char}` | `VersionBriefResponse` | 201 | `briefs:publish` |
| GET | `/briefs/{brief_id}/citations` | `?section=` | `CitationListResponse` | 200 | `runs:read` |

`BriefResponse` (also the JSON document contract, `schema_version = "1.0"`):

```text
brief_id, run_id, status, version{number, run_id, snapshot_ref, generated_at,
previous_version, reason}, sections[{kind, ordinal, statements[{text, status, claim_ids,
citations[{passage_id, resolved, quote, outlet, published_on, medium, page_from, page_to,
source_uri}]}]}], rejected_proposals[{measure, blocking_stakeholders, reasons}],
outcomes[{topic, kind, blocking_stakeholders, reason}],
disclaimer{text, model_reference, prompt_version}, citation_count, schema_version
```

`disclaimer` and the version reference are mandatory in the document (AC 10).

## Event contract (frozen)

| Event | Payload |
|---|---|
| `DecisionBriefPublished` | `brief_id, run_id, version, section_count, citation_count` |
| `DecisionBriefVersioned` | `brief_id, previous_version, reason` |
| `CitationResolutionFailed` | `brief_id, unresolved_count, first_passage_id` |
| `RejectedProposalDisclosed` | `brief_id, measure, blocker_ids` |
| `BriefBlockedByMissingDisclosure` | `brief_id, missing` |

All five travel through the shared outbox; the two blocked-publication events are audit-critical.

## Error contract (frozen codes)

| Error | HTTP | Code | Raised when |
|---|---|---|---|
| `IncompleteBrief` | 422 | `INCOMPLETE_BRIEF` | fewer than eight sections (`missing`) |
| `UnresolvedCitation` | 422 | `UNRESOLVED_CITATION` | a citation has no provenance (`brief_id`, `passage_id`) |
| `DisclosureMissing` | 422 | `DISCLOSURE_MISSING` | rejected proposals or disclaimer absent (`missing`) |
| `StatementWithoutCitation` | 422 | `STATEMENT_WITHOUT_CITATION` | `evidenced` statement with no citation |
| `BlockedOutcomeMisrendered` | 422 | `BLOCKED_OUTCOME_MISRENDERED` | veto-blocked topic rendered as recommendation |
| `PublishedBriefIsImmutable` | 409 | `PUBLISHED_BRIEF_IMMUTABLE` | mutating a published version |
| `BriefNotPublished` | 409 | `BRIEF_NOT_PUBLISHED` | versioning/listing citations of a draft |
| `BriefReproductionMismatch` | 409 | `BRIEF_REPRODUCTION_MISMATCH` | regeneration differs |
| `BriefNotFound` | 404 | `BRIEF_NOT_FOUND` | unknown brief id |
| `BriefGateUnavailable` | 503 | `BRIEF_GATE_UNAVAILABLE` | container or a publication gate is unwired — **the gate can never be skipped** |

Error bodies use the shared envelope `{code, message, details, trace_id}`.

## Wiring obligations (not yet met — later issues)

1. `shared/app.py`: `app.state.decision_brief = build_container(...)` and
   `app.include_router(decision_brief_router)` (additive union with sibling epics).
2. `build_container` requires every gate as a keyword argument; no permissive default.
3. `briefs:publish` must yield 403 for an analyst key.
4. Migration `0502_decision_brief` is reserved and applied by the persistence issue.

## Out of bounds (deliberately not frozen)

Internal algorithms, database column names, ORM annotations, PDF rendering, and any shape not
listed above.
