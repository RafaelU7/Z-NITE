"""
Pacote de modelos — importação centralizada.

A ordem de importação segue as dependências de FK:
  empresa → usuario → tributacao → produto → estoque → caixa → venda → fiscal → auditoria
  empresa → numeracao_fiscal (dependência direta)

SQLAlchemy precisa que todos os modelos estejam importados antes de
`Base.metadata.create_all()` ou de `alembic upgrade head` detectá-los.
"""
from .base import Base, TimestampMixin, UUIDPrimaryKeyMixin  # noqa: F401
from .enums import (  # noqa: F401
    AmbienteFiscal,
    FormaPagamento,
    ModalidadeBCICMS,
    ModalidadeBCICMSST,
    OrigemMercadoria,
    PerfilUsuario,
    RegimeTributario,
    StatusDocumentoFiscal,
    StatusSessaoCaixa,
    StatusVenda,
    TipoDocumentoFiscal,
    TipoMovimentacaoCaixa,
    TipoMovimentacaoEstoque,
    TipoUnidade,
)
from .empresa import Empresa  # noqa: F401
from .numeracao_fiscal import SequenciaFiscal  # noqa: F401
from .usuario import Usuario  # noqa: F401
from .tributacao import PerfilTributario  # noqa: F401
from .produto import Categoria, ProdutoEAN, Produto, UnidadeMedida  # noqa: F401
from .estoque import Estoque, LocalEstoque, MovimentacaoEstoque  # noqa: F401
from .caixa import Caixa, MovimentacaoCaixa, SessaoCaixa  # noqa: F401
from .venda import ItemVenda, PagamentoVenda, Venda  # noqa: F401
from .fiscal import DocumentoFiscal  # noqa: F401
from .auditoria import LogAuditoria  # noqa: F401

__all__ = [
    # Base
    "Base",
    # Empresa
    "Empresa",
    # Numeração fiscal
    "SequenciaFiscal",
    # Usuário
    "Usuario",
    # Tributação
    "PerfilTributario",
    # Produto
    "Categoria",
    "UnidadeMedida",
    "Produto",
    "ProdutoEAN",
    # Estoque
    "LocalEstoque",
    "Estoque",
    "MovimentacaoEstoque",
    # Caixa
    "Caixa",
    "SessaoCaixa",
    "MovimentacaoCaixa",
    # Venda
    "Venda",
    "ItemVenda",
    "PagamentoVenda",
    # Fiscal
    "DocumentoFiscal",
    # Auditoria
    "LogAuditoria",
]
