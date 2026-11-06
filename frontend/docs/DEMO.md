# Demo — eight minutes, screen by screen

Prerequisite: backend on `127.0.0.1:8000`, seed imported (`/tmp/demo-seed.json`), frontend on
`127.0.0.1:3000`. The whole path works with Tab/Enter/Escape.

---

## 0:00 — Übersicht (`/`)

1. Point at the readiness strip: **Bereit**, `attribution: client-declared`, `llm: scripted`,
   `pricing: zero`. Say plainly: the demo runs without a language model and with client-supplied
   invocation ids — both are reported by the service, not hidden by the UI.
2. **Demo-Korpus** card shows the five topics and pack ids. If it is missing, the exact seed
   command is on screen; do not improvise.
3. Read the local-index note: the backend has no run list; this browser remembers its runs.

**Proof:** honest posture, seeded evidence, no invented data.

---

## 1:00 — Neue Verhandlung (`/runs/new`)

1. Keep the default question (waiting times −20 % in five years, spending +≤5 %).
2. Round cap **2**, threshold **0.5**.
3. Leave all nine institutions selected; the right side previews the turn order.
4. **Verhandlung eröffnen**.

The toast shows the truncated `mandate_hash`; the console header keeps it with a title tooltip.

**Proof:** the mandate is an audit anchor; nine institutions are bound.

---

## 2:00 — Konsole (`/runs/[runId]`)

1. **Runde öffnen**. The right panel shows the turn order; every row is “Offen”.
2. **Wort ergreifen** for Ärztekammer:
   - stance **Zustimmung**,
   - text: “Das ASVG regelt die Kassenstellen und die Finanzierung.”,
   - evidence pack **kassenstellen**,
   - claims optional; the invocation id is visible and labelled client-declared,
   - **Argument senden**.
3. Repeat for the remaining eight institutions. Each send closes the drawer and the feed grows.
   Use **Enthaltung erfassen** instead for one institution if time is short — the round still closes.
4. Try **Runde schließen** before all nine are accounted for: the error is a product state
   (`ROUND_CLOSE_GUARD_VIOLATION`) and the panel lists exactly who is missing.
5. Close the round. The toast confirms; the event feed shows `Runde geschlossen`.

**Proof:** turn discipline, evidenced arguments, explicit unsupported path, blocking list.

---

## 4:00 — Positionen (`/runs/[runId]/positions`)

1. **Positionstafel**: topic × institution, cell symbol and tint. Hover a cell for stance and
   position id.
2. **Übereinstimmung**: stakeholder × stakeholder agreement strength; the diagonal is blank.
3. **Prüfen** on a position opens the inspector:
   - position id, initial and current stance, evidence ids;
   - the explicit note that proposal text is not in the event payload;
   - **Herkunft**: if 404, the UI says “noch nicht offengelegt” and offers the disclose action.
4. **Position revidieren** with a stance, one argument id and a reason. A revision without an
   argument or pack id cannot be submitted — the form enforces the domain rule.

**Proof:** stances, revision lineage, provenance honesty, no fabricated proposal text.

---

## 5:00 — Evidenz (`/runs/[runId]/evidence`)

1. Pack `kassenstellen`. The claim is shown; `retrieval_mode` and the index version are visible.
2. **Bewertung**: stacked components (authority, lexical, semantic, recency, directness) with the
   final score marker; the legend names every component.
3. **Autorität**: date × numeric authority, radius = final score; hover shows outlet/date/snippet.
4. Expand **Wie wurde gesucht?** — embedding model (`hashing-char3gram-v1`), reranker, rewrite,
   stance counts, index version. Say: semantic is an approximation (D-004), not a neural embedding.
5. If a pack reports `absence`, show it: “nichts gefunden” is a finding, not an error.

**Proof:** score decomposition, provenance, honest absence, no overclaiming.

---

## 6:00 — Konsens (`/runs/[runId]/consensus`)

1. If records are empty, **Konsens ableiten** (the close already subscribes, so this is usually
   already populated).
2. Support-vs-threshold bullets: bar = support, dashed rule = threshold, outcome label at the right.
3. A `veto_blocked` row is visually distinct and explained: support, proposal class, blockers.
4. Minorities are always expanded with their objections — never collapsed.
5. Open conflicts table: topic, institution, stance, weight, recorded.
6. Packages: show the compose form and the honest 503/`CONSENSUS_ANALYSIS_UNAVAILABLE` when the
   component catalogue is not published. Select a package, assess a scenario with an
   `assumed` basis, then show the comparison chart with rank order preserved from the data.

**Proof:** consensus is not assumed; vetoes and minorities are first-class.

---

## 7:00 — Entscheidungsbrief (`/runs/[runId]/brief`)

1. **Brief publizieren**. If the service refuses, the “Publikation blockiert” panel names the code
   (`DISCLOSURE_MISSING`, `CITATION_RESOLUTION_FAILED`, `INCOMPLETE_BRIEF`) and the missing items.
2. The document shows eight sections in ordinal order. Each statement has an evidence status and
   superscript citation numbers; unresolved citations are red.
3. Outcomes table, rejected proposals callout, disclaimer with model and prompt version.
4. **Belege** side list: resolved state, quote, outlet, date, medium, pages, passage id, source URI.
5. Export: **Drucken** (print stylesheet), **Markdown kopieren**, **JSON herunterladen**.
6. Version form: add a reason and create version N+1; the list keeps the lineage.

**Proof:** the eight-section artefact, resolved citations, rejected proposals, export.

---

## 8:00 — Kosten & Steuerung (`/runs/[runId]/usage`) and Governance

1. Start a run with a budget (max invocations 30). The job card polls `GET /jobs/{id}` every second;
   the SSE panel shows `run.queued → turn.started → turn.completed → …` and the terminal close.
2. Budget gauges are linear; tokens and EUR are tabular. The zero-price warning is explicit.
3. **Pause** and **Fortsetzen** return 202 and update the job status.
4. Governance: run **Text prüfen** with “Dr. Kurz sagte, die Kassenstellen seien sicher.” and
   speaker kind *Person* — the guard rewrites the person span (`GC-001`) or rejects a personal
   quotation (`GC-002`). Show the rule badge and the rewritten text.
5. Allowlist and provenance lookup close the loop.

**Proof:** cost control, live progress, deterministic guards, auditable provenance.
