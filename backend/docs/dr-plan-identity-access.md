# IdentityAccess Disaster Recovery Plan

Scope: API-key credentials and their attribution metadata (`identity_access_api_key`, migration
`0104_identity_access`). Business data recovery is covered by `docs/dr-plan.md`; this plan covers
the authentication surface and credential compromise.

## Targets

| Scenario | RTO | RPO | Basis |
|---|---|---|---|
| API process / bad deploy | 5 min | 0 | stateless; roll back the image |
| Key table corruption/loss | 30 min | ≤ 15 min | restore the database (same instance as corpus) |
| Compromised key | 5 min | 0 | revoke via admin API; no restore needed |
| Demo/local with `PERSISTENCE=memory` | n/a | total loss by design | never used outside `ENV=local` |
| Region loss | out of scope (prototype) | — | single-region by design |

The key table shares the database backup with the corpus, so its real RPO equals the database RPO in
`docs/dr-plan.md`. Plaintext keys are not backed up because they are never stored; only hashes are.

## Backups

- Database backup includes `identity_access_api_key` (hashes + metadata).
- Migration `0104_identity_access` is in git and must be applied after restore.
- Never back up plaintext keys in tickets, logs, object storage or chat. The creation response is the
  only copy; store it in the secret manager immediately.
- Verify restore monthly: restore into a scratch DB, `alembic upgrade head`, run
  `pytest -m integration tests/integration/test_identity_access_*`.

## Restore procedure

1. Freeze deploys and declare the incident.
2. Restore PostgreSQL per `dr-plan.md` (base backup + WAL, then `alembic upgrade head`).
3. Start one API instance; confirm `/healthz`, `/readyz`.
4. Verify the key table:
   ```sql
   select count(*), count(*) filter (where revoked_at is null) from identity_access_api_key;
   ```
5. Keys that existed at backup time work again. If the backup predates a revoke, **re-revoke** any
   key that was revoked after the backup point — a restore can resurrect a revoked credential.
6. If compromise is suspected, rotate: issue a new admin key, revoke all non-bootstrap keys, and
   re-issue per consumer.
7. Record achieved RTO/RPO and the incident timeline.

## Credential compromise procedure

1. `DELETE /api/v1/admin/keys/{key_id}` (admin key required) → next request is `401`.
2. Check `shared_audit` / outbox `actor` values for actions taken with the compromised key.
3. Issue a replacement key with the minimum role; store plaintext once.
4. If the admin key itself is compromised: bootstrap a new admin key from a trusted shell (see
   `runbook-identity-access.md`), revoke the old admin key, then audit admin actions.
5. Rotate any key found in logs/tickets; redaction failures are bugs.

## Failover

- The API is stateless; point `DATABASE_URL` at the promoted replica/restored instance and restart.
- `AUTH_MODE=strict` is required in shared environments; do not fail over to demo mode.
- Key resolution reads the database on every request, so failover is immediate once the DB is
  reachable; there is no in-process key cache to invalidate.
- The outbox relay is independent; revocations and issuance commit in the same database and are
  visible to the next request.

## Post-recovery checks

- `GET /readyz` → `checks.database == "ok"`; LLM check optional.
- Admin list returns the expected keys; revoked keys stay revoked.
- A known-good key resolves to the expected role/actor; a revoked key returns `401`.
- `select count(*) from shared_event_outbox where status = 'pending'` is bounded; command events
  carry the actor label.
- Run the contract checker and integration suite before resuming traffic.

## Communication

Single operator (hackathon prototype). Record the incident, cause, achieved RTO/RPO and follow-up in
the project workpad; notify the demo owner before the next demo if credentials were rotated.
