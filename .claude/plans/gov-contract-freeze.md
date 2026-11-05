# GovernanceCompliance contract freeze (#248)

## Scope
Freeze all public interfaces and schemas for the 11 governance-compliance components before
implementation. ADR-008 service depth: application + infrastructure + concrete interfaces; no
domain modules.

## Frozen surface
- Decisions, violation classes, speaker kinds, figure verdicts, rule ids
- Commands and result DTOs, violation/provenance persistence records
- Seven application services and the deterministic guard rule chain
- NER, institution resolver, figure verdict, allowlist, provenance and publisher ports
- Violation/provenance repository ports
- Error codes and five HTTP routes/scopes/status codes
- Published guard verdict and position provenance views
- Composition container and `build_container` factory

## Validation
- 76 structural contract checks
- ruff/format/mypy, full pytest, architecture/modeling-depth/DDD/canonical validators
