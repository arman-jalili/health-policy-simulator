"""ADR-008 marker: GovernanceCompliance is a service-depth context.

No aggregates, value objects, domain events or Python modules belong in this directory. The
guard is a deterministic rule chain over application DTOs; violations are the audit record.
"""
