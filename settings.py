import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    port: int
    version: str
    health_mode: str

    @classmethod
    def from_env(cls):
        try:
            port = int(os.environ.get("APP_PORT", "8080"))
        except ValueError as exc:
            raise ValueError("APP_PORT must be an integer") from exc
        if not 1 <= port <= 65535:
            raise ValueError("APP_PORT must be between 1 and 65535")

        version = os.environ.get("APP_VERSION", "dev").strip()
        if not version:
            raise ValueError("APP_VERSION must not be empty")

        health_mode = os.environ.get("APP_HEALTH_MODE", "ok")
        if health_mode not in {"ok", "down"}:
            raise ValueError("APP_HEALTH_MODE must be ok or down")

        return cls(port, version, health_mode)
