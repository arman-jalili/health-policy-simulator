# Build the complete frontend for the HealthPolicy Simulator

You are the frontend lead. Build the production-quality frontend for an **existing, working backend** in this
repository, in one shot: **Next.js (App Router) + TypeScript strict + Tailwind CSS + D3.js**. No placeholders,
no TODOs in shipped code, no mock data, no invented endpoints.

The product: a **multi-agent negotiation simulator for Austrian healthcare policy**. Nine institutional
stakeholders (Ärztekammer, Apothekerkammer, BMSGPK, Krankenhausgesellschaft, Landesgesundheitsfonds, ÖGK,
Patientenanwaltschaft, Privatkrankenanstalten, Sozialversicherung) negotiate a policy question over rounds;
every position must cite frozen evidence; output is a consensus analysis and an eight-section decision brief.
The demo audience is a hackathon jury. **They must see decisions being made, with evidence and dissent.**

---

## 0. Read before writing a single line

Mandatory, in this order:

1. `backend/docs/demo-walkthrough.md` — the golden path the UI must reproduce (it is verified end to end).
2. `backend/docs/configuration.md` — env vars, pricing/LLM posture, readiness fields.
3. Module contracts in `backend/.pi/architecture/modules/`:
   `negotiation-session.md`, `consensus-analysis.md`, `decision-brief.md`, `evidence-retrieval.md`,
   `claim-validation.md`, `governance-compliance.md`, `simulation-orchestration.md`, `stakeholder-model.md`.
   Each has an **API surface**, a **Wiring Contract** and a *Collaborator reachability (W8)* table — the last
   two tell you what is real and what is deliberately deferred. Read them literally; do not "improve" them.
4. `backend/.pi/domain/ubiquitous-language.md` — the vocabulary. **Use these words in the UI.**
5. `backend/.pi/architecture/DEFERRED.md` — what is knowingly missing (D-001, D-004, D-005 …).
6. Skills (read them, they are the house style):
   `.pi/skills/nextjs-enterprise-codegen.md`, `.pi/skills/design-system-enterprise-codegen.md`.
7. The live contract: `curl -s http://127.0.0.1:8000/openapi.json | jq '.paths | keys'`.

**Hard rules**

- Do **not** modify anything under `backend/`. The frontend consumes the API as it is.
- Do **not** invent endpoints, fields or semantics. If a screen needs data that does not exist, degrade
  gracefully, name the gap in the UI, and record it in `frontend/DEFERRED.md` with the issue-style format
  used in `backend/.pi/architecture/DEFERRED.md`.
- Everything you display that comes from the backend must be validated with **zod** at the boundary.
- Austrian German is the primary language, English secondary (all copy in one typed dictionary; no hardcoded
  strings in components).

---

## 1. What "done" means (the demo, minute by minute)

The UI must make these eight moments legible without a narrator:

| # | Moment | What the screen proves |
|---|---|---|
| 1 | **Mandate** | Nine institutions bound to a run, each with mandate scope, budget, veto class, power source |
| 2 | **Rounds** | A round opens with a turn order; the run cannot close until every stakeholder has a turn or abstention |
| 3 | **Positions & arguments** | Each position cites an evidence pack; each argument cites evidence or is explicitly marked unsupported |
| 4 | **Evidence** | Passage text, provenance (outlet, date, page, offsets), score decomposition, and honest *absence* when nothing supports a claim |
| 5 | **Guards** | A quoted person or an unknown institution is rejected/rewritten; a contradicted figure is flagged |
| 6 | **Consensus** | Support vs threshold, **veto-blocked** outcomes, recorded minorities with objections, unresolved conflicts |
| 7 | **Brief** | Eight sections in order, resolved citations, rejected proposals, versions, export |
| 8 | **Cost & control** | Live job progress, pause/resume, tokens and EUR per stakeholder and round, budget |

If the backend is degraded (`/readyz` → `degraded`), the UI must say so in one persistent, honest banner
with the named reasons — never a silent empty page.

---

## 2. Stack, repo layout, commands

- Node 22, **pnpm**, **Next.js 15 (App Router)**, **TypeScript strict** (`noUncheckedIndexedAccess`,
  `exactOptionalPropertyTypes`), **Tailwind CSS v4** (CSS-first config via `@theme`), **d3** (`d3-scale`,
  `d3-shape`, `d3-array`, `d3-axis`, `d3-format`, `d3-time-format`, `d3-selection` — not `d3` metapackage),
  **zod**, **@tanstack/react-query v5**, **vitest** + **@testing-library/react** + **jsdom**,
  **@playwright/test** (one smoke spec), **axe-core** (a11y assertions).
- Do **not** add: UI kits (MUI/shadcn/Chakra), chart libraries (recharts/nivo/visx), state libraries
  (redux/zustand/jotai), CSS-in-JS, icon packs beyond a hand-written SVG set, or an i18n framework.
  Keep the dependency surface small enough to build in one shot.

```
frontend/
├── PROMPT.md                  # this file
├── README.md                  # how to run, env, demo script
├── DEFERRED.md                # gaps against the backend contract
├── .env.example               # HPS_API_BASE_URL, HPS_API_KEY (server-only)
├── app/
│   ├── layout.tsx  page.tsx                    # dashboard (runs)
│   ├── api/hps/[...path]/route.ts              # streaming proxy (SSE-safe)
│   ├── runs/new/page.tsx
│   ├── runs/[runId]/
│   │   ├── layout.tsx                          # run shell + tab nav + live status
│   │   ├── page.tsx                            # console: feed, rounds, turn order
│   │   ├── positions/page.tsx                  # positions, revisions, coalitions
│   │   ├── evidence/page.tsx                   # packs, candidates, scores, absence
│   │   ├── consensus/page.tsx                  # records, packages, scenarios, comparison
│   │   ├── brief/page.tsx                      # brief, versions, citations, export
│   │   ├── usage/page.tsx                      # cost, tokens, budget, job progress
│   │   └── governance/page.tsx                 # violations, allowlist, guard check
│   ├── stakeholders/page.tsx
│   ├── claims/page.tsx
│   ├── settings/page.tsx
│   └── health/page.tsx                         # readiness + capabilities matrix
├── components/                # design-system primitives only
├── features/<slice>/          # api.ts (zod + client), hooks.ts, components/*
├── lib/
│   ├── http.ts                # fetch wrapper, error envelope → typed errors
│   ├── sse.ts                 # EventSource-ish reader over the proxy
│   ├── settings.ts            # versioned localStorage store, zod-validated
│   ├── i18n.ts                # de-AT + en dictionaries
│   ├── format.ts              # EUR (tabular), de-AT dates, percentages
│   └── chart/                 # d3 helpers: scale factories, axis, responsive svg
├── styles/globals.css         # @theme tokens
└── tests/                     # vitest unit/component, playwright e2e
```

Commands that must pass at the end: `pnpm typecheck && pnpm lint && pnpm test && pnpm build`.

---

## 3. Backend integration contract

### 3.1 Transport — use a Next.js proxy, not direct browser calls

Create `app/api/hps/[...path]/route.ts`. It must:

- forward GET/POST/PATCH/DELETE to `${HPS_API_BASE_URL}/api/v1/...` (the proxy is mounted under `/api/hps`),
- inject `X-API-Key: ${HPS_API_KEY}` **server-side only** when set (never expose it to the client),
- **stream** responses — no buffering — so SSE works (`Response` with the upstream `body` as-is, preserve
  `content-type`, forward `Last-Event-ID`),
- pass through status codes and the JSON error envelope unchanged.

Why: the backend allows anonymous `localhost` traffic in `AUTH_MODE=demo`, and `CORS_ORIGINS` is empty by
default. Through the proxy the backend sees the Next server (127.0.0.1), the browser never needs CORS, and keys
stay server-side. Do not ask the user to set `CORS_ORIGINS`.

Env (`.env.example`):

```
HPS_API_BASE_URL=http://127.0.0.1:8000
HPS_API_KEY=                 # only for AUTH_MODE=strict; server-side
```

### 3.2 Conventions you must respect

- **Error envelope** on every non-2xx:
  `{ "code": "SNAKE_CASE", "message": "human sentence", "details": [{"field"?: "…", "message": "…"}], "trace_id": "req_…" }`
  Render `message` inline near the action, `code` in small caps for support, `trace_id` in a
  "copy diagnostics" menu. Never render a stack trace.
- **Status codes**: `202` accepted (job queued), `204` no body (abstentions), `409` domain conflict
  (`ROUND_STILL_OPEN`, `RUN_NOT_CLOSED`, `BRIEF_SOURCE_INCOMPLETE`, …), `422` validation/guard
  (`ARGUMENT_WITHOUT_EVIDENCE`, `CLAIM_VERDICT_REJECTED`, `DISCLOSURE_MISSING`, …), `503` dependency
  unavailable (`CONSENSUS_ANALYSIS_UNAVAILABLE`). 409/422 are **product states**, not crashes: show the
  message and the fix (e.g. "close the round first", "cite a pack").
- **IDs are opaque strings** with a type prefix (`run_`, `rnd_`, `pos_`, `arg_`, `cfl_`, `pkg_`, `stk_`,
  `evp_`, `snp_`, `psg_`, `doc_`, `fig_`, `clm_`, `vio_`, `cns_`, `brf_`, `job_`, `inv_`). Never parse,
  never reconstruct, never build one client-side except the demo `invocation_id` label (see 3.5).
- **Money** is a decimal **string** in EUR (`"1.161000"`, `"0"`). Format with `Intl.NumberFormat('de-AT', …)`,
  tabular numerals, 2 decimals for display, 6 in tooltips. Never do float arithmetic on it.
- **Time** is RFC3339 UTC. Display in Europe/Vienna, with a relative form ("vor 12 s") in the live feed.
- **Readiness** `GET /readyz` (outside `/api/v1`): always HTTP 200 unless the DB is down; body
  `{ status: "ready" | "degraded", service, checks: Record<string,string> }`. Known keys:
  `database, llm, llm_model, simulation_model, simulation_pricing, simulation_worker,
  simulation_orchestration, simulation_orchestration_persistence, negotiation_session,
  negotiation_session_persistence, consensus_analysis, consensus_analysis_persistence,
  consensus_analysis_sources, decision_brief, decision_brief_gates, governance_compliance,
  governance_provenance, governance_provenance_producer, governance_allowlist, stakeholder_model,
  stakeholder_institutions, claim_validation, claim_validation_persistence, evidence_retrieval,
  evidence_retrieval_mode, evidence_retrieval_detail, attribution`. Treat unknown keys as pass-through.
  **`attribution: client-declared` and `llm: scripted` must be visible in the UI** — they are honest
  statements that the demo runs without a model and with client-supplied invocation ids.

### 3.3 Live data — the important caveat

There are two different "streams", and today **only one is reachable**:

- `GET /api/v1/runs/{run_id}/stream` is served by **SimulationOrchestration** (job progress). Frames:
  `id: <seq>`, `event: run.queued|run.started|round.started|turn.started|turn.completed|run.paused|
  run.resumed|run.completed|run.failed|run.budget_exhausted|invocation.recorded`, plus a terminal
  `run.stream_closed` with `data: {event_id, run_id, sequence, kind, payload}`. Heartbeats are `: ping`.
  Reconnect with `Last-Event-ID`; an unknown id yields `400 UNKNOWN_LAST_EVENT_ID`.
- The **negotiation event feed** at the same path is shadowed by the above (backend issue #420). Therefore:

**Implement the run console against `GET /api/v1/runs/{run_id}/events`**:

```
GET /api/v1/runs/{run_id}/events[?until_round=N]
→ { "items": [ { "sequence": 12, "event_type": "ArgumentSubmitted",
                 "payload": { … }, "occurred_at": "2026-11-06T06:22:11.412Z" } ],
    "state": { "run_id", "phase", "round", "round_cap", "closed",
               "bound_stakeholder_ids": [], "open_position_ids": [], "coalition_ids": [] } }
```

**There is no `cursor` and no `limit` parameter** — the endpoint replays the whole run log each call (verified
against OpenAPI; this prompt previously claimed otherwise, and `frontend/DEFERRED.md` D-FE-004 records the
correction). So: fetch the full log, sort by `sequence`, and render incrementally client-side (window the list).
Poll 750 ms while `closed == false`, back off to 3 s after 5 idle polls, stop on `closed == true`; the returned
`state` is the canonical run snapshot — do not compute it from events.

**The negotiation SSE now exists** (#420 fixed): `GET /api/v1/runs/{run_id}/negotiation/stream` replays the
domain events with `Last-Event-ID` (`id: <ordinal>`, `event: <name>`, `data: <json>`, `: ping` heartbeats).
`/runs/{run_id}/stream` remains the job-progress feed. Keep the polling implementation behind one hook and switch
when a run needs sub-750 ms updates.

Event names you will see (map each to a feed item with icon + stakeholder + round):
`SimulationRunOpened, RoundOpened, InitialPositionStated, PositionRevised, PositionRevisionRejected,
ArgumentSubmitted, ArgumentRejected, AbstentionRecorded, ConflictOpened, ConflictResolved, CoalitionFormed,
CoalitionOfferMade, RoundLearningCaptured, RoundClosed, NegotiationPhaseAdvanced, SimulationRunClosed`.
`payload` is the domain event's fields — render unknown keys in a collapsible JSON block rather than dropping
them.

Put the polling behind `useRunFeed(runId)` so switching to a real SSE endpoint later is one file.

For **job** progress (after `POST /runs/{id}:start`) use the SSE endpoint above, and also poll
`GET /api/v1/jobs/{job_id}` every 1 s as the authoritative status (`queued|running|paused|completed|failed|
dead_letter|cancelled`) with `attempts`, `checkpoint`, `error`.

### 3.4 Demo bootstrap — there is no pack list endpoint

Positions require `evidence_ids: ["evp_…"]` and the backend has **no** `GET /evidence/packs` list. The
supported way is the seed file produced by `make demo-seed` (`backend/docs/demo-walkthrough.md`), which the
Settings page imports:

```json
{"document_id":"doc_…","snapshot_id":"snp_…","figure_ids":["fig_…"],
 "pack_ids":{"kassenstellen":"evp_…","spitalsreform":"evp_…","pflegepersonal":"evp_…",
             "arzneimittelpreise":"evp_…","digitalisierung":"evp_…"},
 "topics":[…]}
```

Store it in `localStorage` (`hps.seed.v1`), validate with zod, show the five pack ids by topic in a picker.
If it is missing: disable "open position" with an inline explanation and a link to the exact command
(`LOG_LEVEL=ERROR make -s demo-seed > /tmp/demo-seed.json`), because that is the documented, working form.

### 3.5 Attribution (honest, client-declared)

`POST /runs/{run_id}/turns` requires a non-blank `invocation_id` (backend issue: presence is checked, not
membership). The UI must: auto-fill `inv_<run>_<round>_<stakeholder>_<n>`, show it in the argument drawer as
"Attribution (client-declared)", and never claim it was issued by the backend. When a run is driven by
`POST /runs/{id}:start`, real invocation ids come from the worker — display them read-only.

---

## 4. Domain vocabulary (the UI must use these exact words)

| Concept | Values (wire) | German label |
|---|---|---|
| Phase | `draft, position_formation, debate, negotiation, compromise, closed` | Entwurf, Positionsbildung, Debatte, Verhandlung, Kompromiss, Abgeschlossen |
| Stance | `support, oppose, qualify, conditional_accept, abstain` | Zustimmung, Ablehnung, Einschränkung, Bedingte Zustimmung, Enthaltung |
| Stopping condition | `consensus, round_cap, deadlock` | Konsens, Rundenlimit, Patt |
| Conflict status | `open, resolved, deadlocked` | Offen, Gelöst, Festgefahren |
| Consensus outcome | `consensus, partial, veto_blocked, unresolved` | Konsens, Teilweise, Veto blockiert, Ungelöst |
| Proposal class | `statutory_benefit_change, budget_frame, service_catalogue, fee_schedule, hospital_plan, other` | Leistungsänderung, Budgetrahmen, Leistungskatalog, Honorarordnung, Spitalsplan, Sonstiges |
| Package state | `draft, composed, assessed, published, abandoned` | Entwurf, Zusammengestellt, Bewertet, Publiziert, Verworfen |
| Feasibility | `low, medium, high, unknown` | Niedrig, Mittel, Hoch, Unbekannt |
| Impact basis | `measured, derived, modelled, assumed, not_estimated` | Gemessen, Abgeleitet, Modelliert, Angenommen, Nicht geschätzt |
| Uncertainty | `evidenced, modelled, assumed` | Belegt, Modelliert, Angenommen |
| Claim type | `quantitative, legal, causal, qualitative` | Quantitativ, Rechtlich, Kausal, Qualitativ |
| Claim verdict | `pending, verified, contradicted, unsupported, ambiguous` | Ausstehend, Bestätigt, Widersprochen, Unbelegt, Mehrdeutig |
| Guard rule | `GC-001` persons, `GC-002` institutional identities, `GC-003` personal quotations, `GC-004` unsupported facts, `GC-005` contradicted figures | — |
| Violation class | `person_named, personal_quotation, institution_ambiguous, unsupported_fact, contradicted_figure` | Person genannt, Persönliches Zitat, Institution unklar, Unbelegte Tatsache, Widersprüchliche Zahl |
| Speaker kind | `institution, person, anonymous` | Institution, Person, Anonym |
| Attribution strength | `explicit, reported, mention` | Ausdrücklich, Berichtet, Erwähnung |
| Power source | `statutory, contractual, regulatory, budgetary, unspecified` | Gesetzlich, Vertraglich, Regulatorisch, Budgetär, Unbestimmt |
| Institution category | `payer, provider, professional_body, patient_representation, ministry, regulator, insurer_association, hospital_operator, other` | — |

**Brief sections, in this exact order** (the ordinal is part of the artefact):
`1 question_summary, 2 actors_involved, 3 negotiation_history, 4 conflict_analysis,
5 compromise_proposals, 6 consensus_analysis, 7 open_disputes, 8 impact`.

---

## 5. Screens

For each: what it is for, which endpoints, and the states that must exist
(loading skeleton, empty, error with `code`, degraded, 409/422 inline fix).

### 5.1 `/` — Dashboard
Purpose: pick or start a negotiation. `GET /api/v1/runs` **does not exist** — there is no list endpoint.
Consequence: the dashboard lists runs from a **local index** (`hps.runs.v1`) that records every `run_id` this
browser created (label = the question, timestamp, phase snapshot), and offers a manual "open run by id" field
(`GET /api/v1/runs/{id}` validates it). Show a banner explaining this honestly, linking `DEFERRED.md`.
Widgets: readiness strip (`/readyz`), seeded-corpus card (from `hps.seed.v1`; shows the 5 topics),
recent runs, "Neue Verhandlung" CTA.

### 5.2 `/runs/new` — Open a run
Form → `POST /api/v1/runs` (`OpenRunBody`: `question` 1–4000 chars, `round_cap` 1–50 optional,
`stakeholder_ids` optional, `consensus_threshold` 0< x ≤1 default 0.5). Response `202`
`{run_id, phase, mandate_hash, bound:[{stakeholder_id, institution_name, institution_code, profile_version,
persona_version}]}`.
Behaviours: load `GET /api/v1/stakeholders` for the nine cards (multi-select, default all); live preview of the
turn order; defaults come from Settings; on success go to the console and add the run to the local index.
Show `mandate_hash` truncated with a tooltip (it is the audit anchor).

### 5.3 `/runs/[runId]` — Run console (the demo centrepiece)
Data: `GET /runs/{id}` (state) + `useRunFeed` (events) + `GET /runs/{id}/rounds`.
Layout: three panes — **left**: run header (question, phase stepper, round x/y, closed badge, mandate hash),
**centre**: live event feed (virtualised, newest on top, filter by event type, stakeholder chips),
**right**: current round panel — turn order with per-stakeholder status (position / turn / abstention / silent),
the blocking list when `close` fails, and the action bar.
Actions (each with optimistic pending state, error mapping, and a disabled-with-reason tooltip):
`POST /runs/{id}/rounds` (open next round; 409 `ROUND_STILL_OPEN`, 409 `ROUND_CAP_EXCEEDED` → run closed),
`POST /runs/{id}/rounds/{n}:close` (`{learning:[…], convergence:"none|low|medium|high"}`; 409
`ROUND_CLOSE_GUARD_VIOLATION` with the unaccounted list → render as a checklist of who still needs a turn),
`POST /runs/{id}/abstentions` (`{stakeholder_id, topic}` → 204),
`POST /runs/{id}/turns` (argument form: stakeholder, target `{topic, position_id?, argument_id?}`, stance, text
1–8000, `claims:[{text, claim_id?, verdict?}]`, `evidence_ids`, `unsupported`, `invocation_id`).
If `closed`: replace the action bar with a "Run closed" panel showing the stopping condition
(`{name, fired, parameters}`) and CTAs to Consensus / Brief.

**Run provenance (mandatory).** Every run is either **manual** (positions and turns posted by this UI) or
**automated** (`POST /runs/{id}:start` drove it). Store `driver: "manual" | "automated"` in the local run index
and detect it for runs you did not start: `GET /runs/{id}/usage` with nine distinct `by_stakeholder` entries
whose `invocations >= 1` means automated. Render a badge in the run header and — for automated runs — a
persistent amber banner:

> **Automatisierter Lauf (Platzhalter).** Alle Stellungnahmen werden vom Orchestrator als *Zustimmung*
> gesetzt; Thema ist die gesamte Fragestellung. Zustimmungswerte sagen nichts über die Institutionen aus
> (Backend #423).

Do not soften this. Without the banner, a `support: 1.0` panel reads as evidence that nine real institutions
agree.
Also: `POST /runs/{id}/stakeholders:select` (`{mandate}`) and `POST /runs/{id}/stakeholders:bind`
(`{stakeholder_ids}`) for late binding, in a "Mandat" drawer.

### 5.4 `/runs/[runId]/positions` — Positions, revisions, coalitions
Data: the event log (positions/arguments/revisions) is the source of truth; enrich with
`GET /runs/{id}/conflicts?status=open` and `GET /runs/{id}/coalitions` is **not** exposed — coalitions appear
only via events and `RunResponse.coalition_ids`.
Views: **position board** (topic × stakeholder matrix with stance colour + support/oppose/qualify icons),
**position drawer** (proposal `{summary, components:[{measure, effect, population, cost_eur, quantification,
support_record}]}`, evidence packs, provenance), **revision form**
`POST /runs/{id}/positions/{position_id}:revise` (`{stance, reason:{argument_ids, pack_ids, driver}}`) — a
revision without argument or pack ids is rejected (`PositionRevisionRejected`): enforce it in the form.
`POST /runs/{id}/coalitions` (`{topic, member_ids, proposal}`) for a coalition offer; render offers as a
sankey-free "supporters → proposal" list with status.

### 5.5 `/runs/[runId]/evidence` — Evidence packs
Data: `GET /evidence/packs/{pack_id}` (from the seed), `GET /evidence/packs/{pack_id}/scores`,
`POST /evidence/candidates` (`{claim, claim_type, snapshot_id, limit}`, read-only search),
`POST /evidence/packs` (`{claim, claim_type, snapshot_id}`) to assemble a new frozen pack,
`POST /evidence/packs/{pack_id}/reweight` (`{policy:{half_life_days, exempt_source_types}}`).
Show: candidates with passage text, provenance (outlet, date, medium, pages, offsets), stance label, and the
**score decomposition** `{authority, lexical, semantic, recency, directness, final}`; `trace`
(`embedding_model, reranker_model, query_rewrite, stance_counts, retrieval_mode, index_version`) in a
"Wie wurde gesucht?" popover; and **absence** (`absence: {queries, snapshot_id, reason}`) as a first-class
state — "nichts gefunden" is a finding, not an error.
Caveat to surface: `retrieval_mode` is `lexical+dense` with a hashing encoder (`hashing-char3gram-v1`) — label
semantic similarity as an approximation (D-004).

### 5.6 `/runs/[runId]/consensus` — Consensus & packages
Data: `GET /runs/{id}/consensus` → `{records:[{consensus_id, topic, proposal_class, outcome, support,
threshold, supporters[], minorities:[{holders[], objections[]}], blockers[], reason}]}`;
`POST /runs/{id}/analysis:derive` (`{topics?}`) — 409 `RUN_NOT_CLOSED` on an open run, 200 `{records:[]}` when a
closed run produced no stances (this is a valid outcome, not an error: say "keine Stellungnahmen");
`GET /runs/{id}/conflicts/open`; `POST /runs/{id}/packages` (`{component_ids, rejected_ids}`) and
`GET /runs/{id}/packages`; `POST /packages/{id}/scenarios`
(`{baseline:{label, reference}, horizon:{years, description}, assumptions[]}`);
`GET /packages/{id}/comparison` → `{entries:[{package_id, scenario_id, cost, acceptance, feasibility, rank}]}`.
Emphasis: `veto_blocked` must be visually distinct and explained ("7/9 Zustimmung, aber Klasse
`budget_frame` ist durch `oegk` veto-blockiert"), and minorities are always listed with their objections —
never collapsed.

**If the run is automated, the consensus screen is a placeholder** (backend #423: the orchestration hard-codes
`stance=SUPPORT`, a placeholder proposal and the full question as the topic). Requirements for that case:
- keep the banner from §5.3 visible on this screen too;
- never render "Einigkeit" / "alle einig" / a green checkmark for `support: 1.0` on an automated run — label it
  "Zustimmung (automatisch gesetzt)";
- show an explicit empty state for minorities and blockers: "Automatisierte Läufe erzeugen keine Minderheiten"
  with a link to the manual path (Console → Positionen/Turns);
- `outcome: consensus` gets a "(Platzhalter)" suffix on automated runs, and `veto_blocked` keeps its real
  label because that one is a genuine domain decision.

### 5.7 `/runs/[runId]/brief` — Decision brief
Data: `POST /runs/{id}/brief` (no body) → `BriefResponse`
`{brief_id, run_id, status, version:{…}, sections:[…8, in ordinal order…], rejected_proposals:[{measure,
blocking_stakeholders[], reasons[]}], outcomes:[…], disclaimer:{text, model_reference, prompt_version},
citation_count, schema_version}`; `GET /runs/{id}/briefs` → `{versions:[{brief_id, version, previous_version,
reason, status, generated_at}]}`; `GET /briefs/{brief_id}`; `POST /briefs/{brief_id}:version` (`{reason}`,
409 on conflict); `GET /briefs/{brief_id}/citations` → resolved/unresolved citations with quote + provenance.
Renderer: a document view (A4-ish measure), section numbers 1–8, tabular outcomes, rejected proposals as a
callout, citations as superscripts with a side list; unresolved citation → inline error chip, and publication
refusals (`422 DISCLOSURE_MISSING`, `422 CITATION_RESOLUTION_FAILED`, `422 INCOMPLETE_BRIEF`) shown as a
"Publikation blockiert" panel listing exactly what is missing. Export: print stylesheet + "Copy Markdown" +
JSON download (client-side only).

### 5.8 `/runs/[runId]/usage` — Cost, tokens, job control
Data: `GET /runs/{id}/usage` → `{total_invocations, input_tokens, output_tokens, cost, by_stakeholder:[…],
by_round:[…]}`; `POST /runs/{id}:start` (`{budget:{max_invocations?, max_tokens?, max_cost?}}` — accept a
partial object), `POST /runs/{id}:pause`, `POST /runs/{id}:resume` (both `{action, reason?, budget?}`),
`GET /jobs/{job_id}`.
Show: budget gauges (used/limit for invocations, tokens, EUR), per-stakeholder table, per-round bars, and the
SSE job stream with `run.queued → round.started → turn.started → turn.completed → … → run.completed|
run.budget_exhausted|run.failed` + terminal `run.stream_closed`. When `simulation_pricing` is `zero`, put an
inline warning: "Preise nicht konfiguriert — Kosten werden als 0 gemessen."

### 5.9 `/runs/[runId]/governance` — Guard & compliance
Data: `GET /governance/violations` → `{items:[{violation_id, violation_class, offending_span,
rewritten_span, rule_id, rule_version, detected_at}]}`, `GET /governance/allowlist`,
`POST /governance/check` (`{text, speaker_kind, invocation_id, run_id?, position_id?, cited_passage_ids?,
reference_figure_ids?}`) as an interactive "Text prüfen" tool, `GET /positions/{position_id}/provenance`,
`POST /positions/{position_id}/provenance` (`{version, requested_by}`) for re-disclosure.
Render violations as a diff view (offending → rewritten) with the rule id badge; the check tool must show the
decision (`accept|rewrite|reject`), the matched span, and the rule that fired.

### 5.10 `/stakeholders` — Stakeholder model
Data: `GET /api/v1/stakeholders` → `{items:[{stakeholder_id, identity:{name, short_name, category, code},
interest_count, constraint_count, profile_version}]}`; `POST /api/v1/stakeholders` (full profile),
`PATCH /api/v1/stakeholders/{id}`, `GET/POST /stakeholders/{id}/history`
(`{stance, attribution, stated_on, passage_id}`), `POST /stakeholders/{id}/powers`
(`{power_type, proposal_class?, citation, kind, as_of}`).
Cards: institution identity, mandate scope, budget, veto classes, power sources with citations, historical
positions with attribution strength. A "Profilversion" diff is out of scope; show the version string.

### 5.11 `/claims` — Claim validation
Data: `POST /claims:verify` (`{text, claim_type?, measure?, asserted_value?}`),
`GET /claims/{claim_id}`, `POST /claims/{claim_id}:flag` (`{reason}`), `POST /claims/{claim_id}/reviews`
(`{verdict, basis}`), `GET /contradictions` (`{items:[{finding_id, claim_id_a, claim_id_b, measure, delta}]}`),
`GET/POST /reference-figures` (`{measure:{measure, unit, period, geography}, value, tier, as_of, source_id}`).
An interactive verifier: paste a sentence → verdict with the tolerance band used and the reference figure
cited; a reference-figure table with tier ordering from `GET /corpus/authority-rules`.

### 5.12 `/settings` — Configuration (required, see §7)
### 5.13 `/health` — Readiness & capabilities
Full `/readyz` matrix grouped by context with pass/degraded/absent, `openapi.json` link, and the same
diagnostics export as Settings.

---

## 6. D3 visualisations (exactly these eight)

All charts: hand-rolled SVG with `viewBox`, responsive through a `ResizeObserver` wrapper, no chart library,
no animation on update beyond a 200 ms ease, `prefers-reduced-motion` respected, and every chart paired with an
accessible data table (`<table class="sr-only">` or a disclosure "Daten anzeigen"). Colour always carries a
secondary encoding (shape, pattern, or label) — the jury may be colour-blind.

| # | Chart | Where | Encoding |
|---|---|---|---|
| 1 | **Support vs threshold** (bullet) | consensus records | horizontal bar = support (0–1), vertical rule = threshold, outcome badge; one row per topic |
| 2 | **Stance matrix** | positions board | stakeholders × topics grid, cell = stance symbol + tint; hover reveals proposal summary |
| 3 | **Score decomposition** (stacked) | evidence candidates | 5 components (`authority, lexical, semantic, recency, directness`) as a stack, `final` as a marker line |
| 4 | **Authority vs recency scatter** | evidence | x = published date, y = authority tier (ordered), radius = final score, hover = passage snippet |
| 5 | **Round timeline** | run console | x = sequence within round, y = stakeholder (turn order), segments = position/turn/abstention/revision; blocked list highlighted |
| 6 | **Alignment matrix** | positions / consensus | stakeholder × stakeholder agreement strength, diverging palette, diagonal blanked |
| 7 | **Scenario comparison** | consensus packages | grouped bars: cost (EUR, log-safe formatting) and acceptance (0–1) per package, feasibility as a badge column; rank ordering is data, not sorted client-side |
| 8 | **Usage small multiples** | usage | per-stakeholder tokens and EUR per round, as tiny bars in a grid with a shared scale; plus a budget gauge (linear, not a donut) |

Chart rules: no pie/donut beyond three categories (use bars), no 3D, no gradients as data encoding, no
tooltip-only information (values must be reachable by keyboard), axes labelled in German with units
("EUR", "Tage", "Zustimmung %"), zero baselines on bars.

**Degenerate data must be visible, not smoothed.** Automated runs produce no variance (#423): chart 2 (stance
matrix) is one colour, chart 5 (timeline) has no abstentions/revisions, chart 6 (alignment) is uniformly high.
In that case render the chart greyed with a footnote "Automatisierter Lauf — keine Varianz in den Daten" and do
not let the visual imply measured agreement. Never synthesise variance to make a chart look interesting.

---

## 7. The settings page (`/settings`) — specification

Everything here is **client-side only** and must never contain secrets. Persist in
`localStorage` under `hps.settings.v1`, validate on read with zod, and tolerate schema drift (migrate or
reset). SSR must render a neutral skeleton until hydration (no `localStorage` during render).

**A. Verbindung (connection)**
Read-only: proxy path, `HPS_API_BASE_URL` (as exposed by a tiny `GET /api/hps/_meta` route you add that
returns `{baseUrl, hasApiKey}` — never the key), request timeout. Button "Verbindung testen" → calls
`GET /healthz`, `GET /readyz`, `HEAD /openapi.json`, shows status + latency + backend version if present.
Shows `auth_mode` inferred from a 401/403 probe result ("demo (anonym, localhost)" or "strict (API-Key)").

**B. Demo-Bootstrap (seed)**
Textarea/file picker for `demo-seed.json`; zod-validate
`{document_id, snapshot_id, figure_ids[], pack_ids{csv}, topics[]}`; on save, show a table of the five topics
with pack ids and a copy button. Status line: "Seed geladen am …" / "Kein Seed — Positionen können nicht
angelegt werden", with the exact command:
`LOG_LEVEL=ERROR make -s demo-seed > /tmp/demo-seed.json` (`docs/demo-walkthrough.md`).
Also show `GET /corpus/snapshots/{snapshot_id}` result as verification (snapshot label, manifest hash,
passage count).

**C. Simulationsvorgaben (defaults used by the New Run form)**
`round_cap` (1–50, default 2), `consensus_threshold` (0.5–1.0, default 0.5), default stakeholder selection,
default question template (German), budget `max_invocations` (default 30). Each with the backend constraint in
the hint text.

**D. Darstellung & Sprache**
Language `de-AT` (default) / `en`; theme `paper` (default) / `ink` / `dark` / `system`; density
`comfortable` / `compact`; motion `full` / `reduced`; date/time zone `Europe/Vienna`;
number format `de-AT` / `en-GB`.

**E. Guardrails (read-only, from the backend)**
`GET /governance/allowlist` (9 institutions, canonical names, aliases), `GET /reference-figures` count and the
five seeded measures, `GET /corpus/authority-rules` rendered as an ordered tier table per claim type.
Each block links to the corresponding screen. State clearly: these are the rules the backend enforces; the UI
does not enforce them.

**F. Fähigkeiten (capabilities matrix)**
From `/readyz`: persistence adapters per context, `llm` provider + `llm_model` + `simulation_pricing`,
`attribution`, `evidence_retrieval_mode`, `consensus_analysis_sources`, `decision_brief_gates`,
`governance_provenance_producer`. Render as a table; mark `degraded`/`absent` in amber with the named reason.
If `llm: scripted`, a callout: "Kein Sprachmodell konfiguriert — Antworten sind deterministische Platzhalter."
If `simulation_pricing: zero`: "Preise nicht gesetzt — Kosten werden als 0 gemessen."

**G. Diagnose**
Raw `/readyz` JSON (collapsible, copyable), link to `/openapi.json`, the client's last 20 failed requests
(method, path, status, `code`, `trace_id`, time — kept in a bounded in-memory ring buffer), and
"Diagnose kopieren" which produces a JSON blob (settings minus secrets, readiness, failed requests, user agent).

**H. Zurücksetzen**
Clear settings, clear seed, clear the local run index — each behind a confirm, each stating exactly what is
lost (the backend keeps the data; only this browser forgets).

---

## 8. Design system (Tailwind + tokens, no component kit)

- **Tokens** in `styles/globals.css` via `@theme`: colour roles (`--color-surface`, `--surface-muted`,
  `--ink`, `--ink-muted`, `--line`, `--accent`, `--accent-quiet`, `--ok`, `--warn`, `--danger`,
  `--veto`), a **6-step type scale** (13/14/16/18/24/34 px) with `font-feature-settings: "tnum"` on all
  numerals, spacing on a 4 px grid, radii 2/4/8 px only, two shadows maximum (none in `ink` theme).
- **Typography**: one variable sans for UI (system stack is fine: `ui-sans-serif`, `Inter` if you ship it),
  one serif for the decision brief (the artefact should look like a document), monospace for ids/hashes.
  Numerical columns right-aligned, tabular.
- **Layout**: 12-column grid, max content width 1440 px, left navigation rail 240 px collapsible to 64 px,
  sticky page header with breadcrumb `Run → Runde n → Phase`, right-hand inspector drawer 400 px.
- **Density**: `comfortable` (row height 44 px) and `compact` (32 px) applied through a `data-density`
  attribute on `<html>`.
- **States**: every list has `loading` (skeleton, no spinner), `empty` (sentence + primary action),
  `error` (code + message + retry), `degraded` (amber banner, named reasons), `forbidden` (403).
  A status pill component with 6 variants: `ok, warn, danger, info, neutral, veto`.
- **Never**: gradients as decoration, glassmorphism, drop shadows on text, emoji as icons, pill-shaped
  everything, hero sections, marketing copy, animated counters, icon-only buttons without `aria-label`,
  colour as the only signal.
- **Accessibility**: WCAG 2.2 AA. Contrast ≥ 4.5:1 for text. Visible focus ring (2 px, offset 2 px) on every
  interactive element. All actions keyboard-reachable; the golden demo path must work with `Tab/Enter/Escape`
  only. `aria-live="polite"` for the feed (announce at most one item per 2 s), `role="status"` for saves,
  `aria-describedby` for error text, `lang` switching on the html element. Skip link to main content.
  Dialogs trap focus and restore it. Charts: `role="img"`, `<title>`, `<desc>`, plus the data table.
- **Language**: German microcopy, formal ("Sie"), no exclamation marks, no "Let's". Verbs first on buttons
  ("Runde schließen", not "Schließen").

---

## 9. Data layer rules

- `lib/http.ts`: one `request<T>(path, {schema, method, body, signal})` that builds the URL against the proxy,
  parses JSON, validates with the zod schema, and throws a typed `ApiError {status, code, message, details,
  traceId}`. No component ever calls `fetch` directly.
- One zod schema module per context under `features/<slice>/contracts.ts`, derived by hand from the OpenAPI
  components (do not generate 60 files; write the ~25 you need and mark the rest as `z.unknown()` with a
  comment).
- React Query keys: `['run', id]`, `['run', id, 'events']` (the endpoint has no cursor — poll to a ref, not a
  cache key), `['run', id,
  'rounds']`, `['run', id, 'consensus']`, `['run', id, 'usage']`, `['brief', id]`, `['readyz']`,
  `['stakeholders']`. Invalidate precisely on mutation success.
- Retries: GET only, max 2, exponential 300/900 ms, **never** on 4xx. Mutations: no retry; show the error and
  offer the explicit fix.
- Polling: events 750 ms → 3 s backoff; job 1 s; readiness 30 s; usage 5 s while a job runs.
- Mutations that change a run must reconcile with the returned payload **and** the next poll — never invent
  state locally.
- Cancellation: `AbortController` on unmount and on run change; SSE reader closed in `useEffect` cleanup.

---

## 10. Tests and quality gates

- `pnpm typecheck` clean, `pnpm lint --max-warnings=0` clean, `pnpm build` clean.
- **Vitest**: one test per zod contract (a real fixture per endpoint you use), one per hook with a mocked
  transport (`msw` optional; a hand-written `fetch` double is fine), and ≥3 component tests per screen
  covering empty/error/loaded.
- **Playwright** (one spec, skipped unless `HPS_E2E=1`): open run → round → 9 positions from the seed → 9
  turns → close round → consensus visible → brief published; assert the German labels and that no request
  failed. Document that it needs `make demo-seed` and a running backend.
- **axe**: run on `/`, `/runs/[id]`, `/runs/[id]/brief`, `/settings`; zero violations.
- Forbid `any`, `@ts-ignore`, `eslint-disable` without a one-line justification comment; forbid `dangerouslySetInnerHTML`
  except the print view (and sanitise there).
- Performance: no chart renders > 500 nodes for the matrices (aggregate when above); feed virtualised above 200
  items; fonts subset; no client-side date library (use `Intl`).

---

## 11. Deliverables

1. The full `frontend/` application as laid out in §2, building clean.
2. `frontend/README.md`: prerequisites, env, three commands to run (backend, seed, frontend), the demo script
   (which screen to show in which order), troubleshooting (backend not running, degraded readiness, missing
   seed).
3. `frontend/DEFERRED.md`: every place the UI had to work around the backend, with the reason and the exact
   backend behaviour — at minimum: no run list endpoint, no pack list endpoint, negotiation SSE shadowed
   (#420), **automated runs manufacture unanimity (#423)**, client-declared attribution, scripted LLM,
   `open_position_ids` non-empty after close, no settings API. Use the same shape as `backend/.pi/architecture/DEFERRED.md` (one entry per gap: what is true, what the
   UI does instead, what would remove the gap).
4. A short `docs/DEMO.md` in `frontend/` with the 8-minute script mapped to screens and the exact click path.

**Definition of done**: `pnpm build` passes; the golden path in §11.3 works against the real backend; every
screen has empty/error/loading; `/settings` shows a truthful capabilities matrix; no mock data anywhere; no
network call outside the proxy; and a reviewer who has never seen the project can run the demo from the README
alone.

---

## 12. Anti-goals (if you are about to do one of these, stop)

- Inventing endpoints (`/runs` list, `/packs` list, `/settings` admin API) — they do not exist.
- Hardcoding the nine stakeholders or their fields — read `GET /stakeholders` and the run's `bound[]`.
- Faking a consensus or a brief to make a screenshot look good.
- Client-side secrets, API keys in `localStorage`, or `NEXT_PUBLIC_` for the upstream URL.
- A login screen: `AUTH_MODE=demo` is the demo posture; `strict` keys live on the server.
- Chart libraries, component kits, or an i18n framework.
- Silent failure: every error must name the backend `code` and the fix.
- Building a marketing landing page: this is an instrument panel.
- Touching `backend/`.

---

## Appendix A — Endpoint inventory (authoritative: `/openapi.json`)

All under `/api/v1` unless noted. `→` shows the request body; response shapes are in Appendix B / OpenAPI.

**Runs & rounds (NegotiationSession)**
```
POST   /runs                              → OpenRunBody {question, round_cap?, stakeholder_ids?, consensus_threshold}   202
GET    /runs/{run_id}                                                                                                200
GET    /runs/{run_id}/events              ?until_round              → {items[{sequence,event_type,payload,occurred_at}], state}  200
GET    /runs/{run_id}/negotiation/stream  SSE domain events (RoundOpened … SimulationRunClosed), Last-Event-ID       200
GET    /runs/{run_id}/stream              SSE job progress (run.queued … run.stream_closed)                         200
POST   /runs/{run_id}/rounds              → OpenRoundBody? {round?}                                                    201
POST   /runs/{run_id}/rounds/{n}:close    → CloseRoundBody {learning[], convergence}                                  200
GET    /runs/{run_id}/rounds                                                                                         200
POST   /runs/{run_id}/positions           → PositionBody {stakeholder_id, topic, stance, proposal, evidence_ids[]}      201
POST   /runs/{run_id}/positions/{id}:revise → ReviseBody {stance, reason{argument_ids,pack_ids,driver}}                200
POST   /runs/{run_id}/turns               → TurnBody {stakeholder_id, target{topic,position_id?,argument_id?}, stance,
                                              text, claims[{text,claim_id?,verdict?}], evidence_ids[], unsupported, invocation_id}  201
POST   /runs/{run_id}/abstentions         → {stakeholder_id, topic}                                                   204
GET    /runs/{run_id}/conflicts           ?status=open|resolved|deadlocked                                            200
POST   /runs/{run_id}/coalitions          → {topic, member_ids[], proposal}                                           201
GET    /runs/{run_id}/learning                                                                                       200
POST   /runs/{run_id}/stakeholders:select → {mandate}                                                                200
POST   /runs/{run_id}/stakeholders:bind   → {stakeholder_ids[]}                                                       200
```

**Consensus**
```
GET    /runs/{run_id}/consensus             → {records[{consensus_id, topic, proposal_class, outcome, support,
                                                threshold, supporters[], minorities[{holders,objections}], blockers[], reason}]}  200
POST   /runs/{run_id}/analysis:derive       → {topics?}        200 | 409 RUN_NOT_CLOSED
GET    /runs/{run_id}/conflicts/open
POST   /runs/{run_id}/packages              → {component_ids[], rejected_ids[]}    201
GET    /runs/{run_id}/packages              → {packages[{package_id, state, component_count, rejected_count}]}
POST   /packages/{package_id}/scenarios     → {baseline{label,reference}, horizon{years,description}, assumptions[]}  201
GET    /packages/{package_id}/comparison    → {entries[{package_id, scenario_id, cost, acceptance, feasibility, rank}]}
```

**Decision brief**
```
POST   /runs/{run_id}/brief        (no body) → BriefResponse     201
GET    /runs/{run_id}/briefs       → {run_id, versions[{brief_id, version, previous_version, reason, status, generated_at}]}
GET    /briefs/{brief_id}          → BriefResponse
POST   /briefs/{brief_id}:version  → {reason}    201 | 409
GET    /briefs/{brief_id}/citations → [{passage_id, resolved, quote, outlet, published_on, medium, page_from, page_to, source_uri}]
```

**Evidence corpus & retrieval**
```
POST   /corpus/documents           → {source_uri, publication{outlet,published_on,medium}, source_type}   202
POST   /corpus/ingestion-runs      → {shard_label, paths[]}       202
GET    /corpus/ingestion-runs/{id}
GET    /corpus/snapshots/{snapshot_id}
POST   /corpus/snapshots           → {label, document_ids?}       201
GET    /corpus/authority-rules     → [{claim_type, ordered_tiers[]}]
GET    /documents/{document_id}    GET /passages/{passage_id}
POST   /evidence/candidates        → {claim, claim_type, snapshot_id, limit}    200
POST   /evidence/packs             → {claim, claim_type, snapshot_id}           201
GET    /evidence/packs/{pack_id}
GET    /evidence/packs/{pack_id}/scores
POST   /evidence/packs/{pack_id}/reweight → {policy{half_life_days, exempt_source_types[]}}   201
```

**Stakeholders**
```
GET    /stakeholders                       → {items[{stakeholder_id, identity{name,short_name,category,code},
                                               interest_count, constraint_count, profile_version}]}
POST   /stakeholders                       → RegisterStakeholderBody (full profile)   201
PATCH  /stakeholders/{stakeholder_id}      → UpdateProfileBody                        200
GET    /stakeholders/{id}/history
POST   /stakeholders/{id}/history          → {stance, attribution, stated_on, passage_id}   201
POST   /stakeholders/{id}/powers           → {power_type, proposal_class?, citation, kind, as_of}   200
```

**Claim validation**
```
POST   /claims:verify                → {text, claim_type?, measure{measure,unit,period,geography}?, asserted_value?}  200
GET    /claims/{claim_id}
POST   /claims/{claim_id}:flag       → {reason}        200
POST   /claims/{claim_id}/reviews    → {verdict, basis} 200
GET    /contradictions               → {items[{finding_id, claim_id_a, claim_id_b, measure, delta}]}
GET    /reference-figures            → {items[{figure_id, measure, unit, period, geography, value, tier, as_of, source_id}]}
POST   /reference-figures            → ReferenceFigureBody   201
```

**Governance**
```
POST   /governance/check                 → {text, speaker_kind, invocation_id, run_id?, position_id?,
                                            cited_passage_ids[], reference_figure_ids[]}   200
GET    /governance/violations            → {items[{violation_id, violation_class, offending_span, rewritten_span,
                                            rule_id, rule_version, detected_at}]}
GET    /governance/allowlist             → {institutions[{code, canonical_name, short_name, category, aliases}]}
GET    /positions/{position_id}/provenance
POST   /positions/{position_id}/provenance → {version?, requested_by?}   201
```

**Simulation orchestration & identity**
```
POST   /runs/{run_id}:start    → {budget?{max_invocations?, max_tokens?, max_cost?}}   202
POST   /runs/{run_id}:pause    → {action, reason?, budget?}                           202
POST   /runs/{run_id}:resume   → {action, reason?, budget?}                           202
GET    /runs/{run_id}/stream   SSE progress (see §3.3)
GET    /runs/{run_id}/usage    → {total_invocations, input_tokens, output_tokens, cost,
                                   by_stakeholder[{stakeholder,invocations,input_tokens,output_tokens,cost}],
                                   by_round[{round,…}]}
GET    /jobs/{job_id}          → {job_id, run_id, status, attempts, checkpoint{run_id,round,phase,next_actor,
                                   budget_used_invocations,budget_used_tokens,budget_used_cost}, error, progress_sequence}
GET    /admin/keys | POST /admin/keys | DELETE /admin/keys/{key_id}
```

**Platform (not under /api/v1)**: `GET /healthz`, `GET /readyz`, `GET /metrics`.

---

## Appendix B — Real payload samples (from a live run)

```jsonc
// GET /api/v1/runs/{run_id}
{"run_id":"run_01M6Q…","phase":"position_formation","round":1,"round_cap":2,"closed":false,
 "bound_stakeholder_ids":["stk_aerztekammer","stk_apothekerkammer","stk_bmsgpk","stk_krankenhausgesellschaft",
  "stk_landesgesundheitsfonds","stk_oegk","stk_patientenanwaltschaft","stk_privatkrankenanstalten",
  "stk_sozialversicherung"],"open_position_ids":["pos_01M6Q…"],"coalition_ids":[]}

// GET /api/v1/runs/{run_id}/rounds
{"items":[{"round":1,"closed":true,"argument_count":9,"abstention_count":0,
           "learning":{"learning_id":"lrn_run_…_1","run_id":"run_…","round":1,"insights":[…]}}]}

// GET /api/v1/runs/{run_id}/events?limit=3
{"items":[{"sequence":1,"event_type":"SimulationRunOpened","payload":{…},"occurred_at":"2026-11-06T06:23:11.412Z"},
          {"sequence":2,"event_type":"RoundOpened","payload":{"run_id":"run_…","round":1,
           "turn_order":["stk_aerztekammer",…],"phase":"position_formation"},"occurred_at":null}],
 "state":{"run_id":"run_…","phase":"debate","round":1,"round_cap":1,"closed":true,
          "bound_stakeholder_ids":[…],"open_position_ids":[…],"coalition_ids":[]}}

// GET /api/v1/runs/{run_id}/consensus
{"records":[{"consensus_id":"cns_01M6Q…","run_id":"run_…","topic":"cost_control","proposal_class":"other",
             "outcome":"consensus","support":1.0,"threshold":0.5,
             "supporters":["stk_aerztekammer",…],"minorities":[],"blockers":[],"reason":null}]}

// GET /api/v1/runs/{run_id}/usage
{"run_id":"run_…","total_invocations":9,"input_tokens":1107,"output_tokens":405,"cost":"1.161000",
 "by_stakeholder":[{"stakeholder":"stk_aerztekammer","invocations":1,"input_tokens":123,
                    "output_tokens":45,"cost":"0.129"}],
 "by_round":[{"round":0,"invocations":9,"input_tokens":1107,"output_tokens":405,"cost":"1.161000"}]}

// POST /api/v1/runs/{run_id}/brief  (201)
{"brief_id":"brf_01M6Q…","run_id":"run_…","status":"published",
 "version":{"number":1,"run_id":"run_…","snapshot_ref":"mandate:9fb7fbad…", …},
 "sections":[{"kind":"question_summary","ordinal":1,"title":"Fragestellung","body":"…"}, …8],
 "rejected_proposals":[{"measure":"…","blocking_stakeholders":["stk_oegk"],"reasons":["…"]}],
 "outcomes":[…],"disclaimer":{"text":"Simulation, keine Entscheidung.","model_reference":"scripted-local",
 "prompt_version":"brief@1"},"citation_count":5,"schema_version":"1"}

// POST /api/v1/runs   202
{"run_id":"run_…","phase":"position_formation","mandate_hash":"sha256:9fb7…",
 "bound":[{"stakeholder_id":"stk_aerztekammer","institution_name":"Österreichische Ärztekammer",
           "institution_code":"aerztekammer","profile_version":"2026.1","persona_version":"2026.1"}, …9]}

// error envelope (409/422/503)
{"code":"ROUND_CLOSE_GUARD_VIOLATION","message":"round 1 cannot close; unaccounted: stk_oegk, stk_bmsgpk",
 "details":[],"trace_id":"req_01M6Q…"}
```

---

## Appendix C — Golden path (verify your build against this)

```
POST /api/v1/runs {question:"Kassenstellen aufstocken?", round_cap:2}      → 202 run_id, 9 bound
POST /api/v1/runs/{id}:start {}                                             → 202 job_id (needs a seeded corpus;
                                                                                without it the job ends dead_letter with a
                                                                                named reason — show it, do not hide it)
   or, manually:
POST /api/v1/runs/{id}/rounds                                               → 201 round 1, turn_order[9]
POST /api/v1/runs/{id}/positions ×9   {evidence_ids:[seed.pack_ids.kassenstellen]}  → 201 each
POST /api/v1/runs/{id}/turns ×9       {invocation_id:"inv_demo_1"…}         → 201 each
POST /api/v1/runs/{id}/rounds/1:close {learning:[], convergence:"none"}     → 200 stopping_condition
GET  /api/v1/runs/{id}                                                      → closed:true
GET  /api/v1/runs/{id}/consensus                                            → records[…]  (subscriber derived them)
POST /api/v1/runs/{id}/brief                                                → 201 brief_id
GET  /api/v1/runs/{id}/briefs                                               → 1 version
```

Common refusals you must render as guidance, not errors:
`422 ARGUMENT_WITHOUT_EVIDENCE` → pick a pack; `409 ROUND_CLOSE_GUARD_VIOLATION` → the unaccounted list;
`409 RUN_NOT_CLOSED` → close the round first; `422 CLAIM_VERDICT_REJECTED` → the claim verdict was `ambiguous`
(register a reference figure, or send the claim without a `verdict`); `409 ROUND_STILL_OPEN` →
`ROUND_CAP_EXCEEDED` closes the run instead; `503 CONSENSUS_ANALYSIS_UNAVAILABLE` → a dependency is missing,
show `/readyz`.

---

## Appendix D — Known backend limitations the UI must design around

| Limitation | UI consequence |
|---|---|
| No `GET /runs` list endpoint | local run index in `localStorage` + "open by id"; banner explains it |
| No `GET /evidence/packs` list | seed import in `/settings`; disable position creation without it |
| Negotiation SSE shadowed by job SSE (#420) | poll `/events`; one interface so it can switch |
| `llm: scripted` by default (#416 closed, provider optional) | label arguments as scripted when `llm == "scripted"` |
| `attribution: client-declared` | show the invocation id as client-supplied; never claim issuance |
| `simulation_pricing: zero` allowed | show cost 0 with an explicit "unpriced" warning |
| **Automated runs are uniform** (#423): `stance=SUPPORT` for every position and argument, placeholder proposal, topic = the full question, empty round learning → `support: 1.0`, no minorities | badge every run `manual`/`automated`; banner on automated runs; "(Platzhalter)" suffix on consensus; degenerate charts greyed with a footnote; never claim unanimity |
| `open_position_ids` stays populated after close | label the field "Positionen (zuletzt offen)" and do not infer mutability |
| `GET /positions/{id}/provenance` 404 until disclosed | treat 404 as "noch nicht offengelegt", offer the disclose action |
| Integration tests wipe the demo DB (#421) | README: re-run `make demo-seed` after any backend test run |
| Everything is Austrian German domain vocabulary | keep enum labels in the dictionary, never inline |
