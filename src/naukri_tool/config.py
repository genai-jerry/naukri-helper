"""Typed configuration loaded from `.env` via pydantic-settings.

Milestone 1 keeps the surface small — only what the plan's §13 names — but
defines the directories later milestones will write into so the CLI can
create/inspect them without each stage reinventing paths.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration.

    Values come from environment variables; `.env` is loaded automatically when
    present. Fields mirror the names documented in PLAN.md §13.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # --- Secrets ----------------------------------------------------------
    # Optional at scaffold time so the CLI can boot without a key. Stages that
    # actually call the API will assert this is set.
    anthropic_api_key: str | None = Field(default=None)

    # --- Paths ------------------------------------------------------------
    resume_master_path: Path = Field(default=Path("resumes/master.yaml"))
    auth_dir: Path = Field(default=Path("auth"))
    output_dir: Path = Field(default=Path("output"))

    @property
    def storage_state_path(self) -> Path:
        """Playwright storage_state file — written by `naukri-tool login`."""
        return self.auth_dir / "storage_state.json"

    def require_anthropic_api_key(self) -> str:
        """Return the API key or raise a clear error if unset."""
        if not self.anthropic_api_key:
            raise RuntimeError(
                "ANTHROPIC_API_KEY is not set. Copy .env.example to .env and fill it in."
            )
        return self.anthropic_api_key


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Cached settings accessor. Tests can call `get_settings.cache_clear()`."""
    return Settings()
