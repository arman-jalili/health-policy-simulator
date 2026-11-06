# Deferred Work — Frontend

> Gaps between the prompt/UI and the real backend contract. Each entry records **what is true**,
> **what the UI does instead**, and **what would remove the gap** — the same shape as
> `backend/.pi/architecture/DEFERRED.md`.
>
> Contract source of truth: the live `openapi.json` generated from `backend/src/shared/app.py`
> (63 paths). Where the build specification and OpenAPI disagreed, **OpenAPI won**.

The same list is rendered at `/deferred` from `lib/deferred.ts`.

---

## D-FE-001 — No endpoint listing all runs

**What is true:** `GET /api/v1/runs` does not exist. The only read operation is `GET /api/v1/runs/{run_id}`.

**UI instead:** the dashboard keeps a local index in `localStorage` (`hps.runs.v1`) and offers
“Verhandlung per Kennung öffnen”, which validates the id against `GET /runs/{id}`.

**Removal:** a paginated `GET /api/v1/runs` with question, phase, round and timestamp.

---

## D-FE-002 — No endpoint listing evidence packs

**What is true:** positions require `evidence_ids`, but `GET /api/v1/evidence/packs` has no list form.

**UI instead:** Settings imports the output of `LOG_LEVEL=ERROR make -s demo-seed > /tmp/demo-seed.json`;
the five pack ids are shown by topic and feed every picker.

**Removal:** `GET /api/v1/evidence/packs?snapshot_id=…`, or one pack per topic in the run context.

---

## D-FE-004 — Events endpoint has no `cursor` / `limit`

**What is true:** per OpenAPI, `GET /runs/{id}/events` accepts only `until_round`.
The `cursor` and `limit` parameters assumed by the build specification do not exist.

**UI instead:** the console fetches the full event log and sorts client-side by `sequence`; the feed
renders 120 items at a time and can reveal more.

**Removal:** keyset pagination by `sequence`.

---

## D-FE-005 — Brief sections carry `statements`, not `title`/`body`

**What is true:** `BriefSectionBody = {kind, ordinal, statements[]}`. The `{title, body}` shape in
The build specification's Appendix B does not exist. `schema_version` is `"1.0"`, not `"1"`.

**UI instead:** each `CitedStatement` is rendered with its evidence status and citation numbers;
the section heading comes from the localized `kind`.

**Removal:** correct the prompt, or add `title`/`body` additively.

---

## D-FE-006 — Candidates carry neither passage text nor an authority tier

**What is true:** `CandidateBody = {passage_id, stance, score, provenance}`. There is no `text`
and no `tier`.

**UI instead:** the evidence page fetches `GET /passages/{id}` once per candidate (bounded by the
pack size) and the scatter plot's y-axis shows the numeric `score.authority`; the axis label says so.

**Removal:** include `text` and `tier` in `CandidateBody`, or offer a batch passage endpoint.

---

## D-FE-007 — Usage has no stakeholder × round cross-tab

**What is true:** `GET /runs/{id}/usage` returns `by_stakeholder[]` and `by_round[]` separately.

**UI instead:** two small-multiple grids with a shared token scale plus a linear budget gauge;
no client-side fabrication of a cross-tab.

**Removal:** `by_stakeholder_round[{stakeholder, round, …}]`.

---

## D-FE-008 — Institutions are only exposed as summaries

**What is true:** `GET /stakeholders` returns identity, interest/constraint counts and
`profile_version`. There is no `GET /stakeholders/{id}` for mandate scope, budget, veto rights or
power sources.

**UI instead:** the institutions page shows the summary, the historical positions
(`GET /stakeholders/{id}/history`), the power-source check (`POST /powers`) and a visible note
naming the missing profile detail.

**Removal:** a read endpoint for the full stakeholder profile, or embed it in the summary.

---

## D-FE-009 — No coalition list endpoint

**What is true:** coalitions can be created (`POST /runs/{id}/coalitions`), but there is no
`GET /runs/{id}/coalitions`.

**UI instead:** coalitions and their proposals are derived from `CoalitionFormed` events.

**Removal:** a read endpoint with members, proposal and offer status.

---

## D-FE-010 — No position or argument lists; events carry no text

**What is true:** positions and arguments have no read endpoints. `InitialPositionStated` and
`ArgumentSubmitted` payloads carry ids, stance, topic and evidence ids — not proposal or argument text.

**UI instead:** the positions page derives stances/revisions from the event log, renders the stance
and alignment matrices, and explicitly states that proposal and argument text are unavailable.

**Removal:** `GET /runs/{id}/positions` and `/arguments` with text, or text fields in the events.

---

## D-FE-011 — RunResponse has no question

**What is true:** `GET /runs/{id}` returns phase, round, cap, bindings and ids — not the policy question.

**UI instead:** the question comes from the local run index; opening a run by id shows an explicit
“nicht lokal gespeichert” line.

**Removal:** add `question` to `RunResponse`.

---

## D-FE-012 — Attribution is client-declared

**What is true:** `POST /runs/{id}/turns` checks that `invocation_id` is non-blank, not that it was
issued by the orchestrator (backend W8). `/readyz` reports `attribution: client-declared`.

**UI instead:** the turn drawer auto-fills `inv_<run>_<round>_<stakeholder>_<n>` and labels it
“Attribution (client-declared)”; arguments created by `POST /runs/{id}:start` show the worker's
real invocation ids read-only.

**Removal:** a run-scoped invocation lookup in SimulationOrchestration.

---

## D-FE-013 — Default LLM is `scripted`

**What is true:** without `LLM_PROVIDER=openai-compatible` the service returns deterministic
placeholders. `/readyz` reports `llm: scripted`.

**UI instead:** the dashboard, Settings and the capabilities matrix show `llm: scripted` and a
callout: “Kein Sprachmodell konfiguriert — Antworten sind deterministische Platzhalter.”

**Removal:** configure a provider in the deployment (no UI code change).

---

## D-FE-014 — Prices may be zero

**What is true:** `SIMULATION_ALLOW_ZERO_PRICE=true` (the default) permits a run without a price
table; cost is metered as `0`.

**UI instead:** the usage page and Settings show “Preise nicht konfiguriert — Kosten werden als 0
gemessen.” The EUR values remain tabular and decimal-string based.

**Removal:** `SIMULATION_ALLOW_ZERO_PRICE=false` with a price table.

---

## D-FE-015 — `open_position_ids` stays populated after close

**What is true:** the field is a last-known snapshot, not a statement about mutability.

**UI instead:** the UI never infers writability from it; closure comes from `closed` and the phase
stepper. The field is labelled “Positionen (zuletzt offen)” where shown.

**Removal:** clear it on close, or split into open/closed positions.

---

## D-FE-016 — Provenance returns 404 until disclosed

**What is true:** `GET /positions/{id}/provenance` answers 404 until a disclosure row exists.

**UI instead:** 404 is rendered as “noch nicht offengelegt” with an explicit disclose action; no
fabricated provenance is shown.

**Removal:** a 200 with an absence object, or automatic disclosure on close.

---

## D-FE-017 — Integration tests wipe the demo database (#421)

**What is true:** a backend integration test run can remove the seeded corpus.

**UI instead:** the README and Settings repeat the seed command; a missing pack shows the command
inline instead of a silent empty picker.

**Removal:** a separate test schema, or an idempotent seed in the test lifecycle.

---

## D-FE-018 — Event names differ from the prompt

**What is true:** the backend emits `ConflictTopicOpened`, `CoalitionOffered`,
`CoalitionOfferDeclined`, `LearningApplied`, etc. The prompt's `ConflictOpened`, `ConflictResolved`,
`CoalitionOfferMade` and `ArgumentRejected` do not exist.

**UI instead:** known event names are localized; unknown names render unchanged; every payload is
available in an expandable raw JSON block.

**Removal:** align the prompt with the domain vocabulary.

---

## D-FE-019 — Resume requires an `action` field

**What is true:** `POST /runs/{id}:resume` uses `PauseResumeBody`, whose `action` is required even
though the handler overrides it with `RESUME`.

**UI instead:** the UI sends `action: "resume"`.

**Removal:** a dedicated resume body without `action`.

---

## D-FE-020 — History read requires `usable_only`

**What is true:** `GET /stakeholders/{id}/history` has `usable_only` as a required query parameter
without a default.

**UI instead:** the UI always sends `true` or `false`, toggled by a checkbox.

**Removal:** set a default in the endpoint.

---

## Accepted UI limitations (not backend defects)

- The browser run index is per-browser and capped at 50 entries; clearing site data forgets it.
- The feed bounds rendered nodes (120 per page, `content-visibility: auto`); it is not a full
  virtual list.
- The stance and alignment matrices aggregate above 9 institutions × topics rather than paginating.
- Export is client-side only: print stylesheet, copied Markdown, downloaded JSON. No server-side
  PDF or DOCX renderer exists.
- Institution registration (`POST /stakeholders`) and profile update (`PATCH /stakeholders/{id}`)
  are not exposed as forms. The institutions screen focuses on the readable model (summary,
  history, power-source check) because the list endpoint cannot return the full profile it would
  then have to display. Use the API/OpenAPI for those writes.
