---
session_id: 87433e56-b1a2-4464-a232-2dc4fe6f9dfd
created: 2026-11-05
business_context: "read all in @.pi/domain/material/ and explore the full domain for backend only, for winning hackathhon"
status: draft
---

# Domain Exploration: 87433e56-b1a2-4464-a232-2dc4fe6f9dfd

> **Status:** draft — AI-suggested, human-review needed.

---

## Business Context

read all in @.pi/domain/material/ and explore the full domain for backend only, for winning hackathhon

---

## Actors & Roles

| Actor | Description | Interactions |
|-------|-------------|-------------|
| Policy Analyst (End User) | Human researcher/decision-maker who poses a policy question and inspects the full reasoning trail. | Creates simulations, configures scenario constraints, starts/pauses runs, streams progress, reads decision brief. |
| Stakeholder Agent | Autonomous institutional representative (social insurance, ministry, chamber, patient rep, etc.) with own interests, budget constraints, priorities and historical positions. | Forms positions, submits arguments, responds to counterarguments, requests evidence, revises positions, forms coalitions. |
| Moderator Agent | Neutral process steward with no position of its own; translates question into a mandate, selects actors, sets rules, detects contradictions, ends negotiation. | Opens/closes rounds, calls for justification, records consensus/conflict, decides stopping conditions. |
| Evidence Curator / Ingestion Operator | Backend role (human or automated) responsible for corpus ingestion quality and source authority classification. | Triggers ingestion, reviews extraction quality, tunes retrieval, curates authoritative reference data. |
| LLM Provider | External probabilistic reasoning provider used by agents and moderator. | Receives prompts with evidence bundles, returns structured argument/position proposals; never authoritative. |
| Scheduler / Background Worker | Executes long-running ingestion and simulation jobs asynchronously. | Consumes queued jobs, emits progress events, retries on failure. |

---

## Functional Requirements

| ID | Requirement | Priority | Bounded Context |
|----|-------------|----------|----------------|
| FR-001 | The system shall ingest the full Austrian press corpus with document-level and article-level provenance (publication, date, page, source URI). | critical | EvidenceCorpus |
| FR-002 | The system shall extract text from PDF/HTML/scanned documents using an OCR fallback and record an extraction quality indicator per document. | critical | EvidenceCorpus |
| FR-003 | The system shall segment documents into articles and articles into citable passages with exact character offsets. | high | EvidenceCorpus |
| FR-004 | The system shall classify each source into an authority tier (press report, institutional statement, legal text, scientific study, official statistics). | critical | EvidenceCorpus |
| FR-005 | The system shall detect duplicate and syndicated articles and link them to a single canonical article. | medium | EvidenceCorpus |
| FR-006 | The system shall retrieve hybrid (BM25 + dense) candidate passages for a claim and rerank them before use. | critical | EvidenceRetrieval |
| FR-007 | The system shall assemble an EvidencePack containing supporting, contradicting and contextual evidence for a claim, never only supporting evidence. | critical | EvidenceRetrieval |
| FR-008 | The system shall score evidence by authority tier, relevance, recency and directness, with every score component individually inspectable. | high | EvidenceRetrieval |
| FR-009 | The system shall weight recent publications more strongly than historical ones via a configurable recency policy. | high | EvidenceRetrieval |
| FR-010 | The system shall maintain a registry of institutional stakeholders with mandate, interests, constraints, budget limits and decision priorities. | critical | StakeholderModel |
| FR-011 | The system shall bind each activated stakeholder to an agent persona derived from its institutional profile and historical positions. | critical | StakeholderModel |
| FR-012 | The system shall create a simulation run from a policy question and a negotiation mandate selecting the relevant stakeholders. | critical | NegotiationSession |
| FR-013 | The system shall run negotiation rounds in which each stakeholder submits an evidenced initial position before debate begins. | critical | NegotiationSession |
| FR-014 | The system shall record every argument with speaker, target, stance (support/oppose/qualify), claims and cited evidence references. | critical | NegotiationSession |
| FR-015 | The system shall allow a stakeholder to revise its position only by recording the reason and referencing the arguments or evidence that caused the change. | critical | NegotiationSession |
| FR-016 | The system shall record conflict topics with per-stakeholder stance and track their resolution status across rounds. | high | NegotiationSession |
| FR-017 | The system shall allow stakeholders to form a coalition on a conflict topic with an explicit shared proposal. | medium | NegotiationSession |
| FR-018 | The system shall terminate a negotiation when a stopping condition fires (consensus threshold, round cap, deadlock) and record which condition fired. | critical | NegotiationSession |
| FR-019 | The system shall derive consensus, majority and minority positions plus unresolved conflicts from the recorded negotiation history. | critical | ConsensusAnalysis |
| FR-020 | The system shall derive compromise packages from accepted cross-stakeholder proposal components. | high | ConsensusAnalysis |
| FR-021 | The system shall present impact assessments per scenario with explicit assumptions and uncertainty labels. | high | ConsensusAnalysis |
| FR-022 | The system shall generate a DecisionBrief containing all eight required components (question, actors, history, conflicts, compromises, consensus, open disputes, impact) with resolvable citations. | critical | DecisionBrief |
| FR-023 | The system shall verify quantitative and legal claims against authoritative sources and reject arguments whose claims contradict verified figures. | critical | ClaimValidation |
| FR-024 | The system shall flag arguments containing unsupported assertions and surface them as low-confidence in the brief. | high | ClaimValidation |
| FR-025 | The system shall reject any agent output that attributes positions to named real persons or quotes individuals. | critical | GovernanceCompliance |
| FR-026 | The system shall disclose, for every position, how it was derived (sources, arguments, model invocation reference). | critical | GovernanceCompliance |
| FR-027 | The system shall execute simulations asynchronously and stream progress events to the client. | critical | SimulationOrchestration |
| FR-028 | The system shall support pausing and resuming a running simulation without losing negotiation state. | medium | SimulationOrchestration |
| FR-029 | The system shall persist prompt template version, model identifier and parameters for every agent invocation. | high | SimulationOrchestration |
| FR-030 | The system shall allow reconstruction of a completed simulation's full event history and re-rendering of its brief. | high | NegotiationSession |

---

## Non-Functional Requirements

| ID | Requirement | Category | Target |
|----|-------------|----------|--------|
| NFR-001 | The system shall provide citation-grade provenance for every evidence reference down to article and passage. | maintainability | 100% of cited evidence resolvable to document + passage offset; 0 orphan citations in validation |
| NFR-002 | The system shall keep domain state authoritative and independent of workflow-engine state. | maintainability | 0 domain invariants enforced inside LangGraph nodes; all state mutation via domain commands |
| NFR-003 | The system shall stream negotiation progress to clients with low latency. | performance | first progress event < 2s after run start; event emitted within 1s of each domain event commit |
| NFR-004 | The system shall retrieve and rerank evidence within an interactive budget. | performance | PROVISIONAL — no target until corpus profiling and a representative run. Record p50/p95 on demo hardware first, then set the budget from measurement. |
| NFR-005 | The system shall ingest the full corpus without manual per-document intervention. | scalability | PROVISIONAL — throughput target set after profiling file types and OCR share. Requirement: ingestion is parallelisable by document and idempotent on re-run. |
| NFR-006 | The system shall protect against prompt injection and data exfiltration via retrieved documents. | security | all retrieved content treated as untrusted data; zero tool invocations initiated from document text |
| NFR-007 | The system shall enforce the institution-only representation rule at output boundaries. | security | 100% of person-level or person-quoting outputs rejected pre-persistence; 0 such statements in generated briefs |
| NFR-008 | The system shall recover from worker or agent failures without corrupting negotiation state. | availability | run resumable after crash; no partial argument persisted; at-least-once delivery with idempotent domain commands |
| NFR-009 | The system shall document the reproducibility limits of probabilistic agent output. | maintainability | every run records model + prompt versions and seed; brief explicitly states non-determinism |
| NFR-010 | The system shall bound LLM cost and latency per simulation. | performance | PROVISIONAL — a hard cost ceiling per run is required; the concrete number is set after one measured 9-stakeholder run. |
| NFR-011 | The system shall make every generated argument reproducible to its inputs. | maintainability | each argument stores prompt version, model, evidence pack id and round; 100% traceable |
| NFR-012 | The system shall enforce institutional-only agent identities. | security | agent identity bound to an institutional Stakeholder id; 0 agents addressable by personal name |
| NFR-013 | The system shall isolate concurrent simulation runs. | scalability | Isolation is mandatory (no cross-run state). Concurrency count is PROVISIONAL until measured; demo must support at least two concurrent runs. |
| NFR-014 | The system shall keep agent latency acceptable during streaming rounds. | performance | p95 single agent turn < 20s with streaming partial argument tokens |
| NFR-015 | The system shall degrade gracefully when the LLM provider fails. | availability | bounded retries with exponential backoff; run marked paused with diagnosable failure, never partially committed argument |
| NFR-016 | The system shall protect the security of stored simulation and corpus data. | security | secrets never persisted in domain events; least-privilege DB roles; encrypted transport for all provider calls |
| NFR-017 | The system shall keep the API contract stable for the frontend during the hackathon. | maintainability | OpenAPI schema published and versioned; contract tests green on every build |
| NFR-018 | The system shall test domain invariants with automated coverage. | maintainability | >= 80% line coverage on domain layer; every aggregate invariant has at least one rejecting test |
| NFR-019 | The system shall evaluate retrieval quality measurably. | performance | A manually labelled evaluation set of claims with known supporting and contradicting passages is required before any recall figure is set. No arbitrary recall threshold shall be specified in advance. |
| NFR-020 | The system shall keep a full audit trail of state changes. | maintainability | every aggregate transition emits a persisted domain event; history reconstructable to any round |
| NFR-021 | The system shall bound and document ingestion failure rates. | availability | Every failed document is persisted with a reason and is retryable. The admissible failure rate is set after corpus profiling, not assumed. |
| NFR-022 | The system shall keep the corpus index fresh relative to ingestion. | performance | PROVISIONAL — a newly ingested document becomes searchable once its IndexManifest version is published; the latency bound is set after measuring index build cost. |
| NFR-023 | The system shall operate within hackathon cost constraints. | scalability | full demo simulation (9 agents, 6 rounds) within a configured per-run token budget |
| NFR-024 | The system shall authenticate and authorise API access. | security | all mutating endpoints require an authenticated principal; role checks enforced per route; 0 unauthenticated state changes |
| NFR-025 | The system shall expose API contracts covering all documented use cases. | maintainability | >= 95% endpoint coverage of the FR catalogue; every endpoint has request/response schema and contract test |

---

## Assumptions

| Assumption | Impact if Wrong | Mitigation |
|------------|----------------|-----------|
| The ~3GB 2020 press corpus is German-language, PDF/HTML mixed, with usable publication metadata. | Extraction and provenance model must change; citation quality drops. | Profile corpus first; build adapter per source format; degrade gracefully to document-level provenance. |
| Press reports reliably reveal institutional positions but are not ground truth on facts. | Agents would over-claim factual accuracy. | Model source authority tiering; require authoritative sources for quantitative claims. |
| Hackathon scope: one policy question per simulation, deterministic negotiation rules, LLM for content only. | Scope creep into multi-question/multi-run comparison. | Freeze MVP scope; design extension points explicitly. |
| LLM outputs are nondeterministic, so reproducibility is bounded by recorded prompt/model/seed metadata. | Claims of deterministic outcomes would be false. | Persist full event log + prompt/model versions; document reproducibility limits. |
| PostgreSQL + Qdrant are sufficient; no message broker beyond a single worker queue is needed. | Scaling issues on large corpus ingestion. | Keep ingestion idempotent and parallelizable by document. |

---

## Bounded Contexts

| Context | Description | Entities |
|---------|-------------|----------|
| EvidenceCorpus | Owns the authoritative document corpus: ingestion, extraction, article segmentation, passage chunking and citation-grade provenance. Publishes passages as an open host for retrieval. | Document,Publication,Article,Passage,CorpusCollection |
| EvidenceRetrieval | Turns a claim into a balanced, scored, inspectable evidence pack. Owns hybrid search, reranking, stance classification and recency weighting. Never owns the corpus itself. | RetrievalQuery,EvidenceCandidate,EvidencePack,AuthorityWeight |
| StakeholderModel | Owns institutional identity: who the stakeholder is, what it wants, what limits it, and how that becomes a negotiating agent persona. Guarantees institutions only, never persons. | Stakeholder,StakeholderProfile,Interest,Constraint,HistoricalPosition,AgentBinding |
| NegotiationSession | The heart of the domain: a policy question becomes a mandate, stakeholders take turns, argue with evidence, revise positions, form coalitions and the run closes under an explicit stopping condition. | SimulationRun,NegotiationMandate,NegotiationRound,Argument,Position,Coalition,ConflictTopic |
| ConsensusAnalysis | Derives the negotiation result from the recorded history: consensus, majority and minority positions, unresolved conflicts, compromise packages and impact assessments. Never invents agreement. | ConsensusRecord,MajorityPosition,MinorityPosition,CompromisePackage,ImpactAssessment |
| DecisionBrief | Projects a closed run into the publishable, jury-facing artefact with all eight required components and resolvable citations. Read-model of the negotiation, never a source of truth. | DecisionBrief,BriefSection,CitationReference |
| SimulationOrchestration | Agent workflow graph execution (LangGraph), progress streaming, job lifecycle, pause/resume; orchestrates but does not own state. | SimulationJob,WorkflowGraph,ProgressEvent,AgentInvocation |
| ClaimValidation | Keeps figures honest: extracts claims from arguments, verifies them against authoritative sources, detects contradictions between agents and flags unsupported assertions. | Claim,ClaimVerification,ContradictionFinding |
| GovernanceCompliance | Rules that institutions only are represented (never real persons), no quoting of real individuals, and transparency of position derivation. | InstitutionOnlyRule,ProhibitedPersonReference,ProvenanceDisclosure |
| IdentityAccess | Authentication, workspace access, roles (analyst, operator, admin). | User,Workspace,Role |

---

## Entities

| Entity | Context | Type | Description |
|--------|---------|------|-------------|
| Document | EvidenceCorpus | aggregate-root | A physical source file (PDF, HTML, scanned page bundle) with source URI, publication, hash, extraction quality and authority tier. |
| Publication | EvidenceCorpus | entity | The publishing outlet issue/edition: outlet name, issue date, medium type, authority tier default. |
| Article | EvidenceCorpus | entity | A segmented editorial unit inside a Document: headline, dateline, full text, page range, canonical link for syndication. |
| Passage | EvidenceCorpus | entity | A citable contiguous text span of an Article with exact character offsets, the unit indexed and retrieved. |
| AuthorityTier | EvidenceCorpus | value-object | Ranked credibility rubric owned by the corpus: official-statistics, legislation, scientific-study, institutional-statement, press-report, other. Published as published language so retrieval consumes it instead of redefining trust. |
| Provenance | EvidenceCorpus | value-object | Immutable locator bundle: document id, article id, page number, character offset, source URI, retrieval timestamp. |
| ExtractionQuality | EvidenceCorpus | value-object | Measured extraction health: method (native/ocr), confidence, missing-glyph rate, acceptance flag. |
| CorpusCollection | EvidenceCorpus | entity | A named, versioned manifest of which documents and index version a run searched. A manifest, not a transactional aggregate over the whole corpus — it references documents, it does not contain them. |
| RetrievalQuery | EvidenceRetrieval | value-object | Normalised search intent derived from a claim: claim text, entity and time filters, corpus snapshot. Not an aggregate — it is an input to an application operation, and the trace that matters is RetrievalTrace on the pack. |
| EvidenceCandidate | EvidenceRetrieval | entity | A retrieved Passage with stance label (supporting/contradicting/contextual), authority tier and component scores. |
| EvidencePack | EvidenceRetrieval | aggregate-root | The frozen, balanced bundle of candidates handed to an agent as justification for one claim. |
| EvidenceScore | EvidenceRetrieval | value-object | Inspectable weighting: authority weight, lexical score, semantic similarity, recency weight, directness, final rank. |
| StanceLabel | EvidenceRetrieval | value-object | Classification of a candidate relative to the claim: supporting, contradicting, contextual, tangential. |
| RecencyPolicy | EvidenceRetrieval | value-object | Configurable decay function, reference date and minimum weight that operationalises 'current events outweigh history'. |
| CoverageReport | EvidenceRetrieval | value-object | Measured evidence availability for a claim: candidate counts per stance, best authority found, gap flag. |
| Stakeholder | StakeholderModel | aggregate-root | An institution participating in Austrian healthcare policy (social insurance, ministry, chamber, patient representation, hospital association). |
| StakeholderProfile | StakeholderModel | entity | The negotiating character of a Stakeholder: mandate, interests, constraints, budget limits, decision priorities and red lines. |
| Interest | StakeholderModel | value-object | A stated goal the stakeholder optimises for, with weight and the policy topics it applies to. |
| Constraint | StakeholderModel | value-object | A hard limit (budget ceiling, legal competence, political feasibility) that a stakeholder cannot concede. |
| BudgetLimit | StakeholderModel | value-object | Numeric spending envelope with period and tolerance used to reject unacceptable proposals. |
| DecisionPriority | StakeholderModel | value-object | Ordered ranking the stakeholder applies when interests conflict. |
| HistoricalPosition | StakeholderModel | entity | A documented past stance of the institution, derived from press/institutional sources with provenance and date. |
| AgentBinding | StakeholderModel | aggregate-root | The immutable binding of a StakeholderProfile to an agent persona used in one simulation run, including persona rules and allowed evidence. |
| InstitutionIdentity | StakeholderModel | value-object | Canonical institutional name, category and short code used in all identifiers and outputs. |
| SimulationRun | NegotiationSession | aggregate-root | One simulation of one policy question: pinned corpus snapshot, bound stakeholders, phase state machine, round cap and outcome. |
| NegotiationMandate | NegotiationSession | entity | The moderator-issued framing of the question: objective, constraints, selected stakeholders, rules and stopping conditions. |
| NegotiationRound | NegotiationSession | entity | A numbered turn cycle with per-stakeholder turns, closed by the moderator and scored for convergence. |
| Position | NegotiationSession | entity | A stakeholder's stance on a conflict topic: proposal, claims, evidence refs, confidence and revision lineage. |
| Argument | NegotiationSession | entity | A single turn's contribution: speaker, target, stance, claims, citations and a reference to the producing agent invocation. |
| ArgumentStance | NegotiationSession | value-object | Whether the argument supports, opposes, qualifies or conditionally accepts the target. |
| ConflictTopic | NegotiationSession | entity | An identified point of institutional disagreement with per-stakeholder stance history and resolution status. |
| Coalition | NegotiationSession | entity | A set of stakeholders on a conflict topic behind one explicit shared proposal, with a formed round and reasons. |
| RevisionReason | NegotiationSession | value-object | Structured justification of a position change: cited argument ids, evidence ids and stated driver. |
| StoppingCondition | NegotiationSession | value-object | The rule that ended the run: consensus threshold met, round cap reached, or deadlock declared. |
| ConsensusRecord | ConsensusAnalysis | aggregate-root | Per-conflict-topic outcome: consensus level, supporting and opposing stakeholders, threshold met or not. |
| MajorityPosition | ConsensusAnalysis | entity | The stance carried by the majority of weight-bearing stakeholders on a topic, with vote-like support listing. |
| MinorityPosition | ConsensusAnalysis | entity | A dissenting stance with its holders, arguments and unresolved objections. |
| CompromisePackage | ConsensusAnalysis | aggregate-root | A bundle of accepted cross-stakeholder proposal components with provenance and the rejected proposals list. |
| ImpactAssessment | ConsensusAnalysis | entity | Scenario effect estimates per package (e.g. waiting-time reduction, budget delta) with assumptions and uncertainty. |
| SupportLevel | ConsensusAnalysis | value-object | Weighted measure of support for a proposal across stakeholders, derived from interests and stances. |
| UncertaintyLabel | ConsensusAnalysis | value-object | Explicit statement of confidence basis for an estimate: evidenced, modelled, or assumed. |
| UnresolvedConflict | ConsensusAnalysis | value-object | A conflict topic still open at run close, with the positions that remain apart. |
| DecisionBrief | DecisionBrief | aggregate-root | A versioned, immutably persisted projection of one closed run. It is generated — it holds no input state of its own — but once published it is a first-class artefact with its own identity, version lineage and citation integrity. |
| BriefSection | DecisionBrief | entity | One of the eight required components with ordering, content and the entities it projects. |
| CitationReference | DecisionBrief | entity | A resolvable pointer from a brief statement to a Passage provenance with surrounding context. |
| ActorSummary | DecisionBrief | value-object | Institution, goals, constraints and positions adopted, as shown in the actors section. |
| PositionTimeline | DecisionBrief | value-object | Per-stakeholder stance trajectory across rounds, used for the position-change visualisation. |
| BriefVersion | DecisionBrief | value-object | Version marker linking a brief to the run id, corpus snapshot and generation timestamp. |
| Claim | ClaimValidation | aggregate-root | An extracted assertion from an argument: text, type (quantitative, legal, causal, qualitative), measure, value, period, geography. |
| ClaimVerification | ClaimValidation | entity | The verdict for a claim: supported, contradicted, unsupported, or ambiguous, with the source set and method. |
| ContradictionFinding | ClaimValidation | entity | A detected conflict between two verified claims or between a claim and an authoritative figure, with both provenances. |
| ClaimType | ClaimValidation | value-object | Classification driving the required verification path: quantitative, legal, causal, qualitative. |
| VerificationVerdict | ClaimValidation | value-object | Enumerated outcome with confidence basis: supported, contradicted, unsupported, ambiguous. |
| MeasureReference | ClaimValidation | value-object | Normalised identity of a measurable quantity: measure name, unit, reference period, geography, population. |
| ArticleSection | EvidenceCorpus | value-object | Typed region of an Article: headline, standfirst, body, caption or quotation block. Drives directness scoring and quotation screening. |
| QuotationBlock | EvidenceCorpus | value-object | A span of quoted or reported speech with speaker attribution; structurally retained but never promoted as evidence because the challenge forbids quoting real persons. |
| LanguageTag | EvidenceCorpus | value-object | Language variant marker (de-AT, de-DE) governing tokenisation, compound-word handling and embedding model choice for German-language retrieval. |
| CanonicalArticleRef | EvidenceCorpus | value-object | Pointer from a syndicated duplicate to the canonical article that owns the citable passages, preventing duplicate coverage from inflating support. |
| IngestionRun | EvidenceCorpus | aggregate-root | One batch ingestion execution over a shard of source files: documents attempted, accepted, quarantined, failed, with retry lineage and a terminal status. Makes corpus growth auditable and re-runs idempotent. |
| IndexManifest | EvidenceCorpus | entity | Published index state for a corpus snapshot: indexed passages, embedding model, index version, searchable-since. Belongs to the corpus collection rather than being a second aggregate over the same material. |
| AuthorityWeight | EvidenceRetrieval | value-object | Numeric weight looked up from the corpus-owned AuthorityTier rubric. Keeps the rubric owned by EvidenceCorpus while retrieval only consumes it. |
| RetrievalTrace | EvidenceRetrieval | entity | Reproducibility record attached to each pack: index manifest version, embedding and reranker model ids, query rewrite applied, candidate counts per stance. |
| QueryRewrite | EvidenceRetrieval | value-object | Deterministic expansion applied to a German-language claim before search: compound splitting, umlaut folding, institutional synonym mapping. |
| NegotiatingPower | StakeholderModel | value-object | Derived leverage of an institution: mandate scope, budget authority, veto rights and coalition centrality. Drives game-theoretic reasoning instead of opinion averaging. |
| VetoRight | StakeholderModel | value-object | The class of proposals an institution can block outright (e.g. statutory benefit changes without insurer consent). A hard constraint on what consensus is reachable. |
| Dependency | StakeholderModel | value-object | Directional relation between two institutions — funding, approval, staffing, data provision — with strength and the proposal classes it affects. |
| MandateScope | StakeholderModel | value-object | The legally and institutionally admissible range of what the stakeholder may agree to; bounds every concession an agent can make. |
| TurnAssignment | NegotiationSession | value-object | A stakeholder's allocated floor in a round: position in turn order, the conflict topic, and whether the turn was used, passed or abstained. |
| NegotiationPhase | NegotiationSession | value-object | Monotonic process stage: position-formation, debate, negotiation, compromise, closure. Guards which commands are legal at a given moment. |
| Proposal | NegotiationSession | value-object | The structured substance of a position: measure, quantified effect with unit, target population, cost and affected stakeholders — what makes two positions machine-comparable. |
| ProposalComponent | NegotiationSession | value-object | One admissible part of a proposal (e.g. 'expand telemedicine for dermatology') carrying its own support record so packages can be assembled from accepted parts. |
| CoalitionOffer | NegotiationSession | entity | A recorded invitation to join a shared proposal on a conflict topic, with the invited stakeholder, conditions, and accept/decline outcome. |
| Scenario | ConsensusAnalysis | aggregate-root | A counterfactual being assessed: baseline versus the measures of one CompromisePackage, its horizon, affected population and stated assumptions. Impact only means something relative to a scenario. |
| FeasibilityRating | ConsensusAnalysis | value-object | Rated political, legal and administrative feasibility of a package with the basis for each rating; the third dimension the material demands alongside cost and acceptance. |
| ConsensusThreshold | ConsensusAnalysis | value-object | The support level the mandate requires for consensus, together with how veto rights alter the effective bar. |
| VetoBlockedOutcome | ConsensusAnalysis | value-object | Record of a proposal that met the support threshold but is not consensus because a bound stakeholder holds a blocking competence over its class. |
| CitedStatement | DecisionBrief | value-object | The atomic unit of the brief: one statement with its citation references, the claim ids it rests on, and whether it is evidenced, narrative or unsupported. Makes 'which claim does this sentence rest on' answerable per sentence. |
| RejectedProposalRecord | DecisionBrief | entity | A measure that failed to gather support, with the stakeholders who blocked it and their stated reasons. The material explicitly requires 'proposals not implemented' as an output component. |
| SimulationDisclaimer | DecisionBrief | value-object | Statement of what the result is and is not: probabilistic agent reasoning over a pinned corpus, no determinism claim, no real-person positions. |
| BriefComponentSlot | DecisionBrief | value-object | Position of one mandated component among the eight, with its completion state; the structural guarantee that no component can be silently dropped. |
| ReferenceFigure | ClaimValidation | entity | The canonical value of one MeasureReference taken from an authoritative source, with its as-of date and source tier. The baseline against which every agent claim in that measure is compared. |
| ToleranceBand | ClaimValidation | value-object | Admissible numeric deviation for a measure (rounding, revision, estimate spread) below which two figures are treated as equal. |
| ExpertReview | ClaimValidation | entity | Escalation record for claims the deterministic checks cannot settle: the question asked, the evidence supplied, the verdict and its basis. The feedback loop the material requires for figures. |
| RoundLearning | NegotiationSession | entity | Persisted digest of what one round taught the participants: arguments that withstood challenge, proposals that gained or lost support, coalitions formed, evidence that changed minds, and the position shifts it caused. This is the state the challenge requires so agents take partial results into subsequent rounds. |
| LearningApplication | NegotiationSession | value-object | Explicit link from a later argument or position revision to the RoundLearning insight it applies, with the insight type (evidence accepted, alliance shift, proposal weakened). |
| LearningInsightType | NegotiationSession | value-object | What kind of lesson was carried forward: challenger evidence accepted, own claim abandoned, coalition partner shifted, proposal support strengthened or weakened. |
| MandateSource | StakeholderModel | value-object | The authoritative instrument grounding a power claim: legal provision, statutory instrument, budget decision or institutional statute, with citation and as-of date. The source of truth the review demanded for veto rights, competences and budget authority. |
| AttributionStrength | StakeholderModel | value-object | How firmly a source attributes a stance to the institution: explicit attributed statement, reported institutional position, or mere mention. Governs whether a HistoricalPosition may be used. |
| PowerSourceKind | StakeholderModel | value-object | Classification of where an authority derives from: legislation, statutory instrument, budget decision, institutional statute, or negotiated agreement. |
| EstimateBasis | ConsensusAnalysis | value-object | Provenance class of a quantitative estimate: measured, derived from authoritative figures, modelled by a stated method, assumed, or not estimated. The distinction the review demanded between evidence-backed calculation and LLM assumption. |
| DerivationInput | ConsensusAnalysis | value-object | One enumerated input behind a derived figure: a ReferenceFigure id, a passage id, or a run-internal tally such as a stakeholder cost sum. |
| EstimateLimitation | ConsensusAnalysis | value-object | Stated limitation of an estimate: what it ignores, what it assumes constant, and which population or period it does not cover. |
| AbsenceFinding | EvidenceRetrieval | value-object | Recorded negative result for a stance: the queries issued, the corpus snapshot searched and the reason nothing met threshold. Turns 'no contradiction found' into an auditable fact rather than an omission or a blocker. |
| SpeakerKind | EvidenceCorpus | value-object | Who a statement is attributed to: institution, named person, anonymous source or unattributed. Decides whether a QuotationBlock is citable (institutional) or excluded (personal). |
| AuthorityRule | EvidenceCorpus | value-object | Claim-type-specific ordering of source types, replacing a single global authority scale. Legal questions rank legislation first, quantitative ones official statistics, causal ones studies. |
| VerificationPath | ClaimValidation | value-object | The route a claim type must take: quantitative to reference comparison, legal to provision check, causal to study appraisal, qualitative to no-verification. Makes the differentiated handling explicit instead of one universal check. |
| CausalSupport | ClaimValidation | value-object | Appraisal of study evidence for a causal claim: study design, population, effect direction and whether it supports, contests or fails to address the claim. |

---

## Domain Events

| Event | Context | Description | Triggered By |
|-------|---------|-------------|-------------|
| DocumentIngested | EvidenceCorpus | A source file was registered, extracted and quality-assessed. | IngestDocument |
| DocumentExtractionFailed | EvidenceCorpus | Extraction could not reach the acceptance threshold; document excluded from citation. | IngestDocument |
| ArticleSegmented | EvidenceCorpus | Article boundaries and publication metadata were resolved for a document. | SegmentArticle |
| AuthorityTierAssigned | EvidenceCorpus | A source was classified into an authority tier used for evidence weighting. | ClassifySourceAuthority |
| DuplicateArticleLinked | EvidenceCorpus | A syndicated copy was linked to a canonical article so citations collapse correctly and duplicate reporting does not inflate evidence support. | ClassifySourceAuthority |
| EvidencePackAssembled | EvidenceRetrieval | A balanced, scored evidence pack was frozen for a claim. | AssembleEvidencePack |
| ContradictingEvidenceSurfaced | EvidenceRetrieval | Evidence opposing the requesting stakeholder's position was found and included in the pack. | AssembleEvidencePack |
| StakeholderRegistered | StakeholderModel | A new institutional stakeholder entered the registry with mandate and profile. | RegisterStakeholder |
| StakeholderProfileUpdated | StakeholderModel | Interests, constraints or priorities changed; affects all future runs but not running ones. | RegisterStakeholder |
| AgentPersonaBound | StakeholderModel | A stakeholder was bound to an agent persona for a specific run. | BindAgentPersona |
| HistoricalPositionRecorded | StakeholderModel | A past institutional stance was extracted and stored with provenance. | BindAgentPersona |
| MandateViolationDetected | StakeholderModel | A proposed concession exceeded the stakeholder's declared constraints or budget limits. | BindAgentPersona |
| SimulationRunOpened | NegotiationSession | A run was created from a mandate with pinned corpus and stakeholders. | OpenSimulationRun |
| RoundOpened | NegotiationSession | A new negotiation round started with its turn order. | TakeNegotiationTurn |
| InitialPositionStated | NegotiationSession | A stakeholder opened its evidenced starting position. | SubmitInitialPosition |
| ArgumentSubmitted | NegotiationSession | A stakeholder contributed an argument with stance, claims and citations. | TakeNegotiationTurn |
| PositionRevised | NegotiationSession | A stakeholder changed its position with a recorded reason and evidence. | RevisePosition |
| PositionRevisionRejected | NegotiationSession | A position change was refused because no causal reason or evidence reference was supplied. | RevisePosition |
| ConflictTopicOpened | NegotiationSession | Divergence between stakeholders was formalised as a tracked conflict. | TrackConflictTopic |
| CoalitionFormed | NegotiationSession | Several stakeholders aligned behind one shared proposal on a conflict topic. | FormCoalition |
| RoundClosed | NegotiationSession | All turns for the round completed; convergence measured. | TakeNegotiationTurn |
| SimulationRunClosed | NegotiationSession | The run terminated because a stopping condition fired. | EvaluateStoppingCondition |
| ConsensusDetermined | ConsensusAnalysis | Consensus level for a conflict topic was derived from recorded stances. | DeriveConsensus |
| MinorityPositionRecorded | ConsensusAnalysis | A dissenting stance was recorded with holders and reasons. | DeriveConsensus |
| CompromisePackageComposed | ConsensusAnalysis | Accepted components were combined into a package with rejected proposals documented. | ComposeCompromisePackage |
| ImpactAssessed | ConsensusAnalysis | Scenario impacts were estimated for a package with stated assumptions and uncertainty. | AssessImpact |
| UnresolvedConflictDeclared | ConsensusAnalysis | A conflict remained open at run close and was carried into the brief. | DeriveConsensus |
| DecisionBriefPublished | DecisionBrief | A complete, citation-resolved brief was published for a closed run. | PublishDecisionBrief |
| CitationResolutionFailed | DecisionBrief | A citation could not be resolved to a passage provenance; publication blocked. | PublishDecisionBrief |
| DecisionBriefVersioned | DecisionBrief | A new brief version was produced from the same run. | PublishDecisionBrief |
| ClaimExtracted | ClaimValidation | A verifiable assertion was extracted from an argument. | VerifyClaim |
| ClaimVerified | ClaimValidation | A claim was confirmed against an authoritative source. | VerifyClaim |
| ClaimRejected | ClaimValidation | A claim was contradicted by authoritative evidence; the argument may not stand on it. | VerifyClaim |
| UnsupportedAssertionFlagged | ClaimValidation | A claim had no adequate evidence and was flagged low-confidence. | FlagUnsupportedAssertion |
| ContradictionDetected | ClaimValidation | Two claims or a claim and an authoritative figure were found incompatible. | VerifyClaim |
| QuotationBlockDetected | EvidenceCorpus | A passage region was classified as quoted or reported speech of a person and flagged as non-promotable evidence. | SegmentArticle |
| DocumentQuarantined | EvidenceCorpus | A document failed the extraction quality gate and was excluded from the citable corpus while remaining retrievable for diagnostics. | ExtractDocumentText |
| IngestionRunCompleted | EvidenceCorpus | A batch ingestion finished with accepted, quarantined and failed counts recorded against the run. | IngestDocument |
| IndexManifestPublished | EvidenceCorpus | A new index version became searchable for a corpus snapshot, making previously ingested passages citable. | IndexIngestedPassages |
| PassageRevertedFromIndex | EvidenceCorpus | A passage was removed from the live index because its document was retracted or found unusable, so no future argument can cite it. | IndexIngestedPassages |
| NegotiatingPowerChanged | StakeholderModel | An institution's derived leverage changed because its mandate scope, budget authority or veto rights changed, altering which coalitions are viable. | RegisterStakeholder |
| VetoRightRegistered | StakeholderModel | An institution's power to block a class of proposals was declared, making majority-only consensus insufficient. | RegisterStakeholder |
| DependencyRecorded | StakeholderModel | A directional dependency between two institutions was registered, enabling coalition and blockade analysis. | RegisterStakeholder |
| NegotiationPhaseAdvanced | NegotiationSession | The run entered the next process phase, changing which commands are admissible and which UI stage is shown. | EvaluateStoppingCondition |
| CoalitionOffered | NegotiationSession | A stakeholder invited another institution to join a shared proposal with stated conditions. | FormCoalition |
| CoalitionOfferDeclined | NegotiationSession | An invited institution refused a coalition on a conflict topic, with its stated reason. | FormCoalition |
| ScenarioDefined | ConsensusAnalysis | A baseline-versus-package scenario was defined with horizon, population and assumptions before any impact figure was produced. | AssessImpact |
| ConsensusBlockedByVeto | ConsensusAnalysis | A proposal reached the support threshold but cannot be recorded as consensus because an institution holds a blocking competence over its class. | DeriveConsensus |
| FeasibilityRated | ConsensusAnalysis | Political, legal and administrative feasibility of a package was rated with its stated basis. | AssessImpact |
| RejectedProposalDisclosed | DecisionBrief | A proposal that failed to gather support was disclosed in the brief with its blockers and reasons. | PublishDecisionBrief |
| BriefBlockedByMissingDisclosure | DecisionBrief | Publication was refused because a required disclosure (rejected proposal, unsupported statement or disclaimer) was absent. | PublishDecisionBrief |
| ReferenceFigureRegistered | ClaimValidation | A canonical authoritative value was registered for a measure, establishing the comparison baseline for future claims. | ResolveMeasureIdentity |
| ClaimEscalatedForReview | ClaimValidation | A claim the deterministic checks could not settle was escalated to expert review and left unverified meanwhile. | VerifyClaim |
| ExpertReviewResolved | ClaimValidation | An escalated claim received a verdict with its basis, settling or confirming its uncertainty. | VerifyClaim |
| RoundLearningCaptured | NegotiationSession | The outcome of a round was distilled into a persisted learning record consumed by every bound stakeholder in the next round. | TakeNegotiationTurn |
| LearningApplied | NegotiationSession | A stakeholder explicitly applied a captured insight, adapting its argument or position because of what happened earlier in this negotiation. | RevisePosition |
| MandateSourceCited | StakeholderModel | An authority claim was grounded in a citable instrument, making the stakeholder's power auditable rather than asserted. | RegisterStakeholder |
| AuthorityClaimRejected | StakeholderModel | A veto right, competence or budget limit was refused because no admissible mandate source backed it. | RegisterStakeholder |
| WeakAttributionFlagged | StakeholderModel | A historical position was stored with weak or indirect attribution and marked unusable for overriding current statements. | RecordHistoricalPosition |
| UnbackedEstimateBlocked | ConsensusAnalysis | An impact figure was refused because it declared a computed basis without enumerable inputs. | AssessImpact |
| EvidenceAbsenceRecorded | EvidenceRetrieval | A stance produced no qualifying evidence and the absence was recorded together with the searches that failed to find any. | AssembleEvidencePack |
| PersonalQuotationExcluded | EvidenceCorpus | A quotation attributed to a natural person was marked non-citable so it can never reach an agent's evidence pack. | SegmentArticle |
| InstitutionalStatementAttributed | EvidenceCorpus | A statement attributed to an institution (not a person) was retained as citable evidence of that institution's position. | SegmentArticle |
| ClaimMarkedUnverifiable | ClaimValidation | A claim could not be verified by any applicable path and was recorded as explicitly ambiguous instead of being dropped. | VerifyClaim |
| CausalClaimAppraised | ClaimValidation | A causal claim was appraised against study evidence and recorded as supported, contested or unaddressed, never as verified fact. | VerifyClaim |

---

## Ubiquitous Language

| Term | Definition | Bounded Context | Aliases/Synonyms |
|------|-----------|----------------|-----------------|
| Document | A physical ingested source file before editorial segmentation. | EvidenceCorpus | file,pdf,source file |
| Article | One editorial unit segmented out of a Document, carrying headline, date and page. | EvidenceCorpus | news item,story,post |
| Passage | The smallest citable text span; the unit that is indexed, retrieved and cited. | EvidenceCorpus | chunk,snippet,fragment |
| Authority Tier | Ranked credibility rubric owned by the corpus, published to consumers; retrieval never defines trust itself. | EvidenceCorpus | trust level,credibility,source rank |
| Extraction Quality | Measured confidence that a Document's text faithfully represents the physical source. | EvidenceCorpus | ocr confidence,parse quality |
| Provenance | Immutable locator bundle that lets any citation be resolved to a page and offset. | EvidenceCorpus | citation locator,source pointer |
| Corpus Snapshot | The versioned document set a simulation run searched, frozen at run start. | EvidenceCorpus | dataset version,index version |
| Evidence Pack | Frozen, balanced and scored set of supporting, contradicting and contextual evidence for one claim. | EvidenceRetrieval | context bundle,rag result,hits |
| Stance Label | Whether a passage supports, contradicts, contextualises or is tangential to a claim. | EvidenceRetrieval | polarity,sentiment |
| Recency Policy | Configured decay that weights newer publications above older ones. | EvidenceRetrieval | decay,freshness boost |
| Evidence Score | Inspectable multi-component weighting including authority, relevance, recency and directness. | EvidenceRetrieval | confidence,relevance score |
| Evidence Gap | State where a claim has no evidence above threshold, forcing an unsupported flag rather than an invented citation. | EvidenceRetrieval | no results,missing data |
| Directness | Whether a passage explicitly states the claim versus merely talking about the same topic. | EvidenceRetrieval | specificity,explicitness |
| Stakeholder | An institution of the Austrian healthcare system represented in the negotiation. Never a natural person. | StakeholderModel | actor,player,party,participant |
| Stakeholder Profile | Mandate, interests, constraints, budget limits and decision priorities of a Stakeholder. | StakeholderModel | persona spec,agent config |
| Interest | A weighted goal the stakeholder optimises for, scoped to policy topics. | StakeholderModel | objective,preference |
| Constraint | A hard limit the stakeholder cannot concede in negotiation. | StakeholderModel | red line,limit,restriction |
| Budget Limit | Numeric spending envelope within which proposals are acceptable. | StakeholderModel | budget cap,cost ceiling |
| Historical Position | A provenance-backed past institutional stance, weighted lower than current events. | StakeholderModel | past statement,legacy stance |
| Agent Binding | Immutable link of one Stakeholder Profile to the agent that negotiates on its behalf in a run. | StakeholderModel | persona binding,agent assignment |
| Simulation Run | One end-to-end negotiation over one policy question. | NegotiationSession | session,job,simulation |
| Negotiation Mandate | Moderator framing of the question: objective, constraints, actors, rules, stopping conditions. | NegotiationSession | brief,task,setup |
| Position | A stakeholder's current evidenced stance on a conflict topic, with revision lineage. | NegotiationSession | opinion,view,stance |
| Argument | One turn's reasoned contribution with stance, claims and citations. | NegotiationSession | message,utterance,chat line |
| Conflict Topic | A formalised point of institutional disagreement tracked across rounds. | NegotiationSession | issue,disagreement,gap |
| Coalition | Stakeholders aligned on one conflict topic behind an explicit shared proposal. | NegotiationSession | alliance,bloc |
| Revision Reason | Structured justification citing the arguments and evidence that caused a position change. | NegotiationSession | explanation,rationale |
| Stopping Condition | The named rule that terminated the run. | NegotiationSession | exit criterion,termination rule |
| Consensus Record | Derived per-topic outcome statement of agreement level among stakeholders. | ConsensusAnalysis | agreement summary,result |
| Majority Position | Stance carried by most weight-bearing stakeholders on a topic. | ConsensusAnalysis | winning view |
| Minority Position | Dissenting stance with holders and reasons, preserved explicitly. | ConsensusAnalysis | dissent,objection |
| Compromise Package | Bundle of individually accepted, mutually compatible measures with provenance. | ConsensusAnalysis | deal,package,settlement |
| Rejected Proposal | A measure that did not reach support and is documented as not carried. | ConsensusAnalysis | failed proposal,discarded option |
| Impact Assessment | Scenario effect estimate with explicit assumptions and uncertainty label. | ConsensusAnalysis | forecast,projection |
| Uncertainty Label | Stated basis of an estimate: evidenced, modelled or assumed. | ConsensusAnalysis | confidence,certainty |
| Decision Brief | The complete published negotiation result artefact with eight sections and resolvable citations. | DecisionBrief | report,result page,answer |
| Brief Section | One of the eight mandated components of the brief. | DecisionBrief | chapter,block |
| Citation Reference | Resolvable pointer from a brief statement to an evidence passage with provenance. | DecisionBrief | source note,footnote,link |
| Actor Summary | Institution, goals, constraints and adopted positions shown in the actors section. | DecisionBrief | agent card,participant profile |
| Position Timeline | Stance trajectory per stakeholder across rounds for the change visualisation. | DecisionBrief | evolution chart,stance history |
| Claim | A verifiable assertion from an argument, typed by what verification it requires. | ClaimValidation | fact,statement,assertion |
| Claim Verification | The audited verdict for a claim with its source set and comparison method. | ClaimValidation | fact check,validation |
| Unsupported Assertion | A claim with no adequate evidence, surfaced as low-confidence rather than removed. | ClaimValidation | unsourced claim,guess |
| Contradiction Finding | Detected incompatibility between two verified claims or a claim and an authoritative figure. | ClaimValidation | conflict of figures,inconsistency |
| Measure Reference | Normalised identity of a figure (measure, unit, period, geography) enabling comparison across agents. | ClaimValidation | metric key,dimension |
| Authoritative Source | A source tier admissible for verification, as opposed to press reporting. | ClaimValidation | ground truth,official data |
| Article Section | Typed region of an article (headline, standfirst, body, caption, quotation) used for directness scoring and quotation screening. | EvidenceCorpus | zone,block type,layout part |
| Quotation Block | Span of quoted or reported speech of a named person; retained structurally, never promoted as agent evidence. | EvidenceCorpus | quote,citation of person,direct speech |
| Canonical Article | The one article that owns citable passages when several syndicated copies exist. | EvidenceCorpus | original article,master copy |
| Language Tag | German variant marker driving tokenisation and embedding choice. | EvidenceCorpus | locale,lang code |
| Quarantined Document | A document that failed the extraction quality gate and is excluded from citation but kept for diagnostics. | EvidenceCorpus | rejected file,bad scan |
| Ingestion Run | One auditable batch execution of corpus ingestion with accepted, quarantined and failed counts. | EvidenceCorpus | import job,crawl,batch |
| Index Manifest | Published index version for a corpus snapshot, recording embedding model, indexed passages and searchable-since timestamp. | EvidenceCorpus | index state,vector version |
| Retracted Passage | An indexed passage withdrawn because its document was retracted or reclassified as unusable. | EvidenceCorpus | removed chunk,deleted hit |
| Authority Weight | Numeric trust weight derived from the corpus-owned source tier; the only way retrieval may express trust. | EvidenceRetrieval | trust score,credibility,AuthorityTier value |
| Retrieval Trace | Reproducibility record per pack: index manifest version, models used, rewrite applied, stance counts. | EvidenceRetrieval | provenance of retrieval,audit log |
| Query Rewrite | Deterministic German-language expansion of a claim before search: compounds, umlauts, institutional synonyms. | EvidenceRetrieval | query expansion,normalisation |
| Negotiating Power | Derived institutional leverage from mandate scope, budget authority, veto rights and coalition centrality; never assigned by an agent. | StakeholderModel | leverage,influence,weight |
| Veto Right | Power to block a class of proposals outright, bounding what consensus is reachable. | StakeholderModel | blocking power,reserved competence |
| Dependency | Directional relation between institutions (funding, approval, staffing, data) with strength and affected proposal classes. | StakeholderModel | link,reliance |
| Mandate Scope | Admissible range of agreement for an institution; bounds every concession its agent may make. | StakeholderModel | competence,remit |
| Turn Assignment | A stakeholder's allocated floor in a round, with order, topic and used/passed/abstained outcome. | NegotiationSession | slot,speaking order |
| Negotiation Phase | Monotonic process stage from position formation to closure that bounds legal commands. | NegotiationSession | stage,step |
| Proposal | Structured substance of a position: measure, quantified effect, target population, cost, affected institutions. | NegotiationSession | measure,plan,option |
| Proposal Component | One admissible part of a proposal with its own support record, assemblable into packages. | NegotiationSession | building block,item |
| Coalition Offer | Recorded invitation to join a shared proposal, with conditions and accept/decline outcome. | NegotiationSession | invitation,ask |
| Scenario | A counterfactual assessed against a baseline: the measures of one package, a horizon, an affected population and stated assumptions. | ConsensusAnalysis | case,what-if,variant |
| Feasibility Rating | Political, legal and administrative feasibility of a package with the basis for each rating. | ConsensusAnalysis | implementability,practicality |
| Consensus Threshold | Support level the mandate requires for consensus, adjusted where veto rights apply. | ConsensusAnalysis | quorum,majority rule |
| Veto-Blocked Outcome | A proposal that met the support threshold but is not consensus due to a blocking competence. | ConsensusAnalysis | blocked,vetoed |
| Cited Statement | One statement of the brief with its citations, source claim ids and evidence status; the granularity at which transparency is enforced. | DecisionBrief | sentence,bullet,assertion |
| Rejected Proposal Record | A measure that failed to gather support, with blocking stakeholders and reasons. | DecisionBrief | failed motion,discarded option,not implemented |
| Simulation Disclaimer | Statement that the result is probabilistic agent reasoning over a pinned corpus, not a deterministic forecast and free of real-person positions. | DecisionBrief | caveat,note |
| Reference Figure | Canonical authoritative value for one measure, with as-of date and source tier; the comparison baseline. | ClaimValidation | ground truth value,official figure,baseline |
| Tolerance Band | Admissible deviation below which two figures for one measure are treated as equal. | ClaimValidation | epsilon,rounding tolerance,spread |
| Expert Review | Escalation of an unsettled claim to a review step that returns a verdict with its basis. | ClaimValidation | manual check,second opinion,expert agent |
| Round Learning | Persisted digest of a round's outcomes — which arguments held, which proposals moved, who coalesced — that agents must consume in the next round. | NegotiationSession | reflection,memory,feedback state,lessons |
| Learning Application | Explicit reference from a later argument to the RoundLearning insight that caused it. | NegotiationSession | applied lesson,adaptation |
| Mandate Source | Citable legal or institutional instrument that grounds a veto right, competence or budget limit. | StakeholderModel | legal basis,statute reference,authority ground |
| Attribution Strength | Whether a source explicitly attributes a stance to the institution, reports it, or merely mentions the institution. | StakeholderModel | confidence of attribution,how firmly stated |
| Power Source Kind | Where an institution's authority derives from: legislation, statutory instrument, budget decision, institutional statute or agreement. | StakeholderModel | basis of power,authority type |
| Estimate Basis | Provenance class of a figure: measured, derived, modelled, assumed or not estimated. | ConsensusAnalysis | confidence,source of number,how computed |
| Derivation Input | Enumerated input behind a derived figure, cited so the calculation can be re-run or refuted. | ConsensusAnalysis | input,assumption source |
| Assumed Estimate | A figure without enumerated inputs, publishable only with an explicit assumed label. | ConsensusAnalysis | guess,illustrative value |
| Absence Finding | Auditable record that a stance produced no qualifying evidence, naming the queries and snapshot searched. | EvidenceRetrieval | no results,negative result |
| Recency Exemption | Designation of non-perishable source types (legislation, foundational studies, reference figures) that keep full weight regardless of age. | EvidenceRetrieval | no decay,timeless |
| Speaker Kind | Attribution class of a statement: institution, named person, anonymous or unattributed; decides citability. | EvidenceCorpus | attributed to,source type |
| Authority Rule | Claim-type-specific source ordering used instead of one global authority scale. | EvidenceCorpus | ranking,precedence |
| Institutional Statement | Retained, citable statement attributed to an institution rather than a person. | EvidenceCorpus | press release,official position |
| Verification Path | Type-specific route a claim takes: reference comparison, provision check, study appraisal, or no verification. | ClaimValidation | check type,how verified |
| Causal Support | Appraisal of study evidence behind a causal claim, recorded as supported, contested or unaddressed. | ClaimValidation | evidence for causation,study backing |
| Unverifiable Claim | A claim for which no applicable verification path exists, recorded as ambiguous rather than removed. | ClaimValidation | not checkable,out of scope |

---

## Use Cases (Application Services)

| Use Case | Context | Description | Commands / Collaborators |
|-----------|---------|-------------|---------------------------|
| IngestDocument | EvidenceCorpus | Register a source file, extract text (native or OCR), persist extraction quality and provenance. | register source file,detect format,extract text,record extraction quality |
| SegmentArticle | EvidenceCorpus | Detect article boundaries within a publication, assign publication metadata and split into citable passages with offsets. | detect article boundaries,attach publication metadata,split into passages,compute offsets |
| ClassifySourceAuthority | EvidenceCorpus | Assign an authority tier and derive duplicate/syndication links for an article. | classify authority tier,detect duplicates,link canonical article |
| SearchEvidenceCandidates | EvidenceRetrieval | Execute hybrid BM25 + dense search for a claim and rerank candidates. | build query from claim,run lexical search,run vector search,fuse and rerank |
| AssembleEvidencePack | EvidenceRetrieval | Balance supporting, contradicting and contextual evidence for a claim and score each on authority, relevance, recency, directness. | classify stance of candidates,enforce contradiction quota,score components,freeze pack |
| ApplyRecencyPolicy | EvidenceRetrieval | Weight candidate evidence by publication recency under a configurable policy. | load recency policy,compute decay weight,rerank by weighted score |
| RegisterStakeholder | StakeholderModel | Create or update an institutional stakeholder with mandate, interests, constraints and decision priorities. | register institution,declare interests,declare constraints,set budget limits,set decision priorities |
| BindAgentPersona | StakeholderModel | Produce the agent binding for an activated stakeholder, assembling historical positions and persona rules. | select stakeholder profile,load historical positions,validate institution-only identity,emit AgentBinding |
| OpenSimulationRun | NegotiationSession | Turn a policy question into a negotiation mandate, select stakeholders and open a run in PositionFormation phase. | parse policy question,select relevant stakeholders,declare negotiation rules,open run |
| SubmitInitialPosition | NegotiationSession | Record a stakeholder's opening position with claims and cited evidence before debate opens. | gather evidence pack,formulate position,attach claims,attach citations,open position |
| TakeNegotiationTurn | NegotiationSession | Let a stakeholder respond within a round: submit an argument against a target position or argument, with stance and evidence. | select target,determine stance,assemble argument,attach evidence refs,close round when all turns complete |
| RevisePosition | NegotiationSession | Change a position only with a recorded reason citing the arguments or evidence that caused the shift. | assert reason present,assert causal references exist,supersede previous position,emit PositionRevised |
| TrackConflictTopic | NegotiationSession | Open, update and resolve conflict topics with per-stakeholder stance across rounds. | detect divergence,open conflict topic,record stances,mark resolved/unresolved |
| FormCoalition | NegotiationSession | Join stakeholders on a conflict topic behind an explicit shared proposal. | assert shared proposal,add members,record coalition position |
| EvaluateStoppingCondition | NegotiationSession | Decide whether the negotiation closes: consensus threshold, round cap or deadlock; record the fired condition. | compute consensus level,check round cap,detect deadlock,close run |
| ReplaySimulationHistory | NegotiationSession | Reconstruct a run to any round from persisted domain events for audit and re-render. | load event stream,fold events,rebuild projections |
| DeriveConsensus | ConsensusAnalysis | Compute consensus, majority and minority positions and unresolved conflicts from the negotiation record. | classify stances per topic,compute support levels,separate majority/minority,list open conflicts |
| ComposeCompromisePackage | ConsensusAnalysis | Assemble accepted proposal components into a compromise package with provenance. | collect accepted components,merge compatible proposals,attach provenance,record rejected proposals |
| AssessImpact | ConsensusAnalysis | Attach scenario impact estimates with assumptions and uncertainty to each package. | state assumptions,estimate scenario effect,label uncertainty |
| PublishDecisionBrief | DecisionBrief | Project the completed run into the eight-section brief with resolvable citations. | collect sections,resolve citations,assert all sections present,publish brief |
| VerifyClaim | ClaimValidation | Check a quantitative or legal claim against authoritative sources and reject contradictions. | extract claim,retrieve authoritative evidence,compare figures,record verdict |
| FlagUnsupportedAssertion | ClaimValidation | Detect claims without evidence and mark them low-confidence. | detect missing citations,record unsupported flag,propagate confidence |
| EnforceInstitutionOnlyOutput | GovernanceCompliance | Reject agent output that names or quotes real persons before it reaches persistence. | scan for person references,scan for direct quotations,reject or rewrite,record violation |
| DisclosePositionProvenance | GovernanceCompliance | Produce the derivation record for each position: sources, arguments and model invocation reference. | collect derivation inputs,attach invocation metadata,emit ProvenanceDisclosure |
| RunSimulationJob | SimulationOrchestration | Execute the agent workflow graph as a background job, emitting progress events and supporting pause/resume. | enqueue job,advance graph node,emit progress event,pause/resume,record invocation metadata |
| ExtractDocumentText | EvidenceCorpus | Extract text natively when a text layer exists, fall back to OCR for scanned pages, and store the resulting extraction quality and method. | probe text layer,select native or ocr path,run extraction,measure missing-glyph rate,accept or reject document |
| LinkCanonicalArticle | EvidenceCorpus | Detect syndicated and duplicate articles by content similarity and attach them to one canonical article so citations and evidence counts collapse correctly. | compute content fingerprint,compare against existing articles,elect canonical article,link duplicates |
| StreamSimulationProgress | SimulationOrchestration | Publish ordered progress events for a running simulation so clients observe rounds, turns and position changes as they commit. | subscribe to run event stream,order events by commit sequence,emit progress event,close stream on run end |
| PauseOrResumeSimulation | SimulationOrchestration | Pause a running job at a safe boundary and resume it later from persisted negotiation state without losing rounds or arguments. | request pause,finish current turn boundary,persist checkpoint reference,resume from last committed round |
| RecordAgentInvocation | SimulationOrchestration | Persist the traceability envelope of every agent call: model, prompt template version, parameters, evidence pack ids and token cost. | capture model and prompt version,attach evidence pack ids,record token and latency cost,link invocation to produced argument |
| ScoreEvidenceCandidates | EvidenceRetrieval | Compute the inspectable weight breakdown for every candidate — authority weight, lexical score, semantic similarity, recency weight and directness — and rank them so the jury can see why evidence was used. | resolve authority weight from tier,attach lexical and semantic scores,compute directness against claim,apply recency weight,emit EvidenceScore and rank |
| TranslateQuestionToMandate | NegotiationSession | Moderator-specific framing: convert the free-text policy question into a testable mandate with objective, target metric, time horizon, budget constraint and negotiation rules before any run exists. | extract objective and target metric,extract time horizon,extract budget and feasibility constraints,declare negotiation rules,emit NegotiationMandate |
| SelectRelevantStakeholders | StakeholderModel | Moderator-specific selection: determine which institutions are materially affected by the mandate and may therefore be bound into the run. | map mandate topics to stakeholder interests,score materiality,exclude irrelevant institutions,assert minimum viable set |
| DetectArgumentContradiction | NegotiationSession | Moderator-specific arbitration: detect when two stakeholders assert incompatible claims or refuse to justify a position, and force a justification turn. | compare claims across arguments,request justification,open or escalate conflict topic,record procedural note |
| SummariseIntermediateResult | NegotiationSession | Moderator-specific interim documentation after each round: agreed points, open conflicts, emerged options and failed proposals, so convergence is observable mid-run. | collect round arguments,classify agreed vs contested,list emerged options,list failed proposals,emit interim summary |
| PinCorpusSnapshot | EvidenceCorpus | Freeze the exact document set and index version a run may search, so the evidence base of a published brief is reproducible after re-ingestion. | select covered documents,compute snapshot manifest hash,pin index version,emit CorpusCollection |
| IndexIngestedPassages | EvidenceCorpus | Publish extracted passages into the hybrid index (BM25 + vectors) with provenance payloads, keeping ingestion and searchability decoupled and idempotent. | collect accepted passages,build lexical index entries,compute embeddings,upsert vector payload with provenance,mark indexed |
| RecordGovernanceViolation | GovernanceCompliance | Persist a rejected agent output with its violation class, the offending span and the rewrite that replaced it, so the transparency rule is provably enforced. | classify violation,capture offending span,store rewritten output,link to agent invocation,emit violation record |
| VersionDecisionBrief | DecisionBrief | Republish a brief for the same run as an immutable successor version, preserving the prior version and the reason for regeneration. | assert prior brief published,capture regeneration reason,supersede old version,emit new BriefVersion |
| CompareScenarios | ConsensusAnalysis | Evaluate alternative compromise packages side by side on cost, acceptance and feasibility so the brief can state why one package was recommended over another. | select packages to compare,score cost acceptance and feasibility,rank alternatives,record comparison basis |
| RecordHistoricalPosition | StakeholderModel | Extract and store a provenance-backed past institutional stance from corpus evidence, weighted below current events, so personas argue from documented history rather than invention. | retrieve evidence about institution,extract stated stance,attach provenance and publication date,apply recency weight,emit HistoricalPosition |
| RecordAbstention | NegotiationSession | Close the gap in round-close invariant FR-014: a stakeholder that neither argues nor revises must be explicitly recorded as abstaining on a topic before the round can close. | detect missing turn,record abstention with topic,assert no open turn remains,permit round close |
| ResolveMeasureIdentity | ClaimValidation | Normalise a claim's measure into a comparable identity (measure, unit, period, geography) so that figures from different agents and sources can be tested for contradiction. | extract measure name and unit,normalise reference period,normalise geography and population,reconcile with existing MeasureReference,emit ComparisonKey |

---

## Open Questions

RESOLVED this revision: negotiation learning (RoundLearning + LearningApplication, persisted per round, applied with an explicit citation); impact provenance (EstimateBasis: measured|derived|modelled|assumed, with enumerated DerivationInput); stakeholder authority grounding (MandateSource cites legislation/statute/budget decision; unsourced powers inadmissible); evidence balance relaxed to recorded search coverage + AbsenceFinding; claim-type verification paths (quantitative/legal/causal/qualitative, with causal and qualitative never 'verified'); authority made claim-type-relative (AuthorityRule) instead of one global scale; historical positions gated on AttributionStrength (mention is not a position); recency exemptions for non-perishable sources; quotations split by SpeakerKind so institutional statements survive while personal quotes are excluded; derived artefacts declared projections, not competing sources of truth; RetrievalQuery demoted from aggregate root; CorpusCollection and IndexManifest reduced to manifests rather than corpus-wide transactional aggregates; 8 implementation-detail events removed from the catalogue. OPEN: (1) corpus profiling — actual formats, OCR share, metadata quality, German text quality — must precede any throughput or latency target; (2) RAG ingestion contracts (segmentation of multi-clipping digests, duplicate vs syndication vs same-event clustering, BM25/dense fusion weights, reranking model, evidence classification relative to a claim) belong to the architecture pass, not this exploration; (3) database schema, index structure and embedding strategy for German; (4) API contracts and SSE event shapes; (5) worker and failure-recovery design; (6) evaluation harness for evidence quality and negotiation behaviour; (7) which stakeholder set is authoritative and who curates MandateSource citations; (8) reproducibility policy: what is replayed vs regenerated when a run is resumed. DEFERRED as post-hackathon: multi-question comparison runs, cross-run learning, multi-language UI, real-time collaboration.

---

## Aggregate Roots

Document, EvidencePack, Stakeholder, AgentBinding, SimulationRun, ConsensusRecord, CompromisePackage, DecisionBrief, Claim, IngestionRun, Scenario