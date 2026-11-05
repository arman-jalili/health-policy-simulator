# Disaster Recovery Plan — StakeholderModel

Canonical architecture: `.pi/architecture/modules/stakeholder-model.md`.
Runtime decision: `.pi/architecture/decisions/ADR-011-stakeholder-model-runtime-integration.md`.

## Scope and targets

StakeholderModel owns institutional identity, profile completeness, mandate grounding, veto class
rules, historical attribution and immutable run bindings. Persona cards are configuration committed
to git; the current runtime seeds an in-memory registry from them.

| Scenario | RTO | RPO | Basis |
|---|---|---|---|
| API process crash / bad deploy | 5 min | 0 for persona cards | cards in git; in-memory mutations lost |
| Invalid persona deployed | 5 min | 0 | boot aborts; revert the card and redeploy |
| Persona directory loss | 15 min | 0 | restore from git |
| Database loss | out of scope today | — | stakeholder profiles are not yet durable |
| Region loss | out of scope | — | single-region prototype |

## Backup strategy

| What | How | Frequency | Retention |
|---|---|---|---|
| Persona cards | git (`backend/config/personas/`) | per commit | permanent |
| Code + migrations | git | per commit | permanent |
| In-memory runtime state | not backed up | — | lost on restart |
| Contract proofing | CI job output | per PR | 30 days |

The absence of a stakeholder table is deliberate in this phase: there is no durable store to back
up. The PostgreSQL profile/binding adapter and migration are the follow-up; once they exist, this
plan must add `pg_dump`/PITR for those tables before they hold demo-critical state.

## Restore procedure

1. Restore the repository at the last known-good commit (persona cards included).
2. Confirm `backend/config/personas/` contains exactly 9 cards, each with interests and constraints.
3. Start one API instance.
4. Verify boot succeeds; an invalid card must fail before serving.
5. `GET /healthz` → 200; `GET /readyz` → `stakeholder_model=ok`,
   `stakeholder_institutions=9`.
6. Smoke: `GET /api/v1/stakeholders` returns 9; run the waiting-time selection and confirm ≥7
   institutions.
7. Re-record any demo positions/bindings lost with the process (in-memory limitation).
8. Record achieved RTO/RPO and root cause.

## Failover

The prototype runs one API process. Failover means starting a replacement process with the same
persona directory and configuration. There is no stakeholder state to promote today. If the shared
database is unavailable, the process can still boot with memory persistence only in `ENV=local`;
staging/production require the database for the other contexts.

## Data integrity checks after recovery

```bash
# Persona cards are the source of truth
find config/personas -maxdepth 1 -name '*.yaml' | wc -l    # expect 9
grep -L '^interests:' config/personas/*.yaml                # expect empty
grep -L '^constraints:' config/personas/*.yaml              # expect empty

# Runtime allowlist
curl -s localhost:8000/readyz | jq '.checks.stakeholder_institutions'  # expect "9"
```

- The allowlist must contain exactly the 9 persona codes.
- A selection result must never contain an institution outside the allowlist.
- If mutable state matters for a demo, restart before the demo and rebuild it deliberately rather
  than assuming persistence.

## Communication

Single operator (hackathon prototype): record timeline, cause, achieved RTO/RPO and follow-up in the
project workpad. Notify the demo owner if a restart lost recorded positions or bindings. Do not
present reconstructed institutional positions as if they were original provenance-backed records.
