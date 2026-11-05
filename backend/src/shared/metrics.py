"""Minimal in-process metrics for the prototype (Prometheus text exposition).

Canonical: .pi/architecture/implementation-roadmap.md (Phase 0 — observability)

Counters are process-local and reset on restart; that is sufficient for a single-process prototype
and keeps the dependency surface at zero. A real deployment replaces this registry with the
OpenTelemetry SDK without touching call sites.
"""

from __future__ import annotations

import threading
from collections import defaultdict
from typing import Final

CounterKey: Final[str] = "counter"


class MetricsRegistry:
    """Thread-safe counter registry keyed by name and sorted label pairs."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._counters: dict[tuple[str, tuple[tuple[str, str], ...]], float] = defaultdict(float)

    def increment(
        self, name: str, labels: dict[str, str] | None = None, amount: float = 1.0
    ) -> None:
        key = (name, tuple(sorted((labels or {}).items())))
        with self._lock:
            self._counters[key] += amount

    def value(self, name: str, labels: dict[str, str] | None = None) -> float:
        key = (name, tuple(sorted((labels or {}).items())))
        with self._lock:
            return self._counters.get(key, 0.0)

    def render(self) -> str:
        """Render the registry in Prometheus text format."""
        lines: list[str] = []
        with self._lock:
            for (name, labels), value in sorted(self._counters.items()):
                rendered_labels = ""
                if labels:
                    joined = ",".join(f'{key}="{item}"' for key, item in labels)
                    rendered_labels = f"{{{joined}}}"
                lines.append(f"{name}{rendered_labels} {value}")
        return "\n".join(lines) + ("\n" if lines else "")


METRICS = MetricsRegistry()
