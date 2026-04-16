from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, func, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Base declarativa para todos os modelos do Zênite PDV."""
    pass


class UUIDPrimaryKeyMixin:
    """
    Chave primária UUID gerada no lado Python (uuid4).
    Compatível com geração offline no frontend — o cliente pode gerar o UUID
    antes de enviar ao servidor, garantindo idempotência na sincronização.
    """
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        # server_default como fallback para inserções raw SQL
        server_default=text("gen_random_uuid()"),
    )


class TimestampMixin:
    """
    Campos de auditoria temporal em toda entidade persistida.
    Nota: onupdate no ORM atualiza apenas via Session.flush().
    Para atualizações diretas via SQL, um trigger PostgreSQL é recomendado.
    """
    criado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    atualizado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
