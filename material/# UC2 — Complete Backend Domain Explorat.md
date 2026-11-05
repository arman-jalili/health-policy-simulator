# UC2 — Complete Backend Domain Exploration and Design

## Objective

Design the complete backend foundation for UC2 — HealthPolicy Simulator.

This is not a preliminary exploration or a partial architecture exercise. Produce one coherent, end-to-end backend design that is sufficiently detailed for implementation to begin.

The system simulates negotiations between healthcare stakeholders around policy questions. Stakeholder agents must have distinct interests, positions, constraints and objectives. They exchange arguments, challenge evidence, negotiate, form coalitions, change positions and may reach agreement, partial agreement or remain divided.

The simulation must be evidence-backed and explainable. Users must be able to understand why an agent made an argument, why its position changed, and which evidence influenced the outcome.

## 1. Understand the domain

Study the UC2 challenge requirements and the available project material.

Identify:
- Stakeholders and their responsibilities.
- Their interests, incentives, constraints and conflicting objectives.
- How healthcare policy decisions are actually negotiated.
- What constitutes a meaningful position, argument, counterargument, compromise and coalition.
- How consensus, minority positions and unresolved issues should be represented.
- Which parts of the process require simulation and which require deterministic domain rules.

Avoid treating agents as generic chatbots. Model the actual negotiation process.

## 2. Analyze the document corpus

The project includes approximately 3 GB of Austrian press material from 2020.

Investigate the actual documents and their formats. Determine:
- Document types and extraction requirements.
- Metadata availability and consistency.
- Article boundaries and publication information.
- Page-level provenance and citation requirements.
- Duplicates, syndicated articles and repeated content.
- German-language extraction and retrieval challenges.
- Scanned documents and OCR requirements.
- What information can reliably be extracted and what requires validation.

Distinguish press reporting, quoted opinions, institutional statements, scientific studies, legislation and other authoritative sources.

Do not treat press coverage as ground truth. Identify which additional authoritative sources are needed for credible healthcare policy analysis.

## 3. Design the evidence and RAG domain

Design the complete evidence lifecycle:

Document ingestion → extraction → normalization → metadata → article segmentation → chunking → indexing → retrieval → reranking → evidence validation → citation → use in arguments.

Define:
- Document, publication, article, passage and evidence concepts.
- Source authority, relevance, recency and directness.
- Supporting, contradicting and contextual evidence.
- Evidence quality and uncertainty.
- Citation and provenance requirements.
- How an agent obtains evidence for a particular claim.
- How contradictory evidence is surfaced.
- How evidence influences arguments and position changes.
- How unsupported claims are identified and handled.

Do not invent arbitrary confidence percentages. Define what can actually be measured and explain how uncertainty should be represented.

The system must retrieve evidence that challenges an agent's initial position, not only evidence that supports it.

Design ingestion for the full corpus, not just a small demo dataset. However, distinguish the minimum viable implementation from later scaling requirements.

## 4. Complete domain and requirements design

Produce the complete domain model, including:

- Functional requirements (FRs).
- Non-functional requirements (NFRs).
- Explicit assumptions.
- Domain terminology and glossary.
- Actors and use cases.
- Bounded contexts and their responsibilities.
- Aggregates and aggregate roots.
- Entities and value objects.
- Domain invariants and business rules.
- Domain events and event payloads.
- Commands and queries.
- State transitions.
- Context relationships and integration contracts.

Pay particular attention to the negotiation lifecycle and evidence lifecycle.

Define how the system preserves a traceable history of:
- Initial stakeholder positions.
- Arguments and counterarguments.
- Evidence used.
- Negotiation rounds.
- Coalition formation.
- Position changes and their reasons.
- Final agreements, disagreements and unresolved issues.

## 5. Backend architecture and technology

Use the following as the proposed technology baseline. Validate each choice against the actual requirements and explain any changes.

- Python
- FastAPI and Pydantic
- LangGraph for agent workflow orchestration
- Custom Python domain layer for negotiation rules and state
- PostgreSQL for application data and persistent domain state
- Qdrant for vector and hybrid retrieval
- Docling and PyMuPDF for document extraction
- OCRmyPDF and Tesseract for scanned documents
- BM25 and dense retrieval with reranking
- Provider-independent LLM integration
- Background workers for document ingestion and long-running tasks
- Server-Sent Events for streaming simulation progress
- pytest for backend testing

Define the responsibilities and boundaries of each technology.

LangGraph must not become the domain model or the source of truth for negotiation state. Explain how workflow orchestration interacts with domain commands, events and persistence.

Avoid unnecessary infrastructure and distributed-system complexity. Design for a hackathon implementation that can evolve without requiring a rewrite.

## 6. Agent and negotiation design

Define:
- Stakeholder agent responsibilities and boundaries.
- Agent identity and stakeholder representation.
- Initial position generation.
- Argument and counterargument structure.
- Evidence requirements for claims.
- Negotiation rounds and turn-taking.
- Coalition formation.
- Position revision.
- Compromise generation.
- Consensus and minority outcomes.
- Stopping conditions.
- Handling of deadlock and unresolved issues.

Make the distinction between an agent's generated proposal and an accepted domain state explicit.

## 7. Persistence, reproducibility and traceability

Define what must be persisted and why.

The system should support reconstructing a simulation and explaining its outcome. Address:
- Simulation state.
- Domain events.
- Agent outputs.
- Evidence references.
- Prompt/model version information.
- Negotiation history.
- Reproducibility limitations caused by probabilistic LLM outputs.

Do not claim deterministic simulation results when the underlying model behavior is probabilistic.

## 8. API and integration design

Define the backend API contracts required for:
- Creating and configuring a simulation.
- Selecting a policy question and scenario.
- Managing stakeholder agents.
- Starting, pausing and resuming simulations.
- Streaming negotiation progress.
- Inspecting arguments and evidence.
- Inspecting position changes.
- Retrieving consensus, minority positions and unresolved issues.
- Accessing the final decision brief.

Include representative request and response schemas.

## 9. Testing and quality strategy

Define tests for:
- Domain invariants and state transitions.
- Evidence provenance and citation correctness.
- Retrieval quality.
- Contradictory evidence retrieval.
- Agent behavior and stakeholder differentiation.
- Negotiation quality.
- Position changes and their explanations.
- API contracts.
- Ingestion correctness.
- Failure handling and recovery.

Define measurable evaluation criteria. Avoid vague metrics such as "agent quality" without an evaluation method.

## 10. Implementation readiness

Finish with:

1. Complete backend architecture and component responsibilities.
2. Complete domain model and bounded-context map.
3. Aggregate and event definitions.
4. FR/NFR catalogue.
5. API contract outline.
6. RAG and ingestion pipeline design.
7. Technology decisions with rationale.
8. Key risks and unresolved assumptions.
9. Prioritized implementation backlog with dependencies.
10. A recommended implementation sequence.

Clearly distinguish:
- Decisions that are necessary before implementation.
- Assumptions that can be validated during implementation.
- Features required for the hackathon.
- Capabilities that can wait until after the hackathon.

## Instructions

Be concrete, critical and domain-specific.

Do not produce generic multi-agent architecture advice.

Do not assume that every stakeholder needs an LLM agent. Justify where autonomous reasoning is necessary.

Do not let the RAG implementation become a generic document-chat system. Its purpose is to provide traceable evidence for policy arguments and negotiation.

Do not skip domain modeling in favor of technology diagrams.

Do not defer architecture to a later phase. Deliver the complete backend design in this assignment.

Where information is missing, state the assumption and its consequences rather than silently inventing facts.

The final result must be internally consistent and detailed enough that an engineering agent can start implementation without having to invent the domain model halfway through.