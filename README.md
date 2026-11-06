# Demo stack — `docker compose`

Everything the jury sees, in three containers: PostgreSQL (pgvector), the FastAPI backend, and the
Next.js frontend that proxies the API server-side.

```
docker compose up --build        # first run: builds both images
open http://localhost:3000       # the only URL you need
```

| Service | Port | What it is |
|---|---|---|
| `frontend` | 3000 | Next.js (standalone). Serves the UI and proxies `/api/hps/*` → `backend:8000` |
| `backend` | not published | FastAPI + Alembic. Reach it through the frontend proxy, or uncomment `ports:` for `/docs` |
| `db` | not published | PostgreSQL 16 + pgvector, volume `hps-demo-pgdata` |

The browser never talks to the backend and never sees a key: the proxy holds `HPS_API_KEY` server-side.

## 1. First run

```bash
docker compose up --build -d
docker compose ps                      # all three healthy
curl -s localhost:3000/api/hps/_platform/readyz | python3 -m json.tool | head -30
```

`/readyz` reports what the stack can actually do. Expect `status: ready`, `llm: scripted`,
`simulation_pricing: zero`, `ocr: available` (Tesseract is installed in the image) and
`auth_demo_trusted` listing the compose bridge ranges.

Seed the one-document demo corpus (idempotent — safe to run again):

```bash
docker compose exec backend python -m shared.demo_seed
```

## 2. Ingest your own corpus

`./material` is mounted read-only at `/corpus`. PDFs only; the script chunks paragraphs, indexes
passages and pins a snapshot.

```bash
docker compose exec backend python scripts/ingest_corpus.py /corpus --dry-run --snapshot-label corpus-2026
docker compose exec backend python scripts/ingest_corpus.py /corpus --limit 10 --snapshot-label corpus-2026
docker compose exec backend python scripts/ingest_corpus.py /corpus --snapshot-label corpus-2026
```

Afterwards assemble packs against the printed `snapshot_id` (`POST /api/v1/evidence/packs`) or ingest a
curated subset into its own snapshot for the demo. Scanned PDFs need the OCR path — `/readyz` tells you
whether it is available (`ocr: available`), and files it cannot read show up as named failures in the
ingestion run (`GET /api/v1/corpus/ingestion-runs/{id}` → `outcomes[]`).

Long ingest? Run it in the background and watch the log:

```bash
docker compose exec -d backend sh -c \
  'python scripts/ingest_corpus.py /corpus --snapshot-label corpus-2026 > /tmp/ingest.json 2> /tmp/ingest.log'
docker compose exec backend tail -f /tmp/ingest.log
```

## 3. Connect a live model

The stack boots with the scripted provider so a rehearsal needs no key. Any **OpenAI-compatible**
`/chat/completions` endpoint works: hosted APIs (OpenAI, Azure AI Foundry, OpenRouter, Mistral, Groq, …),
a local runtime (Ollama, vLLM, LM Studio), or any vendor that exposes the same shape. Nothing in the code
is bound to one provider.

Two files, both git-ignored:

```bash
# .env at the repository root — the key only, read by compose
LLM_API_KEY=sk-…                    # or any token your endpoint expects

# demo.env.local — the endpoint, model and metering
LLM_PROVIDER=openai-compatible      # live provider; `scripted` is the placeholder
LLM_BASE_URL=https://api.openai.com/v1
LLM_MODEL=gpt-4o-mini
LLM_REASONING_EFFORT=               # optional: low|medium|high, provider-specific
LLM_JSON_MODE=true                  # sends response_format={"type":"json_object"}
SIMULATION_INPUT_PRICE_PER_1K=0.00015
SIMULATION_OUTPUT_PRICE_PER_1K=0.0006
SIMULATION_ALLOW_ZERO_PRICE=false
```

```bash
docker compose up -d --force-recreate backend
curl -s localhost:3000/api/hps/_platform/readyz | grep -o '"llm[^,]*'
# "llm": "openai-compatible", "llm_model": "<your model>", "simulation_pricing": "configured"
```

| Setting | Meaning |
|---|---|
| `LLM_BASE_URL` | API root **without** `/chat/completions`; the adapter appends it. Use `/v1` where the provider needs it |
| `LLM_MODEL` | model id exactly as the provider names it |
| `LLM_JSON_MODE` | asks for a JSON object; both OpenAI-style and self-hosted servers that support it will comply. Set `false` for servers that reject the field |
| `LLM_REASONING_EFFORT` | optional; only for providers that expose reasoning control. Leave empty otherwise |
| `LLM_TIMEOUT_S` / `LLM_MAX_RETRIES` | per-call timeout and retries on 429/5xx/transport errors |
| `SIMULATION_*_PRICE_PER_1K` | your provider's price per 1k tokens, in **one** currency — the UI formats EUR, so either report EUR or say "USD" on stage |

Cost and latency depend entirely on the model you point at; nothing is calibrated to a specific vendor.
With a real provider keep `SIMULATION_ALLOW_ZERO_PRICE=false`, otherwise every call is metered at 0 and the
budget guard can only stop by invocation count. A run is 9 turns per round.

Failures are explicit, never silent: a wrong key ends the job as `dead_letter` with
`LlmProviderFailed … http_401`, an unusable reply with `LLM_OUTPUT_UNPARSEABLE`, and a claim the claim
agent will not admit is dropped from the argument instead of being asserted.

### Switching between the live model and the placeholder at runtime

Both backends sit behind one facade, so a demo can show them back to back without a restart. The active
choice is process state: a restart restores `LLM_PROVIDER`.

```bash
make stack-provider     # {"active":"openai-compatible","model":"<your model>","available":[…]}
make stack-scripted     # placeholder: persona policy, [synthetic] … arguments, zero cost
make stack-live-llm     # back to the live model
```

The same switch is in the UI under **Einstellungen → Modell** ("Live-LLM" / "Skript (Platzhalter)"), and
the overview's status pill follows it. The UI names the *engine*, never the model id; `/usage` reports the
model each run actually used, so runs made with either engine keep their own label.

Pre-flight before the jury (this also exercises pause/resume and the budget guard):

```bash
RUN=$(curl -s -X POST localhost:3000/api/hps/runs -H 'content-type: application/json' \
  -d '{"question":"Kassenstellen aufstocken und Kosten senken?","round_cap":1}' | python3 -c 'import json,sys;print(json.load(sys.stdin)["run_id"])')
curl -s -X POST localhost:3000/api/hps/runs/$RUN:start -H 'content-type: application/json' -d '{"budget":{"max_invocations":12}}'
curl -s localhost:3000/api/hps/runs/$RUN/usage | python3 -m json.tool
```

## 3b. Running the demo on the ingested 2020 press corpus

The corpus lives in a PostgreSQL on the host (`hps-postgres`, port 5433) — 241 documents, 4 304
passages, the annual snapshot `pressespiegel-2020` (231 documents, 4 297 indexed passages) plus the
monthly snapshots. The stack reaches it through `host.docker.internal`, pinned in a git-ignored `.env`
at the repository root so `docker compose up` needs no shell exports:

```bash
# .env (git-ignored)
DATABASE_URL=postgresql+asyncpg://hps:hps@host.docker.internal:5433/health_policy
LLM_API_KEY=sk-…
```

```bash
docker compose up -d            # backend now talks to the host database
curl -s localhost:3000/api/hps/_platform/readyz | grep -o '"database": "[a-z]*"'
```

Then, in the browser:

1. **Settings → Demo-Bootstrap** → import `backend/samples/pressespiegel-2020-seed.json`
   (snapshot + five annual packs + five reference figures). Without it the manual "open position" form
   has no pack to cite; the automated path assembles its own pack and does not need it.
2. **Open a run by id** with the header field (`Lauf-ID suchen`) for runs created outside the browser,
   or start a fresh one from *Neue Verhandlung*.

Alternative, self-contained: re-ingest into the compose volume (`make stack-ingest`) and drop the
`DATABASE_URL` line from `.env`. The ingest script now replaces segmentation's whole-body placeholder
with paragraph-sized chunks, so a fresh corpus indexes properly.

Known demo limits: the brief's eight sections are narrative — `citation_count` is 0 because the brief
cites *admitted claims* and model prose carries none; provenance is shown on the Evidence tab. An
automated round 2 adds arguments but no new positions, so the stance matrix fills in round 1 only.

## 4. Operating it

```bash
docker compose logs -f backend            # structured JSON logs, one line per request
docker compose down                       # keeps the database volume
docker compose down -v                    # wipes documents, runs, briefs
docker compose exec backend python -m shared.demo_seed   # re-seed after a wipe
```

Migrations run from the backend entrypoint on every start (`alembic upgrade head`), so an older volume
is upgraded in place. `HPS_SEED_ON_BOOT=1` seeds before serving — convenient for a rehearsal, but it
runs on every restart, so leave it 0 when you are ingesting your own corpus.

## 5. Two things that will bite you

**Demo auth is host-based.** `AUTH_MODE=demo` grants anonymous access to *loopback clients only*; inside
Docker the frontend is not loopback, so the compose file sets `AUTH_DEMO_TRUSTED_CIDRS` to the private
ranges Docker/OrbStack allocate from. The backend does **not** trust `X-Forwarded-For` (uvicorn runs
without `--proxy-headers`) — a spoofable header would defeat the guard. If your bridge uses another
subnet, set `AUTH_DEMO_TRUSTED_CIDRS` in `demo.env.local`:

```bash
docker network inspect hps-demo_default --format '{{range .IPAM.Config}}{{.Subnet}}{{end}}'
```

**Runtime config must not be prerendered.** `/api/hps/meta` awaits `connection()` so the frontend reads
`HPS_API_BASE_URL` at request time; without it, Next baked the build host's default (`127.0.0.1:8000`)
into the image and every proxy call failed inside Docker.

## 6. Not included (deliberate)

- No reverse proxy / TLS: single-origin on `localhost:3000`. Put Caddy in front for a remote demo.
- No worker sidecar: the simulation worker runs inside the backend process, which is what the current
  design does (single-replica). Running two backend replicas would double-run jobs.
- No secrets in images or `demo.env`: keys live in `demo.env.local` or the shell.

## License

MIT — see [`LICENSE`](LICENSE). The challenge brief in `material/` remains the property of its authors.

