"""Application configuration loaded from environment variables."""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv
from pydantic import BaseModel, Field

BASE_DIR = Path(__file__).resolve().parent.parent


class Config(BaseModel):
    """Runtime configuration resolved from environment variables."""

    app_name: str = Field(default="Circuit Hackathon Backend")
    app_env: str = Field(default="local")
    log_level: str = Field(default="INFO")
    aws_region: str = Field(default="us-east-1")
    neo4j_uri: str = Field(default="bolt://localhost:7687")
    neo4j_user: str = Field(default="neo4j")
    neo4j_password: str = Field(default="neo4j")
    ddtrace_enabled: bool = Field(default=False)

    @property
    def is_production(self) -> bool:
        return self.app_env.lower() in {"prod", "production"}

    @classmethod
    def load(cls) -> "Config":
        env_name = os.getenv("APP_ENV", os.getenv("ENV", "local")).lower()
        if env_name not in {"prod", "production"}:
            load_dotenv(BASE_DIR / ".env", override=False)

        return cls(
            app_name=os.getenv("APP_NAME", "Circuit Hackathon Backend"),
            app_env=os.getenv("APP_ENV", os.getenv("ENV", "local")),
            log_level=os.getenv("LOG_LEVEL", "INFO"),
            aws_region=os.getenv("AWS_REGION", "us-east-1"),
            neo4j_uri=os.getenv("NEO4J_URI", "bolt://localhost:7687"),
            neo4j_user=os.getenv("NEO4J_USER", "neo4j"),
            neo4j_password=os.getenv("NEO4J_PASSWORD", "neo4j"),
            ddtrace_enabled=os.getenv("DDTRACE_ENABLED", "false").lower()
            in {"1", "true", "yes", "on"},
        )


settings = Config.load()
