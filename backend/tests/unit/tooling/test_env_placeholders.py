"""Readiness env rule: documented defaults pass; placeholder secrets fail by name (#239)."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SCRIPT = ROOT / ".pi" / "scripts" / "ci" / "check_env_placeholders.sh"
EXAMPLE = ROOT / ".env.example"
BASH = shutil.which("bash") or "/bin/bash"


def _run(
    tmp_path: Path, env_body: str, example_body: str | None = None
) -> subprocess.CompletedProcess[str]:
    (tmp_path / ".env").write_text(env_body)
    (tmp_path / ".env.example").write_text(
        EXAMPLE.read_text() if example_body is None else example_body
    )
    return subprocess.run(  # noqa: S603 - fixed local script and arguments
        [BASH, str(SCRIPT), ".env", ".env.example"],
        cwd=tmp_path,
        text=True,
        capture_output=True,
        check=False,
    )


def test_copied_example_with_the_documented_database_url_passes(tmp_path: Path) -> None:
    result = _run(tmp_path, EXAMPLE.read_text())

    assert result.returncode == 0, result.stdout + result.stderr
    assert "DATABASE_URL" not in result.stdout


def test_placeholder_secret_fails_and_names_the_variable(tmp_path: Path) -> None:
    result = _run(tmp_path, "API_KEY=change-me\n", "")

    assert result.returncode == 1
    assert "API_KEY" in result.stdout
    assert "placeholder" in result.stdout


def test_secret_matching_the_example_fails_and_names_the_variable(tmp_path: Path) -> None:
    result = _run(tmp_path, "APP_SECRET=same\n", "APP_SECRET=same\n")

    assert result.returncode == 1
    assert "APP_SECRET" in result.stdout
    assert ".env.example" in result.stdout


def test_non_secret_default_may_match_the_example(tmp_path: Path) -> None:
    result = _run(
        tmp_path,
        "DATABASE_URL=postgresql+asyncpg://hps:hps@localhost:5433/health_policy\n",
    )

    assert result.returncode == 0, result.stdout + result.stderr
