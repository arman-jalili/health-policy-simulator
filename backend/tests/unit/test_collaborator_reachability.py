"""The W8 gate must be able to see a dead injection (guard the guard).

The recurring defect in this repo is a collaborator that is constructed, injected, unit-tested and
never called. `check_collaborator_reachability.py` is the mechanical check for it; these tests prove
the check itself works, so a future refactor cannot turn it into another shape-asserting script.
"""

from __future__ import annotations

import importlib.util
import pathlib
import sys
from types import ModuleType

_ROOT = pathlib.Path(__file__).resolve().parents[2]
_CHECK = _ROOT / ".pi/scripts/ci/check_collaborator_reachability.py"


def _load() -> ModuleType:
    spec = importlib.util.spec_from_file_location("check_collaborator_reachability", _CHECK)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_an_injected_collaborator_without_a_call_site_is_reported(tmp_path: pathlib.Path) -> None:
    module = _load()
    source = tmp_path / "src"
    source.mkdir()
    (source / "service.py").write_text(
        "class Service:\n"
        "    def __init__(self, guard):\n"
        "        self._guard = guard\n"
        "\n"
        "    def run(self):\n"
        "        return 1\n"
    )

    findings = module.scan(source)

    assert [(cls, attr) for _, _, cls, attr in findings] == [("Service", "_guard")]


def test_a_collaborator_that_is_read_is_not_reported(tmp_path: pathlib.Path) -> None:
    module = _load()
    source = tmp_path / "src"
    source.mkdir()
    (source / "service.py").write_text(
        "class Service:\n"
        "    def __init__(self, guard):\n"
        "        self._guard = guard\n"
        "\n"
        "    def run(self):\n"
        "        return self._guard.evaluate()\n"
    )

    assert module.scan(source) == []


def test_error_payload_attributes_are_not_treated_as_collaborators(tmp_path: pathlib.Path) -> None:
    module = _load()
    source = tmp_path / "src"
    (source / "domain").mkdir(parents=True)
    (source / "domain" / "errors.py").write_text(
        "class Rejected(Exception):\n"
        "    def __init__(self, reason):\n"
        "        self.reason = reason\n"
    )

    assert module.scan(source) == []


def test_the_repository_allowlist_has_no_stale_entries() -> None:
    """Every allowlisted attribute must still be dead; otherwise prune the entry."""
    module = _load()
    findings = module.scan(_ROOT / "src")
    keys = {
        f"{pathlib.Path(path).relative_to(_ROOT).as_posix()}:{cls}.{attr}"
        for path, _, cls, attr in findings
    }

    assert sorted(set(module._ALLOWED) - keys) == []
