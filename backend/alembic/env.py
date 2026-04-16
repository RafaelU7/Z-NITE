"""
Alembic env.py — configurado para uso com dotenv e SQLAlchemy 2.0.

Suporta dois modos:
  - offline: gera SQL sem conexão ao banco (útil para review de migrations)
  - online: aplica diretamente no banco (padrão)

A DATABASE_URL é lida do arquivo .env para evitar hardcode de credenciais.
"""
from __future__ import annotations

import os
from logging.config import fileConfig

from alembic import context
from dotenv import load_dotenv
from sqlalchemy import engine_from_config, pool

# Carregar variáveis de ambiente do .env antes de tudo
load_dotenv()

# Importar todos os modelos para que o Alembic os detecte no autogenerate
from app.infrastructure.database.models import Base  # noqa: E402

# Configuração do Alembic
config = context.config

# Injetar DATABASE_URL do ambiente no config do Alembic
database_url = os.environ.get("DATABASE_URL")
if not database_url:
    raise RuntimeError(
        "DATABASE_URL não encontrada. Crie o arquivo .env baseado em .env.example"
    )
config.set_main_option("sqlalchemy.url", database_url)

# Configurar logging se houver config file
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Metadados de todos os modelos para autogenerate
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """
    Modo offline: gera SQL sem conectar ao banco.
    Útil para revisar a migration antes de aplicar.
    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        # Detectar alterações em colunas (tipo, nullable, default)
        compare_type=True,
        compare_server_default=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """
    Modo online: aplica diretamente no banco.
    """
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
            compare_server_default=True,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
