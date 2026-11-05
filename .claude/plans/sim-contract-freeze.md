# SimulationOrchestration contract freeze (#205)

## Scope
Freeze all public interfaces/schemas for 11 components before implementation. Service depth:
application + infrastructure + concrete interfaces; no domain modules (ADR-008).

## Frozen surface
- Values/enums/graph state/budget/prompt records
- Commands, result DTOs, invocation envelope
- Service classes, rules, LLM/graph/worker/negotiation ports
- Repository ports and records
- Progress event payloads, error codes
- Concrete HTTP routes, schemas, scopes, status codes
- Published ACL views and composition factory

## Validation
- 40 contract-freeze structural checks
- Full pytest (875), integration (21)
- ruff/format/mypy, all validators, modeling depth, architecture conformance
