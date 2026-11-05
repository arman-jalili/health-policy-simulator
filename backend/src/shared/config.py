"""Environment-driven configuration. Loaded once at boot; fails fast when invalid.

Values come from process environment or a local ``.env`` file (see ``.env.example``).
Required values have no defaults on purpose: a missing ``DATABASE_URL`` must abort startup,
not degrade into a half-configured process.

Canonical: .pi/architecture/decisions/ADR-005-authentication-authorization.md
"""

from __future__ import annotations

from functools import lru_cache
from typing import Annotated, Any

from pydantic import Field, PostgresDsn, ValidationError, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from shared.enums import AuthMode, Environment, LogFormat, Persistence


class ConfigError(RuntimeError):
    """Raised when configuration is missing or unsafe."""


class Settings(BaseSettings):
    """Validated process configuration."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_prefix="",
        case_sensitive=False,
        extra="ignore",
        frozen=True,
    )

    service_name: str = "health-policy-simulator"
    version: str = "0.1.0"
    api_prefix: str = "/api/v1"
    # Bind all interfaces by default: the process is the container's entrypoint.
    api_host: str = "0.0.0.0"  # noqa: S104
    api_port: Annotated[int, Field(ge=1, le=65535)] = 8000

    env: Environment = Environment.LOCAL
    auth_mode: AuthMode = AuthMode.DEMO
    # PostgreSQL is the safe default: memory must be chosen explicitly (ADR-002, issue #26).
    persistence: Persistence = Persistence.POSTGRES

    database_url: Annotated[PostgresDsn, Field(repr=False)]
    # Optional LLM health endpoint; unset means "not configured" in /readyz, never a failure.
    llm_health_url: str | None = None
    simulation_model_id: str = "scripted-local"
    simulation_input_price_per_1k: float = 0.0
    simulation_output_price_per_1k: float = 0.0
    simulation_allow_zero_price: bool = True
    db_echo: bool = False
    db_pool_size: Annotated[int, Field(ge=1, le=50)] = 5
    db_max_overflow: Annotated[int, Field(ge=0, le=50)] = 5
    db_connect_timeout_s: Annotated[float, Field(gt=0, le=60)] = 5.0

    log_level: Annotated[str, Field(pattern="^(DEBUG|INFO|WARNING|ERROR|CRITICAL)$")] = "INFO"
    log_format: LogFormat = LogFormat.JSON

    cors_origins: list[str] = Field(default_factory=list)

    @property
    def is_demo(self) -> bool:
        return self.auth_mode is AuthMode.DEMO

    @model_validator(mode="after")
    def _reject_demo_in_production(self) -> Settings:
        if self.env is Environment.PRODUCTION and self.auth_mode is AuthMode.DEMO:
            raise ValueError("AUTH_MODE=demo is refused when ENV=production; set AUTH_MODE=strict")
        return self

    @model_validator(mode="after")
    def _reject_memory_persistence_outside_local(self) -> Settings:
        if self.env is not Environment.LOCAL and self.persistence is Persistence.MEMORY:
            raise ValueError(
                "PERSISTENCE=memory is refused outside ENV=local; "
                "in-memory state is lost on restart and must never serve staging or production"
            )
        return self


def _format_validation_error(error: ValidationError) -> str:
    problems = []
    for item in error.errors():
        location = ".".join(str(part) for part in item.get("loc", ())) or "<root>"
        problems.append(f"{location.upper()}: {item.get('msg', 'invalid value')}")
    return "; ".join(problems)


def load_settings(**overrides: Any) -> Settings:
    """Build settings, converting validation failures into a single actionable error."""
    try:
        return Settings(**overrides)
    except ValidationError as error:
        raise ConfigError(f"Invalid configuration — {_format_validation_error(error)}") from error


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Process-wide settings singleton."""
    return load_settings()
