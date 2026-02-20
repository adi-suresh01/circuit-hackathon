"""Application configuration loaded from environment variables."""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv
from pydantic import BaseModel, Field

from app.utils.digikey import normalize_digikey_account_id

BASE_DIR = Path(__file__).resolve().parent.parent


class Config(BaseModel):
    """Runtime configuration resolved from environment variables."""

    app_name: str = Field(default="Circuit Hackathon Backend")
    app_env: str = Field(default="local")
    log_level: str = Field(default="INFO")
    aws_region: str = Field(default="us-east-1")
    neo4j_uri: str = Field(default="bolt://localhost:7687")
    neo4j_username: str = Field(default="neo4j")
    neo4j_password: str = Field(default="circuit-dev-password")
    digikey_client_id: str | None = Field(default=None)
    digikey_client_secret: str | None = Field(default=None)
    digikey_account_id: str | None = Field(default=None)
    digikey_use_sandbox: bool = Field(default=False)
    digikey_locale_site: str = Field(default="US")
    digikey_locale_language: str = Field(default="en")
    digikey_locale_currency: str = Field(default="USD")
    digikey_http_timeout_s: int = Field(default=20)
    minimax_api_key: str | None = Field(default=None)
    minimax_base_url: str = Field(default="https://api.minimax.io")
    minimax_model: str = Field(default="MiniMax-M2.5-highspeed")
    enable_minimax_narrator: bool = Field(default=False)
    dd_service: str = Field(default="circuit-backend")
    dd_env: str = Field(default="local")
    dd_version: str = Field(default="0.1.0")
    dd_agent_host: str = Field(default="localhost")
    dd_trace_enabled: bool = Field(default=False)
    dd_logs_injection: bool = Field(default=True)

    @property
    def is_production(self) -> bool:
        return self.app_env.lower() in {"prod", "production"}

    def digikey_host(self) -> str:
        if self.digikey_use_sandbox:
            return "sandbox-api.digikey.com"
        return "api.digikey.com"

    @classmethod
    def load(cls) -> "Config":
        env_name = os.getenv("APP_ENV", os.getenv("ENV", "local")).lower()
        if env_name not in {"prod", "production"}:
            load_dotenv(BASE_DIR / ".env", override=False)
        digikey_timeout_raw = os.getenv("DIGIKEY_HTTP_TIMEOUT_S", "20")
        try:
            digikey_timeout_s = int(digikey_timeout_raw)
        except (TypeError, ValueError):
            digikey_timeout_s = 20

        return cls(
            app_name=os.getenv("APP_NAME", "Circuit Hackathon Backend"),
            app_env=os.getenv("APP_ENV", os.getenv("ENV", "local")),
            log_level=os.getenv("LOG_LEVEL", "INFO"),
            aws_region=os.getenv("AWS_REGION", "us-east-1"),
            neo4j_uri=os.getenv("NEO4J_URI", "bolt://localhost:7687"),
            neo4j_username=os.getenv(
                "NEO4J_USERNAME", os.getenv("NEO4J_USER", "neo4j")
            ),
            neo4j_password=os.getenv("NEO4J_PASSWORD", "circuit-dev-password"),
            digikey_client_id=os.getenv("DIGIKEY_CLIENT_ID"),
            digikey_client_secret=os.getenv("DIGIKEY_CLIENT_SECRET"),
            digikey_account_id=normalize_digikey_account_id(
                os.getenv("DIGIKEY_ACCOUNT_ID")
            ),
            digikey_use_sandbox=os.getenv("DIGIKEY_USE_SANDBOX", "false").lower()
            in {"1", "true", "yes", "on"},
            digikey_locale_site=os.getenv("DIGIKEY_LOCALE_SITE", "US"),
            digikey_locale_language=os.getenv("DIGIKEY_LOCALE_LANGUAGE", "en"),
            digikey_locale_currency=os.getenv("DIGIKEY_LOCALE_CURRENCY", "USD"),
            digikey_http_timeout_s=digikey_timeout_s,
            minimax_api_key=os.getenv("MINIMAX_API_KEY"),
            minimax_base_url=os.getenv("MINIMAX_BASE_URL", "https://api.minimax.io"),
            minimax_model=os.getenv("MINIMAX_MODEL", "MiniMax-M2.5-highspeed"),
            enable_minimax_narrator=os.getenv(
                "ENABLE_MINIMAX_NARRATOR", "false"
            ).lower()
            in {"1", "true", "yes", "on"},
            dd_service=os.getenv("DD_SERVICE", "circuit-backend"),
            dd_env=os.getenv("DD_ENV", os.getenv("APP_ENV", "local")),
            dd_version=os.getenv("DD_VERSION", "0.1.0"),
            dd_agent_host=os.getenv("DD_AGENT_HOST", "localhost"),
            dd_trace_enabled=os.getenv(
                "DD_TRACE_ENABLED", os.getenv("DDTRACE_ENABLED", "false")
            ).lower()
            in {"1", "true", "yes", "on"},
            dd_logs_injection=os.getenv("DD_LOGS_INJECTION", "true").lower()
            in {"1", "true", "yes", "on"},
        )


settings = Config.load()
