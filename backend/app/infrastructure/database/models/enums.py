"""
Enumerações centralizadas do domínio Zênite PDV.

Todos os enums usam str como base para:
  - Serialização transparente em JSON / Pydantic
  - Armazenamento como VARCHAR no PostgreSQL (native_enum=False)
    facilitando ALTER TABLE em produção sem RENAME TYPE
  - Legibilidade nos logs e na auditoria
"""
from __future__ import annotations

from enum import Enum as PyEnum


# ---------------------------------------------------------------------------
# Empresa / Configuração fiscal
# ---------------------------------------------------------------------------

class RegimeTributario(str, PyEnum):
    SIMPLES_NACIONAL = "SN"
    SIMPLES_NACIONAL_EXCESSO = "SNE"   # excesso de sublimite
    LUCRO_PRESUMIDO = "LP"
    LUCRO_REAL = "LR"


class AmbienteFiscal(str, PyEnum):
    PRODUCAO = "1"
    HOMOLOGACAO = "2"


# ---------------------------------------------------------------------------
# Unidade de medida
# ---------------------------------------------------------------------------

class TipoUnidade(str, PyEnum):
    UNITARIA = "unitaria"     # venda por unidade inteira
    PESAVEL = "pesavel"       # venda por peso (kg/g/etc.)
    VOLUME = "volume"         # litros/ml


# ---------------------------------------------------------------------------
# Produto — Origem da mercadoria (campo "orig" NF-e)
# ---------------------------------------------------------------------------

class OrigemMercadoria(str, PyEnum):
    NACIONAL = "0"
    ESTRANGEIRA_IMPORTACAO_DIRETA = "1"
    ESTRANGEIRA_MERCADO_INTERNO = "2"
    NACIONAL_CONTEUDO_IMPORT_SUP_40 = "3"
    NACIONAL_PRODUCAO_BASICA = "4"
    NACIONAL_CONTEUDO_IMPORT_INF_40 = "5"
    ESTRANGEIRA_IMPORTACAO_DIRETA_SEM_SIMILAR = "6"
    ESTRANGEIRA_MERCADO_INTERNO_SEM_SIMILAR = "7"
    NACIONAL_CONTEUDO_IMPORT_SUP_70 = "8"


# ---------------------------------------------------------------------------
# Estoque
# ---------------------------------------------------------------------------

class TipoMovimentacaoEstoque(str, PyEnum):
    ENTRADA_COMPRA = "entrada_compra"
    SAIDA_VENDA = "saida_venda"
    AJUSTE_POSITIVO = "ajuste_positivo"
    AJUSTE_NEGATIVO = "ajuste_negativo"
    INVENTARIO = "inventario"
    ENTRADA_DEVOLUCAO_CLIENTE = "entrada_devolucao_cliente"
    SAIDA_DEVOLUCAO_FORNECEDOR = "saida_devolucao_fornecedor"
    ENTRADA_TRANSFERENCIA = "entrada_transferencia"
    SAIDA_TRANSFERENCIA = "saida_transferencia"
    PERDA = "perda"


# ---------------------------------------------------------------------------
# Caixa
# ---------------------------------------------------------------------------

class StatusSessaoCaixa(str, PyEnum):
    ABERTA = "aberta"
    FECHADA = "fechada"


class TipoMovimentacaoCaixa(str, PyEnum):
    SANGRIA = "sangria"       # retirada de dinheiro
    SUPRIMENTO = "suprimento" # reforço de dinheiro


# ---------------------------------------------------------------------------
# Venda
# ---------------------------------------------------------------------------

class StatusVenda(str, PyEnum):
    EM_ABERTO = "em_aberto"     # sendo lançada no PDV
    CONCLUIDA = "concluida"
    CANCELADA = "cancelada"


class FormaPagamento(str, PyEnum):
    """
    Códigos conforme tabela B.18 do Manual de Orientação do Contribuinte NF-e.
    """
    DINHEIRO = "01"
    CHEQUE = "02"
    CARTAO_CREDITO = "03"
    CARTAO_DEBITO = "04"
    CREDITO_LOJA = "05"
    VALE_ALIMENTACAO = "10"
    VALE_REFEICAO = "11"
    VALE_PRESENTE = "12"
    VALE_COMBUSTIVEL = "13"
    PIX = "17"
    OUTROS = "99"


# ---------------------------------------------------------------------------
# Fiscal
# ---------------------------------------------------------------------------

class TipoDocumentoFiscal(str, PyEnum):
    NFCE = "nfce"    # NFC-e (consumidor final, PDV)
    NFE = "nfe"      # NF-e (B2B, entradas)
    SAT = "sat"      # SAT-CF-e (São Paulo)


class StatusDocumentoFiscal(str, PyEnum):
    PENDENTE = "pendente"           # aguardando emissão
    EMITIDA = "emitida"             # autorizada pela SEFAZ
    CANCELADA = "cancelada"         # cancelada dentro do prazo legal
    REJEITADA = "rejeitada"         # rejeitada pela SEFAZ (erro no XML)
    EM_CONTINGENCIA = "em_contingencia"  # emitida offline, aguardando SEFAZ
    INUTILIZADA = "inutilizada"     # numeração inutilizada
    ERRO = "erro"                   # erro não classificado


# ---------------------------------------------------------------------------
# Usuário / Segurança
# ---------------------------------------------------------------------------

class PerfilUsuario(str, PyEnum):
    SUPER_ADMIN = "super_admin"       # acesso total ao sistema
    ADMIN = "admin"                   # administrador da empresa
    GERENTE = "gerente"               # gestão sem alguns acessos críticos
    OPERADOR_CAIXA = "operador_caixa" # apenas PDV e operações de caixa
    ESTOQUISTA = "estoquista"         # gestão de estoque e produtos


# ---------------------------------------------------------------------------
# Tributação — Modalidade de base de cálculo ICMS
# ---------------------------------------------------------------------------

class ModalidadeBCICMS(str, PyEnum):
    MARGEM_VALOR_AGREGADO = "0"
    PAUTA = "1"
    PRECO_TABELADO = "2"
    VALOR_OPERACAO = "3"


class ModalidadeBCICMSST(str, PyEnum):
    PRECO_TABELADO_MAXIMO = "0"
    LISTA_NEGATIVA = "1"
    LISTA_POSITIVA = "2"
    LISTA_NEUTRA = "3"
    MARGEM_VALOR_AGREGADO = "4"
    PAUTA = "5"
    VALOR_OPERACAO = "6"


# ---------------------------------------------------------------------------
# Modo de emissão da venda
# ---------------------------------------------------------------------------

class TipoEmissao(str, PyEnum):
    FISCAL = "FISCAL"       # emite NFC-e via SEFAZ
    GERENCIAL = "GERENCIAL" # apenas registra venda, sem documento fiscal
