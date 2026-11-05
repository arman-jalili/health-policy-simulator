# ConsensusAnalysis

## Module Status

**Status:** Planned
**Depends:** NegotiationSession (open-host — published session events are the derivation input), StakeholderModel (veto rights and negotiating power)
**Last reviewed:** 2026-11-05
**Source session:** 87433e56-b1a2-4464-a232-2dc4fe6f9dfd

## Description

Derives the negotiation result from the recorded history: consensus, majority and minority
positions, unresolved conflicts, compromise packages and impact assessments. Never invents agreement.

**Modeling Depth:** tactical (core domain)
**Subdomain Rationale:** A negotiation result (not a single answer) is the required output product.
**Context Map:** NegotiationSession → open-host; conformist → DecisionBrief (brief projects consensus records plus history).

## Architecture

| Layer | Responsibility | Path |
|-------|--------------|--------------|
| **Domain** | `ConsensusRecord`, `CompromisePackage`, `Scenario` aggregates; thresholds, estimation basis | `src/consensus_analysis/domain/` |
| **Application** | `DeriveConsensus`, `ComposeCompromisePackage`, `AssessImpact`, `CompareScenarios` | `src/consensus_analysis/application/` |
| **Infrastructure** | SQLAlchemy repositories, event subscribers, projection tables | `src/consensus_analysis/infrastructure/` |
| **Interfaces** | REST routers, `ConsensusView` consumed by DecisionBrief | `src/consensus_analysis/interfaces/` |

**All artefacts here are derived.** They hold no input state; recalculation from the run log must
reproduce them (invariant 1). They exist as persisted projections so the brief can be rendered
without recomputation, not because they are authoritative.

## Related ADRs

| ADR | Relevance |
|---|---|
| ADR-002 Data Storage Strategy | Derived projections in their own schema; rebuildable from the run log |
| ADR-003 Cross-Context Communication | Consumes session events; publishes to DecisionBrief (conformist) |
| ADR-006 Cost Tracking | `AssessImpact` may call an LLM; invocations are metered |
| ADR-008 Proportional Modeling Depth | Tactical: estimation provenance is an invariant |

## Diagrams

### Data Flow

```mermaid
flowchart LR
    E[(Session events<br/>positions, arguments, conflicts)] --> D[DeriveConsensus]
    S[Stakeholder powers<br/>veto rights] --> D
    D --> CR[ConsensusRecord]
    D --> MP[Majority / Minority]
    D --> UC[UnresolvedConflict]
    CR --> CP[ComposeCompromisePackage]
    CP --> PKG[CompromisePackage]
    PKG --> SC[Scenario]
    SC --> AI[AssessImpact<br/>basis + inputs]
    AI --> CMP[CompareScenarios]
    AI --> V[ConsensusView → Brief]
```

### Entity Relationship

```mermaid
classDiagram
    class ConsensusRecord {
        +ConsensusId id
        +TopicRef topic
        +ConsensusThreshold threshold
        +SupportLevel support
        +determine()
        +block_by_veto()
    }
    class MajorityPosition {
        +list supporters
        +Proposal proposal
    }
    class MinorityPosition {
        +list holders
        +list objections
    }
    class CompromisePackage {
        +list components
        +list rejected_proposals
        +compose()
    }
    class Scenario {
        +BaselineRef baseline
        +Horizon horizon
        +list assumptions
    }
    class ImpactAssessment {
        +EstimateBasis basis
        +list derivation_inputs
        +EstimateLimitation limitation
    }
    ConsensusRecord "1" --> "1" MajorityPosition
    ConsensusRecord "1" --> "*" MinorityPosition
    ConsensusRecord "1" --> "0..1" VetoBlockedOutcome
    CompromisePackage "1" --> "*" Scenario : assessed in
    Scenario "1" --> "*" ImpactAssessment : yields
```

### Aggregate State (CompromisePackage)

```mermaid
stateDiagram-v2
    [*] --> Draft
    Draft --> Draft : add_component()
    Draft --> Composed : compose()
    Composed --> Assessed : assess_impact()
    Assessed --> Published : brief projects it
    Draft --> Abandoned : no accepted components
    Abandoned --> [*]
```

### Key Use Case Sequence — DeriveConsensus

```mermaid
sequenceDiagram
    participant Bus as Session event stream
    participant App as DeriveConsensus
    participant Rec as ConsensusRecord
    participant SM as StakeholderModel port
    Bus->>App: SimulationRunClosed / ConflictTopicOpened
    App->>App: replay stances from run log
    App->>SM: veto_classes(stakeholder_ids)
    SM-->>App: veto map
    App->>Rec: determine(topic, threshold, stances)
    alt proposal class is vetoed
        Rec->>Rec: block_by_veto(holder)
        Rec-->>App: ConsensusBlockedByVeto
    else threshold met
        Rec-->>App: ConsensusDetermined
    else below threshold
        Rec-->>App: unresolved + minority recorded
    end
    App->>App: persist projection
```

## Components

### Aggregate root — ConsensusRecord

```python
# src/consensus_analysis/domain/consensus_record.py
@dataclass
class ConsensusRecord:
    id: ConsensusId
    topic: TopicRef
    threshold: ConsensusThreshold
    stances: dict[StakeholderId, StanceSnapshot]
    vetoes: dict[StakeholderId, frozenset[ProposalClass]]
    proposal_class: ProposalClass
    events: list[DomainEvent] = field(default_factory=list)

    def determine(self) -> ConsensusOutcome:
        """Derive the outcome; never assume agreement that the record does not support."""
        self._assert_stances_exist_in_history()
        holders = [sid for sid, clause in self.vetoes.items() if self.proposal_class in clause]
        if holders:
            outcome = VetoBlockedOutcome(self.proposal_class, holders)
            self.events.append(ConsensusBlockedByVeto(self.id, self.topic, holders))
            return ConsensusOutcome.veto_blocked(outcome)

        support = SupportLevel.weighted(self.stances)
        if support.meets(self.threshold):
            self.events.append(ConsensusDetermined(self.id, self.topic, support.value))
            return ConsensusOutcome.consensus(support)

        minority = self._minority_positions()
        if minority:
            self.events.append(MinorityPositionRecorded(self.id, self.topic, len(minority)))
        return ConsensusOutcome.partial(support, minority)

    def _assert_stances_exist_in_history(self) -> None:
        unknown = [s for s in self.stances if not s.recorded]
        if unknown:
            raise StanceNotInHistory(unknown)
```

**Invariants:**

| # | Invariant | Illegal state prevented |
|---|---|---|
| 1 | Derived artefacts hold no input state; recalculation reproduces them; only derivation metadata is authoritative | Derived views drifting into competing sources of truth |
| 2 | A record cites only stances present in the closed run's history | Manufactured agreement |
| 3 | Consensus requires the mandate threshold; below it the outcome is partial or unresolved | Forced consensus |
| 4 | A minority position lists its holders and their arguments | Dissent disappearing from the result |
| 5 | A compromise package combines only individually accepted, mutually compatible components | Unimplementable bundles |
| 6 | Every impact figure declares an `EstimateBasis`; assumed figures are labelled and never presented as computed | LLM guesses published as calculations |
| 7 | A figure marked measured/derived enumerates its inputs; without inputs the basis must be assumed | Unbacked numbers labelled "derived" |
| 8 | Illustrative values from documentation can never appear as run outcomes | A demo figure (22%) reappearing as a result |
| 9 | An impact assessment references exactly one scenario and one package | Orphan headline numbers |
| 10 | A scenario marked feasible names the consenting institutions and confirms no veto | Feasibility asserted against a blocker |
| 11 | Consensus is never declared for a class covered by a bound stakeholder's veto right | Majority rule masquerading as consensus |

**Domain-owned repository:**

```python
# src/consensus_analysis/domain/repositories.py
class ConsensusRepository(Protocol):
    async def get(self, consensus_id: ConsensusId) -> ConsensusRecord | None: ...
    async def save(self, record: ConsensusRecord) -> None: ...
    async def for_run(self, run_id: RunId) -> list[ConsensusRecord]: ...

class StakeholderPowersPort(Protocol):
    async def veto_classes(self, stakeholder_ids: list[StakeholderId]) -> dict[StakeholderId, frozenset[ProposalClass]]: ...
```

### Entities and value objects

| Concept | Kind | Justification |
|---|---|---|
| `ConsensusRecord` | aggregate root | Per-topic outcome with identity and derivation lineage |
| `CompromisePackage` | aggregate root | Independently composed, versioned artefact |
| `Scenario` | aggregate root | Counterfactual with its own lifecycle (defined → assessed → compared) |
| `MajorityPosition` | entity | Immutable snapshot of a carried stance |
| `MinorityPosition` | entity | Immutable dissent record with holders |
| `ImpactAssessment` | entity | Per-scenario estimate with basis and limitations |
| `SupportLevel` | VO | Weighted measure, equal by value |
| `ConsensusThreshold` | VO | Rule parameters from the mandate |
| `EstimateBasis` | VO | measured / derived / modelled / assumed / not_estimated |
| `DerivationInput` | VO | Enumerated input reference (reference figure, passage, tally) |
| `EstimateLimitation` | VO | What the estimate ignores |
| `FeasibilityRating` | VO | Political / legal / administrative rating with basis |
| `UncertaintyLabel` | VO | evidenced / modelled / assumed |
| `ResolvedConflict` / `UnresolvedConflict` | VO | Terminal status with positions that remain apart |
| `VetoBlockedOutcome` | VO | Blocked class + holders |

### Service classification

| Service | Layer | Why |
|---|---|---|
| `DeriveConsensus` | application | Reads history, evaluates rules, persists projection |
| `ComposeCompromisePackage` | application | Transaction boundary for package assembly |
| `AssessImpact` | application | May call an LLM; validates basis before persisting |
| `CompareScenarios` | application | Ranks packages on cost/acceptance/feasibility |
| `ConsensusRule` | domain service | Pure threshold + veto evaluation |
| `EstimateValidator` | domain service | Rejects computed labels without inputs (invariant 6/7) |
| Projection rebuild | infrastructure | Replays run log into projections |

## Domain Events

| Event | Description | Trigger | Payload | Published By |
|---|---|---|---|---|
| `ConsensusDetermined` | Consensus level derived from recorded stances | `DeriveConsensus` | `run_id, topic, support, threshold, supporters[]` | ConsensusAnalysis |
| `ConsensusBlockedByVeto` | Threshold met but a blocking competence applies | `DeriveConsensus` | `run_id, topic, proposal_class, holder_ids[]` | ConsensusAnalysis |
| `MinorityPositionRecorded` | Dissenting stance recorded with holders | `DeriveConsensus` | `run_id, topic, holders[], objection_count` | ConsensusAnalysis |
| `UnresolvedConflictDeclared` | Conflict still open at run close | `DeriveConsensus` | `run_id, topic, positions[]` | ConsensusAnalysis |
| `CompromisePackageComposed` | Accepted components combined with rejected proposals documented | `ComposeCompromisePackage` | `package_id, component_ids[], rejected_count` | ConsensusAnalysis |
| `ScenarioDefined` | Baseline-versus-package scenario defined before any figure | `AssessImpact` | `scenario_id, baseline, horizon, assumption_count` | ConsensusAnalysis |
| `ImpactAssessed` | Impacts estimated for a package with basis and uncertainty | `AssessImpact` | `scenario_id, basis_counts{}, uncertainty` | ConsensusAnalysis |
| `UnbackedEstimateBlocked` | Figure refused for claiming a computed basis without inputs | `AssessImpact` | `scenario_id, field, claimed_basis` | ConsensusAnalysis |
| `FeasibilityRated` | Political/legal/administrative feasibility rated with basis | `AssessImpact` | `package_id, ratings{}, blockers[]` | ConsensusAnalysis |

**ADR-008 triage:** all nine are expert-visible; `ConsensusBlockedByVeto`, `UnbackedEstimateBlocked`
and `MinorityPositionRecorded` are audit-critical (they record refusals and dissent).

## API Endpoints

| Method | Path | Handler | Input | Output | Auth |
|---|---|---|---|---|---|
| POST | `/api/v1/runs/{run_id}/analysis:derive` | `derive_consensus` | `{topics?}` | `[{topic, outcome, support, blockers}]` | `runs:write` |
| GET | `/api/v1/runs/{run_id}/consensus` | `get_consensus` | — | records + majority + minority | `runs:read` |
| GET | `/api/v1/runs/{run_id}/conflicts/open` | `list_unresolved` | — | unresolved conflicts with positions | `runs:read` |
| POST | `/api/v1/runs/{run_id}/packages` | `compose_compromise_package` | `{component_ids[], rejected_ids[]}` | `201 {package_id}` | `runs:write` |
| GET | `/api/v1/runs/{run_id}/packages` | `list_packages` | — | packages with provenance | `runs:read` |
| POST | `/api/v1/packages/{package_id}/scenarios` | `assess_impact` | `{baseline, horizon, assumptions[]}` | `201 {scenario_id, figures[{value,basis,inputs}]}` | `runs:write` |
| GET | `/api/v1/packages/{package_id}/comparison` | `compare_scenarios` | — | ranked alternatives with cost/acceptance/feasibility | `runs:read` |

## Ubiquitous Language

| Term | Definition | Aliases prohibited |
|---|---|---|
| Consensus Record | Derived per-topic outcome statement of agreement level | agreement-summary, result |
| Consensus Threshold | Support level required by the mandate, adjusted for vetoes | quorum, majority-rule |
| Veto-Blocked Outcome | Proposal meeting threshold but not consensus due to a blocking competence | blocked, vetoed |
| Majority Position | Stance carried by most weight-bearing stakeholders | winning-view |
| Minority Position | Dissenting stance with holders and reasons | dissent, objection |
| Compromise Package | Bundle of individually accepted, compatible measures | deal, settlement |
| Rejected Proposal | Measure that did not reach support, documented as not carried | failed-proposal, discarded-option |
| Scenario | Counterfactual: package measures vs baseline, horizon, population, assumptions | case, what-if, variant |
| Impact Assessment | Scenario effect estimate with bias declared | forecast, projection |
| Estimate Basis | Provenance class of a figure: measured/derived/modelled/assumed | confidence, how-computed |
| Derivation Input | Enumerated input behind a derived figure | input, assumption-source |
| Assumed Estimate | Figure without enumerated inputs, publishable only with a label | guess, illustrative-value |
| Feasibility Rating | Political/legal/administrative implementability with basis | implementability, practicality |
| Uncertainty Label | Stated basis of an estimate | confidence, certainty |

## Dependencies

**Depends On:**

| Module | What it provides |
|---|---|
| NegotiationSession | Published events + run log (the only derivation input) |
| StakeholderModel | `veto_classes`, `negotiating_power` per bound stakeholder |
| ClaimValidation | Verified `ReferenceFigure`s usable as derivation inputs |

**Used By:**

| Consumer | What it provides |
|---|---|
| DecisionBrief | `ConsensusView`: consensus, majority, minority, unresolved, packages, impact |

## Implementation Sequence

1. `SupportLevel`, `ConsensusThreshold`, `VetoBlockedOutcome`, `UnresolvedConflict` VOs
2. `ConsensusRecord.determine` with veto precedence + history assertion
3. `DeriveConsensus` projection from the run log + rebuild-from-log test
4. `CompromisePackage` + compatibility rules + rejected-proposal capture
5. `EstimateBasis`, `DerivationInput`, `EstimateLimitation` + `EstimateValidator`
6. `Scenario` + `AssessImpact` (no LLM first: modelled figures only)
7. `FeasibilityRating` + veto-aware feasibility check
8. `CompareScenarios` ranking
9. REST routers + contract tests

## Patterns & OOP Mapping

| Component | Pattern | Rationale |
|---|---|---|
| `ConsensusRule` | **Specification** (`ThresholdMet`, `NotVetoed`, `MajorityHolds`) | Rules combine and are individually testable/reportable |
| Estimation | **Strategy** (`MeasuredEstimator`, `DerivedEstimator`, `ModelledEstimator`, `AssumedEstimator`) | Four real bases with different validation; one interface, honest labels |
| Package assembly | **Composite** | Components accepted individually, composed upward |
| Projection | **Event folding** | Derived state is rebuilt, never hand-edited |
| `EstimateValidator` | **Guard / invariant enforcer** | Blocks the specific failure of an unbacked number |
| Views | **DTO** | `ConsensusView` for the brief |

## Acceptance Criteria

| # | Component | Criterion | Verify In |
|---|---|---|---|
| 1 | Veto precedence | 7/9 support for a vetoed proposal class yields `VetoBlockedOutcome`, never consensus | unit |
| 2 | Threshold | Support below threshold returns partial + minority, not consensus | unit |
| 3 | History assertion | A stance not present in the run log raises `StanceNotInHistory` | unit |
| 4 | Rebibuildability | Rebuilding projections from the run log yields byte-identical records | integration |
| 5 | Unbacked estimate | `basis=derived` with zero inputs raises and emits `UnbackedEstimateBlocked` | unit |
| 6 | Assumed label | An assumed figure persists with the label and cannot be rendered as computed | unit + API |
| 7 | Illustrative-value guard | A figure equal to a documentation example cannot be persisted as an outcome | unit |
| 8 | Minority capture | Every disapproving stakeholder appears in a recorded minority position | unit |
| 9 | Rejected proposals | Every proposal without threshold support appears in `rejected_proposals` | unit |
| 10 | Feasibility veto check | A feasible scenario naming a veto-holding institution as consenting raises | unit |
| 11 | Comparison | Alternative packages are ranked with all three dimensions present | integration |

## Modeling Depth Note (ADR-008)

Tactical depth, but **derived by construction**: this context owns no negotiation state. Its
aggregates exist because consensus, packages and scenarios have their own identity and lifecycle
(a scenario can be re-assessed without touching the run), not because they are sources of truth.
