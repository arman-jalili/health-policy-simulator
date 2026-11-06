# Implementation plan — #404–#409

1. **#404** add `OpenRound` + `POST /runs/{id}/rounds`, close route; round-cap closes the run;
   publish events to the progress broker.
2. **#405** fill `0401`/`0402`; typed aggregate snapshot codec; SQLAlchemy run/log adapters selected by
   `PERSISTENCE`; restart round-trip.
3. **#406** bind run-log, mandate-threshold and veto ACLs; subscribe `HandleRunClosed`; `0501` adapter.
4. **#407** bind brief history/consensus/provenance gates; `0502` adapter; shared-outbox events.
5. **#408** report actual adapters/capability in `/readyz`; add negotiation-session checks.
6. **#409** tick/correct Phase 4/5 roadmap, close D-005/D-007/D-008/D-009, align module contracts.
