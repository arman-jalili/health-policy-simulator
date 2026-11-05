---
# Guardian Workflow Configuration
# YAML front matter = runtime settings. Body = agent prompt.
# Changes to this file are detected and re-applied without restart.

workspace:
  root: ".pi/workspaces"
  hooks:
    timeout_ms: 60000

agent:
  max_turns: 20
  max_retry_backoff_ms: 300000
  stall_timeout_ms: 300000

system_prompt_tier: full

generate:
  on_conflict: warn
  atomic_writes: true

validate:
  fail_fast: false
  timeout_ms: 300000

goal:
  enabled: true
  max_turns: 20
  judge_validator: true

kanban:
  enabled: true
  auto_create_tasks: true

hooks:
  pre_tool_call: []
  post_tool_call: []
  pre_llm_call: []
  post_llm_call: []
  on_session_start: []
  on_session_end: []
  subagent_stop: []

curator:
  enabled: true
  stale_after_days: 30
  archive_after_days: 90
  auto_review: true

delegation:
  max_spawn_depth: 1
  max_concurrent_children: 3
  max_iterations: 50
  child_timeout_ms: 600000
---

# Project Context

> **Purpose:** Single source of truth for project-specific knowledge. All agents load this ONCE.
> **Customize:** Fill in the sections below for your project. The YAML front matter above already has working defaults.

## Project Overview

- **Name:** health-policy-simulator
- **Version:** 0.1.0
- **Language:** Python 3.12+ (FastAPI, SQLAlchemy 2.x async, Alembic)
- **Type:** Web App (REST + SSE API, modular monolith)
- **Repository:** local (`backend/` of health-policy-simulator); no remote yet

## Core Principles

> These are loaded into EVERY agent's context. Keep to 5-8 items.

1. **Read before edit** — Always read a file before modifying it. Never mutate blindly.
2. **Validate early** — Run `bash .pi/scripts/ci/run_preflight.sh` before committing.
3. **Architecture traceability** — Every implementation file must reference its architecture source in `.pi/architecture/modules/`.
4. **DRY context** — Shared knowledge lives in `.pi/context/`, not scattered across agent files.
5. **Shift-left validation** — Plans are validated before code is written.
6. **Auto-advance pipeline** — After completing a step, immediately call `pipeline_advance` to move to the next step/item. Do NOT ask the user for permission — just advance and continue.
7. **Auto-advance epics** — When you merge the last issue of an epic (architecture readiness), immediately start the next epic by running `/architect --epic "Next Module Name"`. Check the roadmap with `/architect --roadmap` to see which module is next. Do NOT ask the user — check the roadmap yourself and proceed.

## Commands

> Essential commands agents need to run. Update these for your project.

| Command | Purpose |
|---------|---------|
| `uv sync` | Install runtime + dev dependencies into `.venv` |
| `uv run pytest -m "not integration"` | Unit tests (no database needed) |
| `uv run pytest -m integration` | Migration/outbox round-trip (needs `DATABASE_URL`) |
| `uv run ruff check .` / `uv run ruff format --check .` | Lint / format check |
| `uv run mypy` | Strict type check (`src`, `tests`) |
| `uv run alembic upgrade head` | Apply migrations |
| `uv run hps-api` | Run the API locally |
| `docker compose up -d db` | Start PostgreSQL 16 + pgvector on :5433 |
| `bash .pi/scripts/ci/run_preflight.sh` | Run local preflight checks (activate `.venv` first) |
| `bash .pi/scripts/validate-*.sh` | Run specific validator |
| `python3 .pi/scripts/ci/check_modeling_depth.py` | ADR-008 modeling-depth check |

## Architecture

### Structure

```
backend/
├── src/
│   ├── main.py       # composition root (create_app)
│   └── shared/       # shared kernel (config, errors, ids, clock, db, outbox, audit, log, http)
├── migrations/       # Alembic revision chain (versions/0000_bootstrap.py)
├── tests/            # unit/ (fast) and integration/ (needs PostgreSQL)
├── docs/             # runbook.md, dr-plan.md
├── .pi/              # architecture source of truth
├── compose.yaml      # PostgreSQL 16 + pgvector for local development
└── pyproject.toml
```

Bounded contexts arrive in Phase 1 as `src/<context>/{domain,application,infrastructure,interfaces}/`.
`shared/` is the only package exempt from that structure; anything else under `src/` must be a
declared context in `.pi/architecture/modeling-depth.json`.

### Key Files

> Files every agent should know about. Keep under 10.

| File | Purpose |
|------|---------|
| `.pi/architecture/modules/` | Canonical architecture modules |
| `.pi/agent/AGENTS.md` | This file — project context + runtime config |
| `.pi/scripts/` | Validation scripts |
| `.pi/extensions/` | Pi extensions (tools, commands, hooks) |

## Quality Gates

### Before Commit

```bash
source .venv/bin/activate   # preflight needs ruff/mypy/pytest on PATH
bash .pi/scripts/ci/run_preflight.sh
```

### Before Push

```bash
uv run pytest            # includes integration tests when DATABASE_URL is set
uv run ruff check . && uv run mypy
```

## Subagent Delegation

| Task | Subagent | Tools |
|------|----------|-------|
| Explore codebase | `explore` | read-only (read, grep, glob) |
| Code review | `code-review` | read-only (read, grep, glob) |
| Security audit | `security-review` | read-only (read, grep, glob) |

Subagents have **restricted tool access** and **fresh context**. Include all relevant context in the spawn prompt.

## Snippets

Available `#handle` tokens for quick instruction injection:

| Handle | Purpose |
|--------|---------|
| `#security-review` | Security audit instructions |
| `#no-comments` | Suppress comments unless WHY is non-obvious |
| `#test-first` | TDD workflow instructions |

## Environment

> Variables agents may reference. Use `$VAR_NAME` in scripts.

| Variable | Purpose |
|----------|---------|
| `$GITHUB_TOKEN` | GitHub API authentication |
| `$CI` | CI environment indicator |

## Security Guards

Path safety guards are enforced by extensions (`.pi/extensions/bash-guard.ts`):

- **Read blocklist:** `.env*`, `*.pem`, `*.key`, `.ssh/*`, `.aws/*`, `.git/*`
- **Write blocklist:** Inherits read restrictions + `/etc/`, `/System/`, `/private/`
- **Command deny-list:** `rm -rf /`, `mkfs`, `dd of=/dev/*`, `terraform destroy`, `kubectl delete`
