"""setup_cnpj_optional

Make cnpj nullable in empresas and replace full unique constraint
with a partial unique index (only when cnpj IS NOT NULL).
This allows the first-access setup to work without a CNPJ.

Revision ID: a57f116b294b
Revises: e28d91864e52
Create Date: 2026-05-03 07:58:00.000000

"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "a57f116b294b"
down_revision: Union[str, None] = "e28d91864e52"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Drop the existing full unique constraint on cnpj
    op.drop_constraint("uq_empresas_cnpj", "empresas", type_="unique")

    # Make cnpj nullable
    op.alter_column("empresas", "cnpj", existing_type=sa.String(14), nullable=True)

    # Add partial unique index — only enforces uniqueness when cnpj IS NOT NULL
    op.execute(
        "CREATE UNIQUE INDEX uq_empresas_cnpj_notnull "
        "ON empresas (cnpj) WHERE cnpj IS NOT NULL"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS uq_empresas_cnpj_notnull")
    op.alter_column("empresas", "cnpj", existing_type=sa.String(14), nullable=False)
    op.create_unique_constraint("uq_empresas_cnpj", "empresas", ["cnpj"])
