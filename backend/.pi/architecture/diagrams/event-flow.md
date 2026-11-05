# Domain Event Flow

**Context:** how domain events travel between bounded contexts. Events are facts in the past tense,
persisted through a transactional outbox, and replayed for audit (ADR-003).

## Event flow across contexts

```mermaid
flowchart LR
    subgraph Corpus["EvidenceCorpus"]
        EC1[DocumentIngested]
        EC2[ArticleSegmented]
        EC3[AuthorityTierAssigned]
        EC4[DocumentQuarantined]
        EC5[IndexManifestPublished]
        EC6[PersonalQuotationExcluded]
        EC7[InstitutionalStatementAttributed]
        EC8[DuplicateArticleLinked]
    end

    subgraph Retrieval["EvidenceRetrieval"]
        ER1[EvidencePackAssembled]
        ER2[ContradictingEvidenceSurfaced]
        ER3[EvidenceAbsenceRecorded]
    end

    subgraph Stakeholders["StakeholderModel"]
        SM1[StakeholderRegistered]
        SM2[HistoricalPositionRecorded]
        SM3[MandateSourceCited]
        SM4[AuthorityClaimRejected]
        SM5[MandateViolationDetected]
    end

    subgraph Negotiation["NegotiationSession"]
        NS1[SimulationRunOpened]
        NS2[InitialPositionStated]
        NS3[ArgumentSubmitted]
        NS4[PositionRevised]
        NS5[ConflictTopicOpened]
        NS6[CoalitionFormed]
        NS7[RoundLearningCaptured]
        NS8[SimulationRunClosed]
    end

    subgraph Consensus["ConsensusAnalysis"]
        CA1[ConsensusDetermined]
        CA2[ConsensusBlockedByVeto]
        CA3[MinorityPositionRecorded]
        CA4[CompromisePackageComposed]
        CA5[UnresolvedConflictDeclared]
        CA6[ScenarioDefined]
    end

    subgraph Brief["DecisionBrief"]
        DB1[DecisionBriefPublished]
        DB2[RejectedProposalDisclosed]
        DB3[CitationResolutionFailed]
    end

    subgraph Validation["ClaimValidation"]
        CV1[ClaimVerified]
        CV2[ClaimRejected]
        CV3[UnsupportedAssertionFlagged]
        CV4[ContradictionDetected]
        CV5[ClaimMarkedUnverifiable]
    end

    subgraph Governance["GovernanceCompliance"]
        GC1[GovernanceViolationRecorded]
        GC2[PositionProvenanceDisclosed]
    end

    EC5 --> ER1
    EC6 --> GC1
    ER1 --> NS2
    ER2 --> NS3
    ER3 --> NS3
    SM5 --> NS3
    CV2 --> NS3
    NS3 --> NS4
    NS4 --> NS7
    NS7 --> NS3
    NS5 --> CA1
    NS6 --> CA1
    NS8 --> CA1
    NS8 --> NA1[DerivationRequested]
    CA1 --> DB1
    CA2 --> DB1
    CA3 --> DB1
    CA4 --> DB1
    CA5 --> DB1
    CA6 --> DB1
    DB1 --> DB2
    NS3 --> CV1
    NS3 --> CV3
    GC1 --> NS3
    GC2 --> DB1
```

## Event classes

| Class | Meaning | Examples | Persistence |
|---|---|---|---|
| **Corpus facts** | The archive changed in a way that affects citations | `DocumentIngested`, `IndexManifestPublished`, `PersonalQuotationExcluded` | Outbox + corpus log |
| **Negotiation facts** | Something happened in the room | `InitialPositionStated`, `ArgumentSubmitted`, `PositionRevised`, `CoalitionFormed` | Outbox + append-only run log |
| **Derivation facts** | Analysis was computed from the record | `ConsensusDetermined`, `CompromisePackageComposed`, `ImpactAssessed` | Outbox |
| **Guard facts** | A rule refused or rewrote output | `GovernanceViolationRecorded`, `CitationResolutionFailed` | Outbox + violation table |
| **Metering facts** | A call was made and cost money | `AgentInvocationRecorded`, `RunBudgetExhausted` | Invocation table |

## Delivery guarantees

- **At-least-once.** Handlers are idempotent, keyed on `event_id`.
- **Ordered per aggregate.** Outbox sequence preserves order within an aggregate id.
- **Replayable.** `ReplaySimulationHistory` reads the run log; derived artefacts can be rebuilt.
- **Bounded payloads.** Ids plus minimal data; consumers re-read for detail.

## Explicit non-events (ADR-008 triage)

These exist as logs or return values, **not** as published domain events:
passage indexing writes, score computation, recency weight application, query rewriting,
phase bookkeeping, brief section completion. They fail all three triage questions.

---

*Generated from session: 87433e56-b1a2-4464-a232-2dc4fe6f9dfd · Date: 2026-11-05*
