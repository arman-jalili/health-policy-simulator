"""Shared kernel: cross-context primitives with no domain semantics of their own.

Only genuinely context-free building blocks live here. Domain vocabulary belongs to the
bounded context that owns it (see ADR-008 and `.pi/architecture/implementation-roadmap.md`).

Modules are imported explicitly (``from shared.errors import AppError``) rather than
re-exported, so that the shared kernel stays free of import cycles.
"""
