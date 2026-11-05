# ClaimValidation runtime defect batch — #200, #201, #202

## Group
Related batch (same module, shared runtime path). One branch/PR.

## Order
1. **#200** — normalise measure identity at the application boundary; expose normalised dimensions; name mismatch reasons.
2. **#201** — produce contradiction findings from `VerifyClaim`; deterministic pair id + upsert.
3. **#202** — parser refuses multiple numbers/year-leading text; immediate-window scale/unit.

## Validation
- Public-API tests for each defect
- Unit regression tests
- Full pytest, integration, ruff, format, mypy
- 95-check proofing, coverage gate, architecture/canonical/readiness
