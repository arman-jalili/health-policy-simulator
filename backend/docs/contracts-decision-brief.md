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
fixed disclosure wording, and `SimulationDisclaimer.canonical(model_reference=,
prompt_version=)` is the only sanctioned way to build the disclosure (#338): the wording cannot be
rewritten per client, and the generation reference stays mandatory.

Construction invariants (#333) — a value that exists is valid; violations raise `ValueError`:

| Type | Rejected form |
|---|---|
| `BriefSection`, `BriefComponentSlot` | ordinal that is not the kind's frozen ordinal |
| `CitedStatement` | blank text; `assert_evidence()` refuses an `evidenced` statement with no citation (claim ids never substitute) |
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
resolve_citations(resolved) -> None                    # implemented (#336): fold resolver output in
publish() -> None                                      # implemented (#332): all gates, then freeze
assert_immutable() -> None                             # implemented (#332): published guard
supersede_by(successor, *, reason) -> DecisionBrief    # implemented (#341): N -> SUPERSEDED, return N+1
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

## JSON rendering (#344)

`JsonBriefRenderer.render(brief)` returns UTF-8 JSON of the frozen document, and
`brief_document(brief)` is the pure mapping used by tests and future PDF/HTML renderers:

- `disclaimer{text, model_reference, prompt_version}` is always present (AC 10) and
  `schema_version` names the document contract (`"1.0"`);
- sections are emitted in ordinal order regardless of insertion order, so the document is
  deterministic byte-for-byte;
- citations carry their locator and `resolved` flag; blocked outcomes keep `kind: "blocked"` and
  their blockers; rejected proposals are listed;
- the document validates against `BriefResponse`, which is why the HTTP contract and the renderer
  cannot drift.

## Blocked-outcome honesty (#343)

`TopicOutcome.assert_honest()` refuses any outcome that names a blocker but is stated as
`recommendation` or `open_dispute`: naming a veto and rendering consensus is exactly the smoothing
invariant 8 forbids. `OutcomeHonestyCheck` applies the rule to a whole outcome list, and `publish()`
runs it as the last gate, so a misrendered veto leaves the brief `BLOCKED` and unpublished. The wire
schema keeps `blocked` as a first-class `TopicOutcomeBody.kind`.

## Reproduction (#342)

`ReproductionCheck.assert_reproduces(published, regenerated)` compares the two artefacts section by
section in ordinal order and raises `BriefReproductionMismatch(run_id, section)` at the first
divergence. The fingerprint fixes everything a reader could check — section kind and ordinal,
statement `EvidenceStatus`, `claim_ids`, citation passage ids/resolution/quote and the text of every
`EVIDENCED` statement — while **narrative wording may change** between generations. A missing section
is named too. This is the machine form of invariant 7: the brief is a projection, not a second source
of truth.

## Lineage (#341)

`VersionDecisionBrief.execute` builds version N+1 from N (same run, same snapshot, `previous_version = N`,
mandatory reason), publishes it through the same gates, and in one transaction marks N `SUPERSEDED`,
saves both versions and publishes `DecisionBriefVersioned{brief_id, previous_version, reason}` followed
by the successor's events. N keeps its content and stays retrievable — only its lifecycle moves.
`supersede_by` refuses a draft (`BRIEF_NOT_PUBLISHED`), another run, a version that is not N+1 or a
successor whose `previous_version`/`reason` disagrees (`BRIEF_VERSION_CONFLICT`).

## Immutability (#340)

Publishing is a one-way freeze: after `publish()` succeeds, any attribute assignment raises
`PublishedBriefIsImmutable`, and the section map becomes a `_FrozenSections` mapping whose every
mutator (`__setitem__`, `__delitem__`, `clear`, `pop`, `popitem`, `setdefault`, `update`) raises the
same error. The audit `events` list stays appendable by design — the outbox drains it. A *blocked*
draft is not frozen, so a rejected publication can be fixed and retried; only `published` is final.

## Rejected-proposal disclosure (#337)

`SectionAssembler.assemble` renders every record of `RunProjection.rejected_proposals` inside
section 5 (`compromise_proposals`) as `"<measure> — rejected — blocked by <blockers>: <reasons>"`, and
`SectionAssembler.rejected_proposals(run)` carries the records onto the brief so
`assert_rejected_proposals_disclosed(run_rejected_measures)` can compare. Publication appends one
`RejectedProposalDisclosed{brief_id, measure, blocker_ids}` per disclosed record before
`DecisionBriefPublished`, so a tidy result cannot hide a refusal.

## Citation gate (#336)

`EvidenceCorpusCitationResolver` is the concrete `CitationResolver` adapter: it calls the corpus
`ResolvePassage` use case per passage id and maps `PassageView` → `CitationProvenance` + quote. A
passage the corpus does not know becomes `unresolved` — provenance is never invented. The aggregate
folds the result in with `resolve_citations(resolved)`: references whose passage id was not resolved
stay unresolved, so `publish()` still raises `UnresolvedCitation` and emits
`CitationResolutionFailed`. Resolving on a published brief raises `PublishedBriefIsImmutable`.

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
application = the five use cases; domain = `BriefProjectionBuilder`, `SectionAssembler`,
`ReproductionChecker`, `OutcomeHonestyPolicy`; infrastructure = `CitationResolver`,
`ProvenanceDisclosureGate`; interfaces = `BriefRenderer`.

`SectionAssembler` (#335) is the concrete pure mapping: `assemble(run, consensus)` returns all eight
sections at their frozen ordinals, `outcomes(run, consensus)` returns blocked topics then open
disputes. It performs no I/O and reads no unordered collection, so identical projections produce
identical sections. Statements stay `EVIDENCED` with unresolved `CitationReference`s — resolution is
the citation gate's job — and a verdict without a citable passage is `UNSUPPORTED`, never `EVIDENCED`.

Classification is machine-checked (#334): a test resolves each classified name to the file that
defines it and fails when the declared layer is not the owning layer, when a port is not an
application-layer runtime protocol, or when an infrastructure-classified port has no adapter with a
matching method signature.

Implemented services: `GetDecisionBrief`, `ListBriefVersions` and `ListCitations` read through
`DecisionBriefRepository` (`BriefNotFound` for unknown ids; `BriefNotPublished` before publishing).
`PublishDecisionBrief` remains the stub owned by its publication issue; `VersionDecisionBrief` and
`supersede_by` are implemented (#341).

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

## Runtime integration (#346)

`BriefProjectionAdapter` (infrastructure) is the real `BriefProjectionBuilder`: it runs the pure
`SectionAssembler` and adds only identity and version from the clock/ids ports. It is bound in
`shared/app.py`.

The remaining unbound ports are recorded in `.pi/architecture/DEFERRED.md` **D-007** with owners and
exit criteria: NegotiationSession publishes no question text or corpus snapshot pin, the
consensus-analysis container is not mounted yet, and GovernanceCompliance has no run-level
provenance query. They stay fail-closed (`503 BRIEF_GATE_UNAVAILABLE` / `409 BRIEF_SOURCE_INCOMPLETE`)
rather than being filled with fabricated values.

## Wiring (#345)

1. `shared/app.py` binds `app.state.decision_brief = build_container(...)` and
   `app.include_router(decision_brief_router)`; the routes are in the app's OpenAPI document.
2. `build_container` requires every port as a keyword argument — there is no permissive default.
   Ports the runtime has not bound yet (`history`, `consensus`, `provenance`, `projection`) are
   passed as fail-closed stand-ins (`infrastructure/failclosed.py`) which raise
   `BRIEF_GATE_UNAVAILABLE` (503) on use: publication stops instead of skipping a gate.
3. The citation resolver is already real (`EvidenceCorpusCitationResolver` over
   `corpus.resolve_passage`); the renderer is the frozen `JsonBriefRenderer`.
4. `briefs:publish` is declared per route and enforced by `require_declared_scope`: an analyst key
   gets 403 on both POST routes, `runs:read` covers the three GET routes.
5. Persistence is in-memory until migration `0502_decision_brief` gets its adapter; events are
   logged by `LoggingEventPublisher` until the shared outbox is bound (runtime-integration issue).

`PublishDecisionBrief.execute` now runs the real path: load the closed run, load the derived
consensus, assert the provenance disclosures, build the eight sections, check the rejected-proposal
disclosure, resolve every cited passage, fold the resolutions in, publish through the aggregate
gates, then save and publish the events in one unit of work. A missing run or consensus raises
`BRIEF_SOURCE_INCOMPLETE` (409) rather than projecting a partial artefact.

## Out of bounds (deliberately not frozen)

Internal algorithms, database column names, ORM annotations, PDF rendering, and any shape not
listed above.
