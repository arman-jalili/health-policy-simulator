# MVP Scope — HealthPolicy Simulator (Hackathon)

> **Purpose:** this is the build plan. The full exploration
> (`.pi/domain/exploration/87433e56-b1a2-4464-a232-2dc4fe6f9dfd.md`, 97 entities / 65 events)
> is the **design appendix** answering "how would this scale beyond the prototype". Do not implement it.
>
> **Rule:** if a task cannot be shown on screen in the demo, it does not ship.

---

## 1. What wins

| Jury criterion (from the brief) | Our answer | Ships in |
|---|---|---|
| Realistic institutional perspectives, traceable | 9 personas with interests/constraints/red lines | Day 1 |
| Dynamic discussion, agents react to counterarguments | 4-round loop: position → rebuttal → compromise | Day 1–2 |
| Transparency of decision process | click a claim → source passage | Day 2 |
| Sources, arguments, assumptions, position changes shown | position-change log with reason | Day 2–3 |
| Compromises, alternatives, remaining conflicts | conflict topics + rejected proposals | Day 2 |
| Working prototype, streaming visualisation | SSE round-by-round | Day 1 |
| Figures must not contradict, must be substantiated | curated figure table + number check | Day 3 (optional) |

Not scored: aggregate boundaries, event catalogues, claim-type authority rules, ingestion manifests.

---

## 2. Cut list (explicit — do not build)

Deleted from the model for the hackathon:

`IdentityAccess` (no auth) · `GovernanceCompliance` as a context (**becomes a 30-line output filter**) ·
`SimulationOrchestration` as a context (**becomes one FastAPI background task + SSE**) ·
`DecisionBrief` as a context (**one serializer**) · `ClaimValidation` as a context (**one module**) ·
`IngestionRun`, `IndexManifest`, `CorpusCollection`, `ArticleSection`, `CanonicalArticleRef`, `LanguageTag`,
`ExtractionQuality` (→ columns) · `TurnAssignment`, `NegotiationPhase` (→ enum), `ProposalComponent`,
`CoalitionOffer`, `LearningApplication`, `LearningInsightType`, `NegotiatingPower`, `Dependency`,
`MandateScope`, `PowerSourceKind`, `AgentBinding`, `AttributionStrength`, `VerificationPath`,
`CausalSupport`, `ExpertReview`, `ToleranceBand` (→ constant), `Scenario`, `FeasibilityRating`,
`DerivationInput`, `RetrievalTrace`, `QueryRewrite`, `AuthorityRule`, `SupportLevel`, `UnresolvedConflict`,
`CitedStatement`, `BriefComponentSlot`, `SimulationDisclaimer` (→ constant string).

**Total: 97 → ~20 entities.**

---

## 3. The 8 tables

```sql
-- corpus (3)
source      (id, file_path, outlet, published_on, source_type, text_hash)
article     (id, source_id, headline, body, page)
passage     (id, article_id, ord, text, char_start, char_end, speaker_kind, is_person_quote)

-- simulation (5)
run         (id, question, mandate_json, status, phase, created_at)
run_stakeholder (run_id, stakeholder_key, profile_json)
round       (id, run_id, number, learning_summary, closed_at)
position    (id, run_id, round_id, stakeholder_key, topic, stance, proposal_text,
             claims_json, revision_reason, superseded_by)
argument    (id, run_id, round_id, stakeholder_key, target_position_id, stance,
             text, claims_json, created_at)
conflict_topic (id, run_id, title, status, resolved_in_round)
```

Plus `passage_embedding (passage_id, vector)` if Qdrant is not used (pgvector is enough).
Full-text search: Postgres `tsvector` on `passage.text` — **no separate BM25 service**.

Derived, computed in code, never stored: consensus, majority/minority, rejected proposals, brief sections.

---

## 4. The 9 personas (YAML, one file each)

```yaml
key: social_insurance
name: Dachverband der Sozialversicherungsträger
interests:
  - cost containment (weight 0.4)
  - efficient service delivery (0.3)
  - legal certainty (0.3)
constraints:
  - no benefit cuts without statutory basis
  - budget increase above 5% not acceptable
red_lines:
  - mandatory telemedicine for all patients
budget_authority: high
veto_classes: [statutory_benefit_change]
historical_positions:
  - "opposes blanket telemedicine mandates (2020)"
```

Personas: social insurance, health ministry, finance ministry, provinces, medical chamber,
contract physicians, hospitals, care sector, patient representatives.

Fictional-but-institutional names only. **No real persons anywhere** — enforced by the output filter.

---

## 5. Negotiation loop (the demo)

```
1. moderator.parse_question   → mandate: objective, target metric, horizon, constraints
2. select stakeholders        → all 9 (static list for demo)
3. ROUND 1  position formation
      each agent: evidence pack (support + contradict) → stance + proposal + claims[]
4. moderator: detect conflict topics (topics where stances differ)
5. ROUNDS 2..4  debate
      each agent: sees opponent arguments + last round summary → rebuts, may revise
      revision requires: reason + which argument changed its mind
      moderator writes round learning_summary → injected into next round
6. ROUND 5  compromise
      moderator proposes package from accepted components
      each agent: accept / reject / amend with condition
7. close: consensus, majority, minority, unresolved, rejected proposals
8. brief: 8 sections + citation refs
```

Stopping: consensus threshold met, or round cap (5), or deadlock (no stance change in a round).

**Learning (required by the brief):** `round.learning_summary` — a short moderator text of what
shifted and why, injected into every prompt of the next round. That is the whole mechanism.
No entity, no graph.

---

## 6. Evidence contract

Per claim the agent asserts, the system fetches:

- 4 supporting passages, 4 contradicting/contextual passages
- each with `authority_tier`, `published_on`, `published_on` recency weight, passage id
- if a direction yields nothing: `{"absence": true, "queries": [...], "reason": "no candidate above threshold"}`

Passage payload given to the LLM contains **only** `passage.id`, text and metadata — never the
file path. Agent output must cite `passage_id`; unknown ids are rejected → claim marked unsupported.

Ingestion: 200–500 articles for the demo. Docling/PyMuPDF, OCR fallback via OCRmyPDF+Tesseract.
Segmentation by headline heuristics; **boundary uncertainty is logged, not solved**.

Dedup: sha256 on normalised text only. Syndication/same-event clustering: **out of scope**, noted as future work.

---

## 7. API (7 endpoints)

```
POST /runs                    {question} → {run_id}
GET  /runs/{id}/stream        SSE: round_opened, position, argument, revision, conflict, round_closed, run_closed
GET  /runs/{id}               full state
GET  /runs/{id}/arguments     filterable by stakeholder, round
GET  /runs/{id}/positions     incl. revision history
GET  /runs/{id}/brief         8 sections + citations
GET  /passages/{id}           provenance: file, outlet, date, page, offsets
```

---

## 8. Build order (fail fast on the demo, not on infrastructure)

| Day | Deliverable | Done when |
|---|---|---|
| 0.5 | Ingest 50 articles → passages in Postgres with provenance | `GET /passages/{id}` returns source text |
| 0.5 | 9 personas + one agent turn producing stance + claims with cited passage ids | one agent answers the waiting-time question |
| 1.0 | Round loop + SSE | screen shows 9 positions streaming in |
| 0.5 | Round learning summary + rebuttal round | an agent visibly changes its mind with a stated reason |
| 0.5 | Moderator conflict extraction + compromise round | conflict topics and one package appear |
| 0.5 | Brief serializer + 8 sections | brief renders with citations |
| 0.5 | Number check against 10 curated figures | one fabricated figure gets flagged live |
| 0.5 | Polish, demo script rehearsal | 3-minute run |

If time is short, cut in this order: number check → compromise round → rebuttal granularity.
**Never cut**: evidence citations, position-change reasons, streaming.

---

## 9. Demo script (3 minutes)

1. Enter the question: *"How can waiting times for specialist appointments be reduced by 20%
   within five years without increasing spending by more than 5%?"*
2. Positions stream in. Point out two institutions disagreeing on the same fact.
3. Click the medical chamber's claim → show the passage from the press archive.
4. Round 3: an agent revises its position — show the stated reason and the argument that caused it.
5. Conflict panel: 3 consensus points, 2 open conflicts, 2 rejected proposals.
6. Brief: consensus, minority, unresolved, impact **labelled as modelled/assumed**.
7. One sentence: "every claim in this brief resolves to a page in the archive."

---

## 10. What to say about scale (the appendix)

Keep the full exploration. One slide:

> "The prototype models the negotiation as 8 tables. The full design separates 7 core contexts with
> 20 invariants — evidence provenance, claim verification by type, authority grounded in legal
> instruments, and derived artefacts that cannot drift from the negotiation record. That is the
> difference between a demo and something a ministry could audit."

That framing turns the over-engineering into the "beyond the prototype" answer the brief asks for,
without costing a build day.
