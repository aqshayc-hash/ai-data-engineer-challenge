"""Configuration management using Pydantic."""

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class DatabaseConfig(BaseSettings):
    """Database configuration."""

    model_config = SettingsConfigDict(env_prefix="POSTGRES_", extra="ignore")

    user: str = "dagster"
    password: str = "dagster"
    host: str = "postgres"
    port: int = 5432
    db: str = "mama_health"

    @property
    def connection_string(self) -> str:
        """Generate SQLAlchemy connection string."""
        return (
            f"postgresql+psycopg2://{self.user}:{self.password}@{self.host}:{self.port}/{self.db}"
        )


class RedditConfig(BaseSettings):
    """Reddit API configuration."""

    model_config = SettingsConfigDict(env_prefix="REDDIT_", extra="ignore")

    client_id: str
    client_secret: str
    user_agent: str
    username: str = ""
    password: str = ""
    request_timeout: int = 30
    rate_limit_per_minute: int = 60


class GoogleConfig(BaseSettings):
    """Google API configuration for Gemini."""

    model_config = SettingsConfigDict(env_prefix="GOOGLE_", extra="ignore")

    api_key: str = ""


class LLMConfig(BaseSettings):
    """Language Model configuration."""

    model_config = SettingsConfigDict(env_prefix="LLM_", extra="ignore")

    model: str = "gemini/gemini-pro"
    temperature: float = 0.3
    max_tokens: int = 1000
    request_timeout: int = 60


class PipelineConfig(BaseSettings):
    """Pipeline execution configuration."""

    model_config = SettingsConfigDict(env_prefix="", extra="ignore")

    target_subreddit: str = "Crohns"
    posts_limit: int = 100
    comments_limit: int = 50
    search_limit_days: int = 30


class AppConfig(BaseSettings):
    """Main application configuration.

    Aggregates all sub-configs. Each nested config reads its own env vars
    independently via its own prefix (e.g. REDDIT_*, GOOGLE_*, LLM_*).
    Supports loading from a .env file for local development.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    database: DatabaseConfig = Field(default_factory=DatabaseConfig)  # type: ignore[arg-type]
    reddit: RedditConfig = Field(default_factory=RedditConfig)  # type: ignore[arg-type]
    google: GoogleConfig = Field(default_factory=GoogleConfig)  # type: ignore[arg-type]
    llm: LLMConfig = Field(default_factory=LLMConfig)  # type: ignore[arg-type]
    pipeline: PipelineConfig = Field(default_factory=PipelineConfig)  # type: ignore[arg-type]
    log_level: str = "INFO"
