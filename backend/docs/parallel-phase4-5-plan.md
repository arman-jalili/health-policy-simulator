# Parallel Execution Plan — Phases 4 & 5 (pipeline-native)

**Status:** Proposed
**Date:** 2026-11-06
**Goal:** three `/architect --epic` pipelines running concurrently in three worktrees, converging on `main`.
No hand-written module code, no hand-written contracts, no fakes — the epics build their own
contract-freeze as item #1, exactly as they did for Phase 3.

---

## 1. What the pipeline already handles

| Concern | Handled by | Verdict |
|---------|-----------|---------|
| Contract freeze per module | pipeline item #1 (`issue-*-contract-freeze`, `generateContractFreezeMarkdown`) | ✅ leave alone |
| Module doc → components | `parseModuleFile` reads `## Components` + the AC table; all three docs are complete | ✅ leave alone |
| Per-epic state machines | `.guardian-*.json` are gitignored | ✅ independent per worktree |
| Published language NS→CA→DB | already normative in the module docs (`negotiation-session.md:320-360` events, `consensus-analysis.md` Wiring Contract subscriptions) | ✅ the docs are the contract |
| Wiring / runtime-integration / proofing / readiness | items #n-3 … #n of every epic | ✅ leave alone |
| Merge to `main` per item | step 4 of every item, `mergeOnValid: true` | ✅ keep — this is how main stays releasable |

## 2. The only two things that must be fixed before a second pipeline exists

### Fix 1 — module-scoped issue IDs (blocking)

`.pi/extensions/architect.ts`:

| Line | Now | After |
|---|---|---|
| `:295` | `issue-${comp.name…}` | `issue-${moduleSlug}-${comp.name…}` |
| `:273` | `issue-contract-freeze` | `issue-${moduleSlug}-contract-freeze` |
| `:326` | `issue-runtime-integration` | `issue-${moduleSlug}-runtime-integration` |
| `:346` | `issue-proofing` | `issue-${moduleSlug}-proofing` |
| `:365` | `issue-architecture-readiness` | `issue-${moduleSlug}-architecture-readiness` |

`moduleSlug` is already computed at `:294`. Without this, all three epics emit the same four item IDs →
the same branch `feat/<id>` → `reconcile()` (`pipeline.ts:268-290`, runs on every `session_start`) sees a
merged PR for that branch and **marks the item done** in every other epic. That is silent work loss, not a
merge conflict.

### Fix 2 — pre-allocated Alembic chain (blocking)

The revision chain is linear (`0305_governance_compliance` is head). Three branches each appending
`down_revision="0305"` merges cleanly in git but leaves **three heads**, and `alembic upgrade head` fails
in the integration job on every branch after the second merge.

Create five empty revisions, chained, in one commit — each session later fills **its own file** and never
touches the chain:

```
0305_governance_compliance
  → 0401_negotiation_session        → 0402_negotiation_session_log     (NS owns)
  → 0501_consensus_analysis                                             (CA owns)
  → 0502_decision_brief                                                 (DB owns)
```

The roadmap already names these revisions (`§Phase 4`/`§Phase 5 Database Migrations`), so this is not a
design decision — it is writing down what the docs already say.

Optional 1-liner alongside: add `.pi/.guardian-kanban.json` to `.gitignore` (agent runtime state; the
other two state files are already ignored).

### Fix 3 — component status parsing (silent component loss)

`parseModuleFile` treats **any** line starting with `status:` as the component status
(`helpers.ts:436`). `decision-brief.md` embeds `status: BriefStatus = BriefStatus.DRAFT` inside the
aggregate-root code block, so that component parsed as status `briefstatus = briefstatus.draft` and was
**excluded from `nextLogicalSlice`** — the DB epic would have silently dropped its aggregate root and run
17 items instead of 18. Fixed by restricting the value to the four declared statuses
(`planned | in-progress | implemented | deprecated`). Verified by parsing all three module docs:
17 / 15 / 14 components → 21 / 19 / 18 items, all ids unique.

**Total prep:** ~15 minutes, one small PR. Nothing else.

## 3. Launch sequence

```bash
cd /Users/arman/project/ki-challange/health-policy-simulator
git switch main && git pull --ff-only
# after Fix 1 + Fix 2 are merged:
git worktree add ../hps-ns -b epic/negotiation-session
git worktree add ../hps-ca -b epic/consensus-analysis
git worktree add ../hps-db -b epic/decision-brief
```

One worktree may hold `main` — these hold their own epic branches instead. In each worktree's `backend/`:

```
/architect --epic "negotiation-session" --tdd     # hps-ns  — start first
/architect --epic "consensus-analysis" --tdd      # hps-ca  — start after NS contract-freeze merges
/architect --epic "decision-brief" --tdd          # hps-db  — start after CA contract-freeze merges
```

**Stagger by one item, not by one phase.** NS's `contract-freeze` item is ~1–2 h of a ~3-day run; wait for
it to merge to `main`, then start CA from the updated `main`, then DB after CA's freeze. Each epic's
contract-freeze item then codes against a published language that actually exists on `main`, instead of
re-inventing it in three directions. Cheapest insurance available; costs ~2 h wall clock.

Item counts (components from `## Components` + AC table, plus contract-freeze, runtime-integration,
proofing, readiness): NS **21**, CA **19**, DB **18** — ~58 items × 4 steps.

## 4. Rules the three sessions follow (mechanical, no design work)

1. **Per-item base:** before creating `feat/<issue-id>`, `git fetch origin && git reset --hard origin/main`.
   After any rebase, re-run the step's validators before merging.
2. **Own your files:** `src/<own module>/**`, `tests/unit/<own module>/**`, own migration file, own
   module doc, own `.pi/issues/issue-<module>-*.md`, own `CHANGELOG.md` subsection.
3. **`src/shared/app.py` and `migrations/env.py` are shared** — each epic's *wiring* and
   *runtime-integration* items touch them. They will conflict. Resolve by keeping all three additions
   (imports, container line, `include_router` line); it is 3 short hunks, not a design conflict.
4. **Dependency tail:** CA's and DB's `runtime-integration` / `proofing` items need a working upstream.
   If the upstream isn't on `main` yet, leave the item at its merge step with the PR open — the pipeline
   waits, nothing is faked, no work is lost. This is the only real serializer and it lands at the end of
   each epic, after all components are built.
5. **`--tdd`** on all three: the generated failing tests come from each module's own architecture
   contracts, and they cannot overlap between modules.

## 5. Convergence

When all three pipelines drain: one session on `main` runs the full chain through the real app
(open run → rounds → close → consensus derived → brief published, Postgres, HTTP), executes the roadmap's
W1–W10 evidence sweep across the three modules, updates Phase 4/5 status + CHANGELOG, and closes the
tracking issues/epics. ADR-015 (NS runtime integration) and ADR-016 (analysis/brief runtime integration)
are written here, not per module.

## 6. Risk register

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Issue-ID collision | certain if not fixed | silent skipped components | Fix 1 |
| Dropped component (status parse) | certain for `decision-brief` | silent missing aggregate root | Fix 3 |
| Alembic multiple heads | certain if not fixed | red CI on `main` | Fix 2 |
| `app.py` / `env.py` conflicts | likely (3–4× per epic) | minutes each | rule 3 — keep all hunks |
| Contract drift CA/DB vs NS events | medium | medium | stagger by one item (§3); the tail items re-verify against the real producer |
| Rebase churn | medium | medium | rule 1; rebase at step boundaries only |
| 3 × CI queue (~8 min/PR) | medium | low | `ci.yml:14` groups per ref, no cross-cancel; merge round-robin |
| ~232 pipeline steps to supervise | high | medium | `--tdd` reduces round-trips; expect ~3 days wall clock vs ~6.5 sequential |
