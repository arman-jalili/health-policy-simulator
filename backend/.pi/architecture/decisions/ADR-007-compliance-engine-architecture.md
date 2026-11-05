# ADR-007: Compliance Engine Architecture

**Status:** Accepted
**Date:** 2026-11-05
**Session:** 87433e56-b1a2-4464-a232-2dc4fe6f9dfd

## Context

The challenge imposes hard representational constraints:

1. Institutions must not be represented by individual real persons.
2. No statements by real persons may be quoted or depicted.
3. It must be transparent how an agent's position arises (sources, arguments, model).
4. Figures must not contradict each other and must be substantiated.

These are not stylistic preferences — they are admissibility rules. A single quoted official in a
demo would invalidate the entry. The rules must be enforced **where the violation would be created**
(agent output) and **where it would be published** (the brief), not discovered by a reviewer.

## Decision

**A two-stage guard pipeline with a persisted violation record, plus a provenance disclosure
requirement at the brief boundary.**

**Stage 1 — pre-persistence guard (on every agent output, before any domain write)**
| Check | Mechanism | On violation |
|---|---|---|
| Person reference | Institutional-name allowlist; NER for `PERSON`; title patterns (`Dr.`, `Mag.`, `Prof.`, `Obmann`, `Präsident`) | Reject the field; do not persist the argument |
| Direct quotation of a person | Quotation-block attribution (`speaker_kind = person`) carried from the corpus | Strip the quotation, retain the surrounding institutional sentence |
| Unattributed claim presented as fact | Claim extraction: claim without `passage_id` or figure reference | Downgrade to `unsupported` label, keep text |
| Figure contradiction | Claim verification against `ReferenceFigure` with tolerance band | Reject the figure or mark `contradicted` |

Guard output is one of: **accept**, **rewrite** (with the rewritten span recorded), **reject**.
Rewrites are recorded so the transformation is auditable — the system never silently edits.

**Stage 2 — publication gate (brief)**
A brief cannot be published unless every `CitedStatement` resolves to a passage and every
disclosure is present (rejected proposals, unsupported statements, simulation disclaimer).
Failure raises `BriefBlockedByMissingDisclosure` — a domain event, not a 500.

**Provenance disclosure requirement**
`DisclosePositionProvenance` must produce, for every published position: the evidence passages
cited, the arguments that caused each revision, and the invocation id of the model call. A position
without a disclosure record is unpublishable.

**Where deterministic vs LLM checks live**
| Check | Implementation | Why |
|---|---|---|
| Person/quotation detection | Deterministic rules + NER | Must be testable and predictable; LLM judgement is not a compliance control |
| Unsupported claim detection | Deterministic (citation presence) | Boolean fact |
| Figure contradiction | Deterministic (parse, normalise, compare with tolerance) | Arithmetic, not judgement |
| Whether an argument is convincing | Not a compliance concern | Out of scope of the guard |

## Consequences

- Compliance failures are cheap and loud, before they reach a brief.
- The allowlist of institutional names becomes a curated artefact (operator-owned).
- Deterministic guards can produce false positives (e.g. an institution named after a person).
  The rewrite path exists precisely so a false positive does not destroy a legitimate argument.
- Every blocked output is recorded, so the "we enforce this" claim is demonstrable in the demo.

## Alternatives Considered

| Alternative | Why rejected |
|---|---|
| Post-hoc review of the brief | Violations already persisted; the demo could ship one |
| LLM-as-judge for compliance | Unreliable, unauditable, non-deterministic — fails the "provably enforced" test |
| Prompt instruction only ("never quote persons") | Not a control; a single drift publishes a violation |
| Removing all quotations from the corpus | Over-broad: loses legitimate institutional statements, which are the actual evidence |

## Affected Modules

GovernanceCompliance (owner), EvidenceCorpus (speaker attribution at segmentation),
ClaimValidation (figure checks), DecisionBrief (publication gate), NegotiationSession (pre-write hook)
