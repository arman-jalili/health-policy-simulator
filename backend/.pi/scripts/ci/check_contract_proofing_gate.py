#!/usr/bin/env python3
"""Fail when a module doc has no contract script, or CI does not invoke the loop (#428).

Proofing that exists only on a developer laptop is documentation. The workflow runs every
`check_*_contracts.sh` and `check_*_contract.py`; this gate makes the module-doc inventory and that
loop agree, so a new module cannot be added without proofing or a deliberate exclusion.
"""

from __future__ import annotations

import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[3]
REPO = BACKEND.parent
MODULES = BACKEND / ".pi" / "architecture" / "modules"
CI_DIR = BACKEND / ".pi" / "scripts" / "ci"
CI_WORKFLOW = REPO / ".github" / "workflows" / "ci.yml"

# Named exclusions must be explicit and commented in the workflow; template is not a module.
EXCLUDED_DOCS = {"module-template.md"}
EXCLUDED_SCRIPTS: set[str] = set()


def contract_scripts(slug: str) -> list[Path]:
    variants = {slug, slug.replace("-", "_")}
    found: list[Path] = []
    for variant in variants:
        found.extend(CI_DIR.glob(f"check_{variant}_contracts.sh"))
        found.extend(CI_DIR.glob(f"check_{variant}_contract.py"))
    return sorted(set(found))


def main() -> int:
    failures: list[str] = []
    workflow = CI_WORKFLOW.read_text(encoding="utf-8") if CI_WORKFLOW.is_file() else ""
    if "check_*_contracts.sh" not in workflow:
        failures.append("ci.yml does not loop over check_*_contracts.sh")
    if "check_*_contract.py" not in workflow:
        failures.append("ci.yml does not loop over check_*_contract.py")

    scripts = {
        path.name
        for pattern in ("check_*_contracts.sh", "check_*_contract.py")
        for path in CI_DIR.glob(pattern)
    }
    sh_loop = "check_*_contracts.sh" in workflow
    py_loop = "check_*_contract.py" in workflow
    for script in sorted(scripts - EXCLUDED_SCRIPTS):
        covered = sh_loop if script.endswith(".sh") else py_loop
        if not covered:
            failures.append(f"{script} exists but the matching ci.yml loop is missing")

    for doc in sorted(MODULES.glob("*.md")):
        if doc.name in EXCLUDED_DOCS:
            continue
        slug = doc.stem
        if not contract_scripts(slug):
            failures.append(f"{doc.name} has no check_{slug}_contracts.sh / check_{slug}_contract.py")

    if failures:
        print("Contract proofing gate FAILED:")
        for failure in failures:
            print(f"  - {failure}")
        return 1
    print(f"Contract proofing gate passed ({len(scripts)} scripts, {len(list(MODULES.glob('*.md'))) - 1} modules).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
