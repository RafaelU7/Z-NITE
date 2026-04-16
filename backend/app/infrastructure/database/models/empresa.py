"""
Modelo: Empresa

Configuração central da empresa — regime tributário, endereço, numeração fiscal,
credenciais do provedor fiscal externo e configuração do ambiente SEFAZ.

Decisão arquitetural:
  - Suporte a múltiplas empresas no mesmo banco (multi-tenant futuro) via empresa_id
    nas demais tabelas. Por enquanto, o sistema opera com empresa única.
  - CSC (Código de Segurança do Contribuinte) separado por ambiente
    para evitar mistura de credenciais produção / homologação.
  - A chave de API do provedor fiscal é armazenada criptografada pelo backend
    antes de persistir (responsabilidade da camada de serviço).
"""
from __future__ import annotations

from typing import Optional

from sqlalchemy import CHAR, Boolean, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from .enums import AmbienteFiscal, RegimeTributario


class Empresa(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "empresas"
    __table_args__ = (
        UniqueConstraint("cnpj", name="uq_empresas_cnpj"),
        {"comment": "Configuração central da empresa e parâmetros fiscais"},
    )

    # Identificação
    razao_social: Mapped[str] = mapped_column(String(150), nullable=False)
    nome_fantasia: Mapped[Optional[str]] = mapped_column(String(150))
    cnpj: Mapped[str] = mapped_column(
        String(14),
        nullable=False,
        comment="Apenas dígitos, sem formatação",
    )
    inscricao_estadual: Mapped[Optional[str]] = mapped_column(String(20))
    inscricao_municipal: Mapped[Optional[str]] = mapped_column(String(20))

    # Regime tributário
    regime_tributario: Mapped[RegimeTributario] = mapped_column(
        String(5),
        nullable=False,
        comment="SN=Simples Nacional | LP=Lucro Presumido | LR=Lucro Real",
    )

    # Endereço
    end_logradouro: Mapped[Optional[str]] = mapped_column(String(200))
    end_numero: Mapped[Optional[str]] = mapped_column(String(10))
    end_complemento: Mapped[Optional[str]] = mapped_column(String(100))
    end_bairro: Mapped[Optional[str]] = mapped_column(String(100))
    end_municipio: Mapped[Optional[str]] = mapped_column(String(100))
    end_uf: Mapped[Optional[str]] = mapped_column(CHAR(2))
    end_cep: Mapped[Optional[str]] = mapped_column(
        String(8),
        comment="Apenas dígitos, sem formatação",
    )
    end_codigo_ibge: Mapped[Optional[str]] = mapped_column(
        String(7),
        comment="Código IBGE do município para NF-e",
    )

    telefone: Mapped[Optional[str]] = mapped_column(String(15))
    email: Mapped[Optional[str]] = mapped_column(String(200))

    # ---------------------------------------------------------------------------
    # Configuração Fiscal NF-e / NFC-e
    # ---------------------------------------------------------------------------
    ambiente_fiscal: Mapped[AmbienteFiscal] = mapped_column(
        String(1),
        nullable=False,
        default=AmbienteFiscal.HOMOLOGACAO,
        comment="1=Produção | 2=Homologação. Iniciar sempre em Homologação.",
    )

    # Série padrão — a numeração sequencial fica em SequenciaFiscal (SELECT FOR UPDATE)
    serie_nfce: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=1,
        comment="Série padrão da NFC-e (geralmente 1). Numeração em sequencias_fiscais.",
    )
    # Numeração NF-e
    serie_nfe: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=1,
        comment="Série padrão da NF-e. Numeração em sequencias_fiscais.",
    )
    # REMOVIDO: proximo_numero_nfce / proximo_numero_nfe
    # Motivo: race condition com múltiplos caixas simultâneos.
    # Use SequenciaFiscal com SELECT FOR UPDATE para numeração atômica.

    # CSC — Código de Segurança do Contribuinte (NFC-e)
    # Emitido pelo SEFAZ estadual, necessário para o QR Code da NFC-e
    csc_id_producao: Mapped[Optional[str]] = mapped_column(
        String(6),
        comment="ID do CSC em ambiente de Produção",
    )
    csc_token_producao: Mapped[Optional[str]] = mapped_column(
        String(36),
        comment="Token CSC em ambiente de Produção",
    )
    csc_id_homologacao: Mapped[Optional[str]] = mapped_column(String(6))
    csc_token_homologacao: Mapped[Optional[str]] = mapped_column(String(36))

    # Provedor fiscal externo (Focus NFe, PlugNotas, etc.)
    fiscal_provider_nome: Mapped[Optional[str]] = mapped_column(
        String(50),
        comment="Ex: focus_nfe | plugnotas",
    )
    fiscal_provider_api_key: Mapped[Optional[str]] = mapped_column(
        String(500),
        comment="Chave de API — armazenada criptografada pela camada de serviço",
    )
    fiscal_provider_cnpj_emissor: Mapped[Optional[str]] = mapped_column(
        String(14),
        comment="CNPJ registrado no provedor fiscal (pode diferir do CNPJ principal em testes)",
    )

    ativo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    # Relationships
    usuarios: Mapped[list["Usuario"]] = relationship(  # noqa: F821
        "Usuario",
        back_populates="empresa",
        lazy="select",
    )
    sequencias_fiscais: Mapped[list["SequenciaFiscal"]] = relationship(  # noqa: F821
        "SequenciaFiscal",
        back_populates="empresa",
        lazy="select",
        cascade="all, delete-orphan",
    )
