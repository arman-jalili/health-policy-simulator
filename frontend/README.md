# HealthPolicy Simulator — Frontend

Instrument panel for the multi-agent negotiation simulator for Austrian healthcare policy.
Nine institutional stakeholders negotiate a policy question; the UI makes the mandate, rounds,
evidenced positions, consensus, dissent, guards, cost and the eight-section decision brief legible
without a narrator.

Next.js App Router · TypeScript strict · Tailwind CSS v4 · zod · TanStack Query v5 · D3 (subpackages only).

## Prerequisites

- Node 22+ (developed on Node 25)
- pnpm 10+
- The backend in `../backend/` with PostgreSQL (Docker Compose)
- `make demo-seed` for evidence packs

## 1. Start the backend

```bash
cd ../backend
cp .env.example .env
docker compose up -d db
uv sync
uv run alembic upgrade head
uv run hps-api            # http://127.0.0.1:8000
```

Verify: `curl -s localhost:8000/healthz` and `curl -s localhost:8000/readyz`.

`AUTH_MODE=demo` (the documented local default) allows loopback traffic anonymously. The Next
proxy calls the backend from `127.0.0.1`, so **CORS is never needed** and no key reaches the browser.

## 2. Seed the demo corpus once

```bash
cd ../backend
LOG_LEVEL=ERROR make -s demo-seed > /tmp/demo-seed.json
```

Import `/tmp/demo-seed.json` in **Einstellungen → Demo-Bootstrap (Seed)**. The five evidence pack
ids then appear in every position/turn picker. Re-run the seed after any backend test run — the
integration suite can wipe the demo database (D-FE-017).

## 3. Start the frontend

```bash
cd frontend
cp .env.example .env.local
pnpm install
pnpm dev                  # http://127.0.0.1:3000
```

`.env.example`:

```dotenv
HPS_API_BASE_URL=http://127.0.0.1:8000
HPS_API_KEY=              # only for AUTH_MODE=strict; server-side
```

The browser only talks to `/api/hps/*`. The route handler injects the key server-side and streams
SSE responses without buffering.

## Gates

```bash
pnpm typecheck
pnpm lint                 # eslint . --max-warnings=0
pnpm test                 # vitest (contracts, hooks, components, axe)
pnpm build
```

Playwright is opt-in:

```bash
HPS_E2E=1 pnpm e2e        # needs the backend, the seed, and `pnpm dev` on port 3000
HPS_E2E=1 HPS_E2E_RUN_ID=run_… pnpm e2e  # also runs axe on console, consensus and brief
```

## Demo

The 8-minute click path is in [`docs/DEMO.md`](docs/DEMO.md). Short form:

1. **Übersicht** — readiness, `llm: scripted`, `attribution: client-declared`, seeded topics.
2. **Neue Verhandlung** — question, round cap, nine institutions, mandate hash.
3. **Konsole** — open a round, take nine evidenced turns, close the round; the feed is polled
   from `/runs/{id}/events`, the right panel shows the turn order and the blocking list.
4. **Positionen** — stance matrix, alignment matrix, revisions with a required cause, coalitions.
5. **Evidenz** — pack candidates, score decomposition, authority/recency, the retrieval trace and
   an honest “nichts gefunden” state.
6. **Konsens** — support vs threshold, veto-blocked outcomes, minorities with objections, packages
   and the scenario comparison.
7. **Entscheidungsbrief** — eight sections, resolved citations, rejected proposals, print/Markdown/JSON.
8. **Kosten & Steuerung** — job stream, pause/resume, tokens and EUR; **Governance** — guard diff,
   allowlist and provenance.

## Troubleshooting

| Symptom | Cause / fix |
|---|---|
| `Dienst nicht erreichbar` banner | Backend down or `HPS_API_BASE_URL` wrong. The proxy returns `503 PROXY_UPSTREAM_UNREACHABLE`. |
| `/readyz` says `degraded` | The banner names the failing checks. Start the DB (`docker compose up -d db`) and re-check `/health`. |
| Positions cannot be created | No seed in this browser. Run the seed command and import it in Settings. |
| Costs are `0,00 €` | `simulation_pricing: zero` — the backend has no price table. The UI says so. |
| Answers look like echoes | `llm: scripted` — no model is configured. The UI says so. |
| “Verhandlung nicht gefunden” for a known id | Runs are not listed by the backend; use **Verhandlung per Kennung öffnen** and check the id. |
| Empty dashboard after a browser reset | The run list is local (`hps.runs.v1`); the backend still has the runs. Open by id. |

## Architecture notes

- `lib/http.ts` is the only transport. It validates every response with zod and throws
  `ApiError { status, code, message, details, traceId }`.
- `features/<slice>/contracts.ts` holds hand-written zod schemas derived from the live
  `openapi.json`; `api.ts` and `hooks.ts` sit beside them.
- `features/run/hooks.ts → useRunFeed` polls the event log (750 ms → 3 s idle backoff, stop on
  close). It is the single place to swap in a future negotiation SSE endpoint.
- All copy lives in `lib/i18n.ts` (de-AT primary, en secondary). All enums are localized there.
- Client-only state: `hps.settings.v1`, `hps.seed.v1`, `hps.runs.v1`.
- `lib/deferred.ts` mirrors [`DEFERRED.md`](DEFERRED.md) and is rendered at `/deferred`.
- `instant = false` on the run routes allows the dynamic console to hydrate without a Suspense
  bailout; the app shell itself is wrapped in Suspense.

### Tooling deviation

The brief names Next.js 15. The repository was scaffolded on **Next.js 16.4.5** (App Router,
Turbopack, Cache Components) with Tailwind v4 and pnpm. Nothing in the product depends on a
Next 15-only API; the Next-16-specific behaviours handled here are Cache Components (no
`runtime`/`dynamic` route config; `instant = false` on run routes) and the React Compiler lint.
