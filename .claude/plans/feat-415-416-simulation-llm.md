# Implementation plan — #415/#416

1. **#415** replace the production no-op with `NegotiationSessionGateway`: load the aggregate, open
   rounds, submit evidenced positions, take one metered turn per stakeholder, close rounds, and let the
   run reach `CLOSED`. `RunSimulationJob` must not report `completed` for an undriven run.
2. **#416** add `LLM_PROVIDER` (`scripted`, `openai-compatible`, `azure_ai_foundry`), base URL, key,
   model, timeout/retries/temperature/output limits; implement `HttpLlmClient` with real usage tokens,
   latency, retries and a named failure; refuse scripted outside `ENV=local`; report provider/model in
   `/readyz`.
3. Prove both through the public API: rounds/positions/arguments/closed run/derived consensus, real
   stakeholder attribution, non-zero cost when priced, and `failed`/`dead_letter` instead of
   `completed` when the provider cannot drive the run.
