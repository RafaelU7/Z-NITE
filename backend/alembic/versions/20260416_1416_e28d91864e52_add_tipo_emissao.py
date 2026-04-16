"""add_tipo_emissao

Revision ID: e28d91864e52
Revises: ded24518b32b
Create Date: 2026-04-16 14:16:29.964228

"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e28d91864e52'
down_revision: Union[str, None] = 'ded24518b32b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    tipo_emissao_enum = sa.Enum('FISCAL', 'GERENCIAL', name='tipo_emissao_enum')
    tipo_emissao_enum.create(op.get_bind(), checkfirst=True)
    op.add_column('vendas', sa.Column(
        'tipo_emissao',
        tipo_emissao_enum,
        server_default='FISCAL',
        nullable=False,
        comment='FISCAL = emite NFC-e; GERENCIAL = registra sem documento fiscal',
    ))


def downgrade() -> None:
    op.drop_column('vendas', 'tipo_emissao')
    op.execute("DROP TYPE IF EXISTS tipo_emissao_enum")
