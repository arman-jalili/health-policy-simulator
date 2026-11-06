# Implementation plan — #411–#414

1. **#411** make `IndexWriterPort.search` one async contract; await it in `CorpusPassageSearch`; remove
   the `except TypeError` arity guess; prove pack assembly against PostgreSQL.
2. **#412** `CloseRound` discloses every open position after the aggregate save; GovernanceCompliance
   joins the close UnitOfWork; `/readyz` names `close_round` as producer; prove 201/422 through the API.
3. **#413** remove the "no stances" 503; project `unresolved` + `reason: no_recorded_stances`; keep 503
   for an unbound source; prove the three cases.
4. **#414** add `samples/demo-corpus.pdf`, idempotent `shared.demo_seed`, HTTP `shared.demo_walkthrough`,
   `make demo-seed` / `make demo-walkthrough`, CI stage and `docs/demo-walkthrough.md`; document the
   `client-declared` attribution posture in `/readyz`.
