from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import Field, PostgresDsn, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Aplicação
    app_name: str = "Zênite PDV"
    app_env: Literal["development", "staging", "production"] = "development"
    debug: bool = False
    log_level: str = "INFO"

    # Banco de Dados
    database_url: str = Field(..., description="PostgreSQL connection string")
    db_pool_size: int = 10
    db_max_overflow: int = 20
    db_pool_timeout: int = 30

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # Segurança / JWT
    secret_key: str = Field(..., min_length=32, description="Chave secreta para JWT")
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 480  # 8 horas
    refresh_token_expire_days: int = 30

    # CORS
    cors_origins: list[str] = ["http://localhost:5173", "http://localhost:3000"]

    # Fiscal
    fiscal_provider_default: str = "focus_nfe"
    focus_nfe_token: str = ""
    focus_nfe_base_url: str = "https://homologacao.focusnfe.com.br"
    focus_nfe_timeout: int = 30
    fiscal_max_tentativas: int = 5

    @field_validator("database_url", mode="before")
    @classmethod
    def validate_db_url(cls, v: str) -> str:
        if not v.startswith("postgresql"):
            raise ValueError("DATABASE_URL deve ser uma URL PostgreSQL")
        return v

    @property
    def async_database_url(self) -> str:
        """URL assíncrona para asyncpg (FastAPI). Alembic usa database_url (sync).

        Neon e outros provedores cloud fornecem URLs com ?sslmode=require e
        opcionalmente &channel_binding=require (parâmetros libpq/psycopg2).
        O asyncpg/SQLAlchemy 2.0 exige ?ssl=require e não reconhece channel_binding.
        Esta conversão é segura: em dev local sem esses parâmetros a URL não muda.
        """
        url = self.database_url.replace(
            "postgresql://", "postgresql+asyncpg://", 1
        ).replace("postgresql+psycopg2://", "postgresql+asyncpg://", 1)
        # Converte parâmetro SSL do formato psycopg2 para asyncpg
        url = url.replace("sslmode=require", "ssl=require")
        url = url.replace("sslmode=prefer", "ssl=prefer")
        url = url.replace("sslmode=disable", "ssl=disable")
        # Remove channel_binding — parâmetro libpq, não suportado pelo asyncpg
        import re
        url = re.sub(r"[&?]channel_binding=[^&]*", "", url)
        return url

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"

    @property
    def is_development(self) -> bool:
        return self.app_env == "development"


@lru_cache
def get_settings() -> Settings:
    return Settings()
