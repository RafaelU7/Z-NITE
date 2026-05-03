"""
Router Gerencial — retaguarda mínima para gerentes.

Endpoints (todos requerem perfil GERENTE ou superior):
  GET  /dashboard                — KPIs do dia
  GET  /produtos                 — lista produtos (busca + paginação)
  POST /produtos                 — cria produto
  PATCH /produtos/{id}           — atualiza produto (preço, descrição, status)
  GET  /unidades                 — lista unidades de medida disponíveis
  GET  /perfis-tributarios       — lista perfis tributários ativos
  GET  /usuarios                 — lista usuários da empresa
  POST /usuarios                 — cria operador/estoquista
  PATCH /usuarios/{id}/status    — ativa ou desativa usuário
  GET  /sessoes                  — lista sessões de caixa recentes
"""
from __future__ import annotations

import uuid
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from typing import List, Optional
from uuid import UUID

import httpx

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import cast, Date, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.core.database import get_async_session
from app.core.dependencies import require_perfil
from app.infrastructure.database.models.caixa import Caixa, SessaoCaixa
from app.infrastructure.database.models.enums import (
    PerfilUsuario,
    StatusSessaoCaixa,
    StatusVenda,
    TipoEmissao,
    TipoMovimentacaoEstoque,
)
from app.infrastructure.database.models.estoque import Estoque, LocalEstoque, MovimentacaoEstoque
from app.infrastructure.database.models.produto import Categoria, Produto, UnidadeMedida
from app.infrastructure.database.models.tributacao import PerfilTributario
from app.infrastructure.database.models.usuario import Usuario
from app.infrastructure.database.models.venda import PagamentoVenda, Venda
from app.infrastructure.security.password_handler import hash_password, hash_pin

router = APIRouter(prefix="/gerencial", tags=["Gerencial"])

_MIN_PERFIL = PerfilUsuario.GERENTE

# ---------------------------------------------------------------------------
# Labels de formas de pagamento
# ---------------------------------------------------------------------------
_FORMA_LABEL: dict[str, str] = {
    "01": "Dinheiro",
    "02": "Cheque",
    "03": "Cartão Crédito",
    "04": "Cartão Débito",
    "05": "Crédito Loja",
    "10": "Vale Alimentação",
    "11": "Vale Refeição",
    "12": "Vale Presente",
    "13": "Vale Combustível",
    "17": "Pix",
    "99": "Outros",
}

# ---------------------------------------------------------------------------
# DTOs de saída / entrada
# ---------------------------------------------------------------------------


class PagamentoPorFormaDTO(BaseModel):
    forma: str
    label: str
    total: Decimal
    qtd: int


class DashboardDTO(BaseModel):
    data_referencia: str
    # Dia
    total_vendas: Decimal
    qtd_vendas: int
    ticket_medio: Decimal
    por_forma_pagamento: List[PagamentoPorFormaDTO]
    sessoes_abertas: int
    # Semana / Mês
    total_semana: Decimal
    qtd_semana: int
    total_mes: Decimal
    qtd_mes: int
    # Por operador (dia)
    por_operador: List[dict]
    # Fiscal vs Gerencial (dia)
    total_fiscal: Decimal
    total_gerencial: Decimal


class ProdutoGerencialDTO(BaseModel):
    id: UUID
    sku: Optional[str] = None
    codigo_barras_principal: Optional[str] = None
    descricao: str
    descricao_pdv: Optional[str] = None
    preco_venda: Decimal
    unidade_id: UUID
    unidade_codigo: Optional[str] = None
    perfil_tributario_id: Optional[UUID] = None
    categoria_id: Optional[UUID] = None
    controla_estoque: bool
    ativo: bool
    destaque_pdv: bool

    model_config = {"from_attributes": True}


class PaginatedProdutos(BaseModel):
    items: List[ProdutoGerencialDTO]
    total: int
    page: int
    per_page: int


class ProdutoCreateRequest(BaseModel):
    descricao: str = Field(..., min_length=2, max_length=200)
    descricao_pdv: Optional[str] = Field(None, max_length=60)
    codigo_barras_principal: Optional[str] = Field(None, max_length=14)
    sku: Optional[str] = Field(None, max_length=50)
    preco_venda: Decimal = Field(..., ge=0)
    unidade_id: UUID
    perfil_tributario_id: Optional[UUID] = None
    categoria_id: Optional[UUID] = None
    controla_estoque: bool = True
    ativo: bool = False
    destaque_pdv: bool = False


class ProdutoPatchRequest(BaseModel):
    descricao: Optional[str] = Field(None, min_length=2, max_length=200)
    descricao_pdv: Optional[str] = Field(None, max_length=60)
    preco_venda: Optional[Decimal] = Field(None, ge=0)
    ativo: Optional[bool] = None
    destaque_pdv: Optional[bool] = None
    perfil_tributario_id: Optional[UUID] = None


class UnidadeDTO(BaseModel):
    id: UUID
    codigo: str
    descricao: str

    model_config = {"from_attributes": True}


class PerfilTributarioSimpleDTO(BaseModel):
    id: UUID
    nome: str

    model_config = {"from_attributes": True}


class CategoriaDTO(BaseModel):
    id: UUID
    nome: str
    categoria_pai_id: Optional[UUID] = None
    ativo: bool

    model_config = {"from_attributes": True}


class UsuarioListDTO(BaseModel):
    id: UUID
    nome: str
    email: str
    perfil: str
    codigo_operador: Optional[str] = None
    ativo: bool
    ultimo_acesso: Optional[str] = None

    model_config = {"from_attributes": True}


class UsuarioCreateRequest(BaseModel):
    nome: str = Field(..., min_length=2, max_length=150)
    email: EmailStr
    senha: str = Field(..., min_length=6, max_length=200)
    perfil: PerfilUsuario = PerfilUsuario.OPERADOR_CAIXA
    codigo_operador: Optional[str] = Field(None, max_length=20)
    pin: Optional[str] = Field(None, min_length=4, max_length=6)


class SessaoListDTO(BaseModel):
    id: UUID
    caixa_id: UUID
    caixa_descricao: Optional[str] = None
    caixa_numero: int
    operador_id: UUID
    operador_nome: str
    status: str
    data_abertura: str
    data_fechamento: Optional[str] = None
    total_liquido: Decimal
    quantidade_vendas: int
    # Fechamento
    diferenca_fechamento: Optional[Decimal] = None
    saldo_informado_fechamento: Optional[Decimal] = None
    saldo_sistema_fechamento: Optional[Decimal] = None
    total_dinheiro: Decimal = Decimal("0")
    total_pix: Decimal = Decimal("0")
    total_cartao_debito: Decimal = Decimal("0")
    total_cartao_credito: Decimal = Decimal("0")
    total_outros: Decimal = Decimal("0")
    ticket_medio: Optional[Decimal] = None


class RelatorioDiarioDTO(BaseModel):
    data_referencia: str
    total_vendas: Decimal
    qtd_vendas: int
    ticket_medio: Decimal
    por_forma_pagamento: List[PagamentoPorFormaDTO]
    sessoes_abertas: int
    sessoes_fechadas: int
    diferenca_total: Decimal
    sessoes: List[SessaoListDTO]


class CaixaDTO(BaseModel):
    id: UUID
    numero: int
    descricao: Optional[str] = None
    numero_serie: Optional[str] = None
    ativo: bool

    model_config = {"from_attributes": True}


class CaixaCreateRequest(BaseModel):
    numero: int = Field(..., ge=1)
    descricao: Optional[str] = Field(None, max_length=100)
    numero_serie: Optional[str] = Field(None, max_length=50)


# ---------------------------------------------------------------------------
# Helpers de hierarquia de perfis
# ---------------------------------------------------------------------------
_PERFIL_NIVEL = {
    PerfilUsuario.OPERADOR_CAIXA: 0,
    PerfilUsuario.ESTOQUISTA: 1,
    PerfilUsuario.GERENTE: 2,
    PerfilUsuario.ADMIN: 3,
    PerfilUsuario.SUPER_ADMIN: 4,
}


def _nivel(perfil: PerfilUsuario) -> int:
    return _PERFIL_NIVEL.get(perfil, -1)


# ---------------------------------------------------------------------------
# DASHBOARD
# ---------------------------------------------------------------------------

@router.get("/dashboard", response_model=DashboardDTO)
async def dashboard(
    gerente: Usuario = Depends(require_perfil(_MIN_PERFIL)),
    session: AsyncSession = Depends(get_async_session),
) -> DashboardDTO:
    empresa_id = gerente.empresa_id
    today = date.today()

    # Totais das vendas concluídas hoje
    venda_r = await session.execute(
        select(
            func.count(Venda.id).label("qtd"),
            func.coalesce(func.sum(Venda.total_liquido), 0).label("total"),
        ).where(
            Venda.empresa_id == empresa_id,
            Venda.status == StatusVenda.CONCLUIDA,
            cast(Venda.data_venda, Date) == today,
        )
    )
    v = venda_r.one()
    qtd = int(v.qtd)
    total = Decimal(str(v.total))
    ticket = (total / qtd) if qtd else Decimal("0")

    # Breakdown por forma de pagamento
    pag_r = await session.execute(
        select(
            PagamentoVenda.forma_pagamento.label("forma"),
            func.count(PagamentoVenda.id).label("qtd"),
            func.coalesce(func.sum(PagamentoVenda.valor), 0).label("total"),
        )
        .join(Venda, PagamentoVenda.venda_id == Venda.id)
        .where(
            Venda.empresa_id == empresa_id,
            Venda.status == StatusVenda.CONCLUIDA,
            cast(Venda.data_venda, Date) == today,
        )
        .group_by(PagamentoVenda.forma_pagamento)
    )
    por_forma = [
        PagamentoPorFormaDTO(
            forma=str(row.forma),
            label=_FORMA_LABEL.get(str(row.forma), str(row.forma)),
            total=Decimal(str(row.total)),
            qtd=int(row.qtd),
        )
        for row in pag_r.all()
    ]

    # Sessões abertas
    sessoes_r = await session.execute(
        select(func.count(SessaoCaixa.id)).where(
            SessaoCaixa.empresa_id == empresa_id,
            SessaoCaixa.status == StatusSessaoCaixa.ABERTA,
        )
    )
    sessoes_abertas = int(sessoes_r.scalar() or 0)

    # Semana (últimos 7 dias)
    week_start = today - timedelta(days=6)
    sem_r = await session.execute(
        select(
            func.count(Venda.id).label("qtd"),
            func.coalesce(func.sum(Venda.total_liquido), 0).label("total"),
        ).where(
            Venda.empresa_id == empresa_id,
            Venda.status == StatusVenda.CONCLUIDA,
            cast(Venda.data_venda, Date) >= week_start,
            cast(Venda.data_venda, Date) <= today,
        )
    )
    sem = sem_r.one()

    # Mês (mês corrente)
    mes_start = today.replace(day=1)
    mes_r = await session.execute(
        select(
            func.count(Venda.id).label("qtd"),
            func.coalesce(func.sum(Venda.total_liquido), 0).label("total"),
        ).where(
            Venda.empresa_id == empresa_id,
            Venda.status == StatusVenda.CONCLUIDA,
            cast(Venda.data_venda, Date) >= mes_start,
            cast(Venda.data_venda, Date) <= today,
        )
    )
    mes = mes_r.one()

    # Por operador (dia)
    op_r = await session.execute(
        select(
            Usuario.id.label("operador_id"),
            Usuario.nome.label("operador_nome"),
            func.count(Venda.id).label("qtd"),
            func.coalesce(func.sum(Venda.total_liquido), 0).label("total"),
        )
        .join(Usuario, Venda.operador_id == Usuario.id)
        .where(
            Venda.empresa_id == empresa_id,
            Venda.status == StatusVenda.CONCLUIDA,
            cast(Venda.data_venda, Date) == today,
        )
        .group_by(Usuario.id, Usuario.nome)
        .order_by(func.sum(Venda.total_liquido).desc())
    )
    por_operador = [
        {"operador_id": str(row.operador_id), "nome": row.operador_nome,
         "qtd": int(row.qtd), "total": float(row.total)}
        for row in op_r.all()
    ]

    # Fiscal vs Gerencial (dia)
    emissao_r = await session.execute(
        select(
            Venda.tipo_emissao.label("tipo"),
            func.coalesce(func.sum(Venda.total_liquido), 0).label("total"),
        )
        .where(
            Venda.empresa_id == empresa_id,
            Venda.status == StatusVenda.CONCLUIDA,
            cast(Venda.data_venda, Date) == today,
        )
        .group_by(Venda.tipo_emissao)
    )
    total_fiscal = Decimal("0")
    total_gerencial = Decimal("0")
    for row in emissao_r.all():
        if str(row.tipo) == TipoEmissao.FISCAL:
            total_fiscal = Decimal(str(row.total))
        else:
            total_gerencial = Decimal(str(row.total))

    return DashboardDTO(
        data_referencia=today.isoformat(),
        total_vendas=total,
        qtd_vendas=qtd,
        ticket_medio=ticket.quantize(Decimal("0.01")),
        por_forma_pagamento=por_forma,
        sessoes_abertas=sessoes_abertas,
        total_semana=Decimal(str(sem.total)),
        qtd_semana=int(sem.qtd),
        total_mes=Decimal(str(mes.total)),
        qtd_mes=int(mes.qtd),
        por_operador=por_operador,
        total_fiscal=total_fiscal,
        total_gerencial=total_gerencial,
    )


# ---------------------------------------------------------------------------
# PRODUTOS
# ---------------------------------------------------------------------------

@router.get("/produtos", response_model=PaginatedProdutos)
async def list_produtos(
    q: Optional[str] = Query(None, max_length=100),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    gerente: Usuario = Depends(require_perfil(_MIN_PERFIL)),
    session: AsyncSession = Depends(get_async_session),
) -> PaginatedProdutos:
    empresa_id = gerente.empresa_id
    offset = (page - 1) * per_page

    base = (
        select(Produto)
        .options(joinedload(Produto.unidade))
        .where(Produto.empresa_id == empresa_id)
    )
    if q:
        pattern = f"%{q}%"
        base = base.where(
            Produto.descricao.ilike(pattern)
            | Produto.codigo_barras_principal.ilike(pattern)
            | Produto.sku.ilike(pattern)
        )

    count_r = await session.execute(
        select(func.count()).select_from(base.subquery())
    )
    total = int(count_r.scalar() or 0)

    items_r = await session.execute(
        base.order_by(Produto.descricao).offset(offset).limit(per_page)
    )
    produtos = items_r.unique().scalars().all()

    return PaginatedProdutos(
        items=[
            ProdutoGerencialDTO(
                id=p.id,
                sku=p.sku,
                codigo_barras_principal=p.codigo_barras_principal,
                descricao=p.descricao,
                descricao_pdv=p.descricao_pdv,
                preco_venda=Decimal(str(p.preco_venda)),
                unidade_id=p.unidade_id,
                unidade_codigo=p.unidade.codigo if p.unidade else None,
                perfil_tributario_id=p.perfil_tributario_id,
                categoria_id=p.categoria_id,
                controla_estoque=p.controla_estoque,
                ativo=p.ativo,
                destaque_pdv=p.destaque_pdv,
            )
            for p in produtos
        ],
        total=total,
        page=page,
        per_page=per_page,
    )


@router.post("/produtos", response_model=ProdutoGerencialDTO, status_code=201)
async def create_produto(
    req: ProdutoCreateRequest,
    gerente: Usuario = Depends(require_perfil(_MIN_PERFIL)),
    session: AsyncSession = Depends(get_async_session),
) -> ProdutoGerencialDTO:
    empresa_id = gerente.empresa_id

    # Anti-duplicidade por EAN
    if req.codigo_barras_principal:
        dup_ean = await session.execute(
            select(Produto).where(
                Produto.empresa_id == empresa_id,
                Produto.codigo_barras_principal == req.codigo_barras_principal,
            )
        )
        if dup_ean.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="EAN já cadastrado nesta empresa.",
            )

    # Regra: produto ativo requer perfil tributário
    if req.ativo and not req.perfil_tributario_id:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Produto ativo requer perfil_tributario_id.",
        )

    # Validar unidade
    unid_r = await session.execute(
        select(UnidadeMedida).where(
            UnidadeMedida.id == req.unidade_id,
            UnidadeMedida.empresa_id == empresa_id,
        )
    )
    if not unid_r.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Unidade de medida não encontrada.")

    produto = Produto(
        id=uuid.uuid4(),
        empresa_id=empresa_id,
        descricao=req.descricao,
        descricao_pdv=req.descricao_pdv,
        codigo_barras_principal=req.codigo_barras_principal,
        sku=req.sku,
        preco_venda=req.preco_venda,
        unidade_id=req.unidade_id,
        perfil_tributario_id=req.perfil_tributario_id,
        categoria_id=req.categoria_id,
        controla_estoque=req.controla_estoque,
        ativo=req.ativo,
        destaque_pdv=req.destaque_pdv,
        custo_medio=Decimal("0"),
        estoque_minimo=Decimal("0"),
    )
    session.add(produto)
    await session.flush()
    await session.refresh(produto, ["unidade"])

    return ProdutoGerencialDTO(
        id=produto.id,
        sku=produto.sku,
        codigo_barras_principal=produto.codigo_barras_principal,
        descricao=produto.descricao,
        descricao_pdv=produto.descricao_pdv,
        preco_venda=Decimal(str(produto.preco_venda)),
        unidade_id=produto.unidade_id,
        unidade_codigo=produto.unidade.codigo if produto.unidade else None,
        perfil_tributario_id=produto.perfil_tributario_id,
        categoria_id=produto.categoria_id,
        controla_estoque=produto.controla_estoque,
        ativo=produto.ativo,
        destaque_pdv=produto.destaque_pdv,
    )


@router.patch("/produtos/{produto_id}", response_model=ProdutoGerencialDTO)
async def patch_produto(
    produto_id: UUID,
    req: ProdutoPatchRequest,
    gerente: Usuario = Depends(require_perfil(_MIN_PERFIL)),
    session: AsyncSession = Depends(get_async_session),
) -> ProdutoGerencialDTO:
    empresa_id = gerente.empresa_id

    p_r = await session.execute(
        select(Produto)
        .options(joinedload(Produto.unidade))
        .where(Produto.id == produto_id, Produto.empresa_id == empresa_id)
    )
    produto = p_r.unique().scalar_one_or_none()
    if not produto:
        raise HTTPException(status_code=404, detail="Produto não encontrado.")

    if req.descricao is not None:
        produto.descricao = req.descricao
    if req.descricao_pdv is not None:
        produto.descricao_pdv = req.descricao_pdv
    if req.preco_venda is not None:
        produto.preco_venda = req.preco_venda
    if req.destaque_pdv is not None:
        produto.destaque_pdv = req.destaque_pdv
    if req.perfil_tributario_id is not None:
        produto.perfil_tributario_id = req.perfil_tributario_id
    if req.ativo is not None:
        if req.ativo and not produto.perfil_tributario_id:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Produto ativo requer perfil_tributario_id.",
            )
        produto.ativo = req.ativo

    await session.flush()

    return ProdutoGerencialDTO(
        id=produto.id,
        sku=produto.sku,
        codigo_barras_principal=produto.codigo_barras_principal,
        descricao=produto.descricao,
        descricao_pdv=produto.descricao_pdv,
        preco_venda=Decimal(str(produto.preco_venda)),
        unidade_id=produto.unidade_id,
        unidade_codigo=produto.unidade.codigo if produto.unidade else None,
        perfil_tributario_id=produto.perfil_tributario_id,
        categoria_id=produto.categoria_id,
        controla_estoque=produto.controla_estoque,
        ativo=produto.ativo,
        destaque_pdv=produto.destaque_pdv,
    )


# ---------------------------------------------------------------------------
# UNIDADES E PERFIS TRIBUTÁRIOS (referências para formulários)
# ---------------------------------------------------------------------------

@router.get("/unidades", response_model=List[UnidadeDTO])
async def list_unidades(
    gerente: Usuario = Depends(require_perfil(_MIN_PERFIL)),
    session: AsyncSession = Depends(get_async_session),
) -> List[UnidadeDTO]:
    empresa_id = gerente.empresa_id
    r = await session.execute(
        select(UnidadeMedida)
        .where(UnidadeMedida.empresa_id == empresa_id, UnidadeMedida.ativo.is_(True))
        .order_by(UnidadeMedida.codigo)
    )
    return [UnidadeDTO.model_validate(u) for u in r.scalars().all()]


@router.get("/categorias", response_model=List[CategoriaDTO])
async def list_categorias(
    gerente: Usuario = Depends(require_perfil(_MIN_PERFIL)),
    session: AsyncSession = Depends(get_async_session),
) -> List[CategoriaDTO]:
    empresa_id = gerente.empresa_id
    r = await session.execute(
        select(Categoria)
        .where(
            Categoria.empresa_id == empresa_id,
            Categoria.ativo.is_(True),
        )
        .order_by(Categoria.nome)
    )
    return [CategoriaDTO.model_validate(c) for c in r.scalars().all()]


@router.get("/perfis-tributarios", response_model=List[PerfilTributarioSimpleDTO])
async def list_perfis_tributarios(
    gerente: Usuario = Depends(require_perfil(_MIN_PERFIL)),
    session: AsyncSession = Depends(get_async_session),
) -> List[PerfilTributarioSimpleDTO]:
    empresa_id = gerente.empresa_id
    r = await session.execute(
        select(PerfilTributario)
        .where(
            PerfilTributario.empresa_id == empresa_id,
            PerfilTributario.ativo.is_(True),
        )
        .order_by(PerfilTributario.nome)
    )
    return [PerfilTributarioSimpleDTO.model_validate(p) for p in r.scalars().all()]


# ---------------------------------------------------------------------------
# USUÁRIOS
# ---------------------------------------------------------------------------

@router.get("/usuarios", response_model=List[UsuarioListDTO])
async def list_usuarios(
    gerente: Usuario = Depends(require_perfil(_MIN_PERFIL)),
    session: AsyncSession = Depends(get_async_session),
) -> List[UsuarioListDTO]:
    empresa_id = gerente.empresa_id
    r = await session.execute(
        select(Usuario)
        .where(Usuario.empresa_id == empresa_id)
        .order_by(Usuario.nome)
    )
    usuarios = r.scalars().all()
    return [
        UsuarioListDTO(
            id=u.id,
            nome=u.nome,
            email=u.email,
            perfil=u.perfil,
            codigo_operador=u.codigo_operador,
            ativo=u.ativo,
            ultimo_acesso=u.ultimo_acesso.isoformat() if u.ultimo_acesso else None,
        )
        for u in usuarios
    ]


@router.post("/usuarios", response_model=UsuarioListDTO, status_code=201)
async def create_usuario(
    req: UsuarioCreateRequest,
    gerente: Usuario = Depends(require_perfil(_MIN_PERFIL)),
    session: AsyncSession = Depends(get_async_session),
) -> UsuarioListDTO:
    empresa_id = gerente.empresa_id

    # Gerente não pode criar usuário com perfil >= ao seu
    nivel_gerente = _nivel(PerfilUsuario(gerente.perfil))
    nivel_novo = _nivel(req.perfil)
    if nivel_novo >= nivel_gerente:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Você não pode criar usuário com perfil igual ou superior ao seu.",
        )

    # Email único na empresa
    dup = await session.execute(
        select(Usuario).where(
            Usuario.empresa_id == empresa_id,
            Usuario.email == req.email,
        )
    )
    if dup.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="E-mail já cadastrado nesta empresa.",
        )

    # Código de operador único na empresa
    if req.codigo_operador:
        dup_cod = await session.execute(
            select(Usuario).where(
                Usuario.empresa_id == empresa_id,
                Usuario.codigo_operador == req.codigo_operador,
            )
        )
        if dup_cod.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Código de operador já utilizado.",
            )

    usuario = Usuario(
        id=uuid.uuid4(),
        empresa_id=empresa_id,
        nome=req.nome,
        email=req.email,
        senha_hash=hash_password(req.senha),
        perfil=req.perfil,
        codigo_operador=req.codigo_operador,
        pin_hash=hash_pin(req.pin) if req.pin else None,
        ativo=True,
    )
    session.add(usuario)
    await session.flush()

    return UsuarioListDTO(
        id=usuario.id,
        nome=usuario.nome,
        email=usuario.email,
        perfil=str(usuario.perfil),
        codigo_operador=usuario.codigo_operador,
        ativo=usuario.ativo,
        ultimo_acesso=None,
    )


@router.patch("/usuarios/{usuario_id}/status", response_model=UsuarioListDTO)
async def patch_usuario_status(
    usuario_id: UUID,
    ativo: bool = Query(...),
    gerente: Usuario = Depends(require_perfil(_MIN_PERFIL)),
    session: AsyncSession = Depends(get_async_session),
) -> UsuarioListDTO:
    empresa_id = gerente.empresa_id

    r = await session.execute(
        select(Usuario).where(
            Usuario.id == usuario_id,
            Usuario.empresa_id == empresa_id,
        )
    )
    usuario = r.scalar_one_or_none()
    if not usuario:
        raise HTTPException(status_code=404, detail="Usuário não encontrado.")

    # Não pode desativar a si mesmo
    if usuario.id == gerente.id and not ativo:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Você não pode desativar seu próprio usuário.",
        )

    usuario.ativo = ativo
    await session.flush()

    return UsuarioListDTO(
        id=usuario.id,
        nome=usuario.nome,
        email=usuario.email,
        perfil=str(usuario.perfil),
        codigo_operador=usuario.codigo_operador,
        ativo=usuario.ativo,
        ultimo_acesso=usuario.ultimo_acesso.isoformat() if usuario.ultimo_acesso else None,
    )


# ---------------------------------------------------------------------------
# SESSÕES DE CAIXA
# ---------------------------------------------------------------------------

def _sessao_to_dto(s: SessaoCaixa) -> SessaoListDTO:
    return SessaoListDTO(
        id=s.id,
        caixa_id=s.caixa_id,
        caixa_descricao=s.caixa.descricao if s.caixa else None,
        caixa_numero=s.caixa.numero if s.caixa else 0,
        operador_id=s.operador_id,
        operador_nome=s.operador.nome if s.operador else "",
        status=str(s.status),
        data_abertura=s.data_abertura.isoformat(),
        data_fechamento=s.data_fechamento.isoformat() if s.data_fechamento else None,
        total_liquido=Decimal(str(s.total_liquido or 0)),
        quantidade_vendas=s.quantidade_vendas or 0,
        diferenca_fechamento=Decimal(str(s.diferenca_fechamento)) if s.diferenca_fechamento is not None else None,
        saldo_informado_fechamento=Decimal(str(s.saldo_informado_fechamento)) if s.saldo_informado_fechamento is not None else None,
        saldo_sistema_fechamento=Decimal(str(s.saldo_sistema_fechamento)) if s.saldo_sistema_fechamento is not None else None,
        total_dinheiro=Decimal(str(s.total_dinheiro or 0)),
        total_pix=Decimal(str(s.total_pix or 0)),
        total_cartao_debito=Decimal(str(s.total_cartao_debito or 0)),
        total_cartao_credito=Decimal(str(s.total_cartao_credito or 0)),
        total_outros=Decimal(str(s.total_outros or 0)),
        ticket_medio=Decimal(str(s.ticket_medio)) if s.ticket_medio is not None else None,
    )

@router.get("/sessoes", response_model=List[SessaoListDTO])
async def list_sessoes(
    limit: int = Query(30, ge=1, le=200),
    gerente: Usuario = Depends(require_perfil(_MIN_PERFIL)),
    session: AsyncSession = Depends(get_async_session),
) -> List[SessaoListDTO]:
    empresa_id = gerente.empresa_id

    r = await session.execute(
        select(SessaoCaixa)
        .options(
            joinedload(SessaoCaixa.caixa),
            joinedload(SessaoCaixa.operador),
        )
        .where(SessaoCaixa.empresa_id == empresa_id)
        .order_by(SessaoCaixa.data_abertura.desc())
        .limit(limit)
    )
    sessoes = r.unique().scalars().all()

    return [_sessao_to_dto(s) for s in sessoes
    ]


# ---------------------------------------------------------------------------
# CAIXAS
# ---------------------------------------------------------------------------

@router.get("/caixas", response_model=List[CaixaDTO])
async def list_caixas(
    gerente: Usuario = Depends(require_perfil(_MIN_PERFIL)),
    session: AsyncSession = Depends(get_async_session),
) -> List[CaixaDTO]:
    empresa_id = gerente.empresa_id
    r = await session.execute(
        select(Caixa)
        .where(Caixa.empresa_id == empresa_id)
        .order_by(Caixa.numero)
    )
    return [CaixaDTO.model_validate(c) for c in r.scalars().all()]


@router.post("/caixas", response_model=CaixaDTO, status_code=201)
async def create_caixa(
    req: CaixaCreateRequest,
    gerente: Usuario = Depends(require_perfil(_MIN_PERFIL)),
    session: AsyncSession = Depends(get_async_session),
) -> CaixaDTO:
    empresa_id = gerente.empresa_id

    dup = await session.execute(
        select(Caixa).where(
            Caixa.empresa_id == empresa_id,
            Caixa.numero == req.numero,
        )
    )
    if dup.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Já existe caixa com número {req.numero}.",
        )

    caixa = Caixa(
        id=uuid.uuid4(),
        empresa_id=empresa_id,
        numero=req.numero,
        descricao=req.descricao,
        numero_serie=req.numero_serie,
        ativo=True,
    )
    session.add(caixa)
    await session.flush()
    return CaixaDTO.model_validate(caixa)


@router.patch("/caixas/{caixa_id}/status", response_model=CaixaDTO)
async def patch_caixa_status(
    caixa_id: UUID,
    ativo: bool = Query(...),
    gerente: Usuario = Depends(require_perfil(_MIN_PERFIL)),
    session: AsyncSession = Depends(get_async_session),
) -> CaixaDTO:
    empresa_id = gerente.empresa_id
    r = await session.execute(
        select(Caixa).where(
            Caixa.id == caixa_id,
            Caixa.empresa_id == empresa_id,
        )
    )
    caixa = r.scalar_one_or_none()
    if not caixa:
        raise HTTPException(status_code=404, detail="Caixa não encontrado.")
    caixa.ativo = ativo
    await session.flush()
    return CaixaDTO.model_validate(caixa)


# ---------------------------------------------------------------------------
# CADASTRO RÁPIDO DE PRODUTO
# ---------------------------------------------------------------------------

class EANSugestaoExterna(BaseModel):
    nome: Optional[str] = None
    marca: Optional[str] = None
    categoria: Optional[str] = None


class EANLookupResult(BaseModel):
    status: str  # "found_local" | "found_external" | "not_found"
    produto: Optional[ProdutoGerencialDTO] = None
    saldo_atual: Optional[float] = None
    sugestao: Optional[EANSugestaoExterna] = None


class CadastroRapidoRequest(BaseModel):
    ean: Optional[str] = Field(None, max_length=14)
    descricao: str = Field(..., min_length=2, max_length=200)
    descricao_pdv: Optional[str] = Field(None, max_length=60)
    marca: Optional[str] = Field(None, max_length=100)
    preco_venda: Decimal = Field(..., gt=Decimal("0"))
    preco_custo: Optional[Decimal] = Field(None, ge=Decimal("0"))
    estoque_inicial: Decimal = Field(default=Decimal("0"), ge=Decimal("0"))
    unidade_id: Optional[UUID] = None
    perfil_tributario_id: Optional[UUID] = None


class CadastroRapidoResponse(BaseModel):
    produto: ProdutoGerencialDTO
    saldo_atual: float
    ativo: bool
    aviso: Optional[str] = None


class AjusteEstoqueRequest(BaseModel):
    quantidade: Decimal
    motivo: Optional[str] = Field(None, max_length=200)


class AjusteEstoqueResponse(BaseModel):
    produto_id: UUID
    saldo_anterior: float
    saldo_atual: float
    tipo_movimentacao: str


@router.get("/produtos/lookup-ean", response_model=EANLookupResult)
async def lookup_ean(
    ean: str = Query(..., min_length=1, max_length=14),
    gerente: Usuario = Depends(require_perfil(_MIN_PERFIL)),
    session: AsyncSession = Depends(get_async_session),
) -> EANLookupResult:
    empresa_id = gerente.empresa_id

    # 1. Busca local
    p_r = await session.execute(
        select(Produto)
        .options(joinedload(Produto.unidade))
        .where(
            Produto.empresa_id == empresa_id,
            Produto.codigo_barras_principal == ean,
        )
    )
    produto = p_r.unique().scalar_one_or_none()

    if produto:
        est_r = await session.execute(
            select(Estoque)
            .join(LocalEstoque, LocalEstoque.id == Estoque.local_estoque_id)
            .where(
                Estoque.produto_id == produto.id,
                Estoque.empresa_id == empresa_id,
                LocalEstoque.principal.is_(True),
            )
        )
        estoque = est_r.scalar_one_or_none()
        saldo = float(estoque.saldo_atual) if estoque else 0.0

        dto = ProdutoGerencialDTO(
            id=produto.id,
            sku=produto.sku,
            codigo_barras_principal=produto.codigo_barras_principal,
            descricao=produto.descricao,
            descricao_pdv=produto.descricao_pdv,
            preco_venda=Decimal(str(produto.preco_venda)),
            unidade_id=produto.unidade_id,
            unidade_codigo=produto.unidade.codigo if produto.unidade else None,
            perfil_tributario_id=produto.perfil_tributario_id,
            categoria_id=produto.categoria_id,
            controla_estoque=produto.controla_estoque,
            ativo=produto.ativo,
            destaque_pdv=produto.destaque_pdv,
        )
        return EANLookupResult(status="found_local", produto=dto, saldo_atual=saldo)

    # 2. Consulta Open Food Facts (fallback silencioso)
    sugestao: Optional[EANSugestaoExterna] = None
    try:
        async with httpx.AsyncClient(timeout=2.0) as client:
            resp = await client.get(
                f"https://world.openfoodfacts.org/api/v0/product/{ean}.json",
                follow_redirects=True,
            )
            if resp.status_code == 200:
                data = resp.json()
                if data.get("status") == 1:
                    prod_data = data.get("product", {})
                    nome = (
                        prod_data.get("product_name_pt")
                        or prod_data.get("product_name")
                        or prod_data.get("abbreviated_product_name")
                    )
                    marca_raw = prod_data.get("brands", "") or ""
                    marca = marca_raw.split(",")[0].strip() or None
                    categoria: Optional[str] = None
                    for tag in prod_data.get("categories_tags", []):
                        if tag.startswith("pt:"):
                            categoria = tag[3:].replace("-", " ").title()
                            break
                    if nome:
                        sugestao = EANSugestaoExterna(
                            nome=nome[:200],
                            marca=marca[:100] if marca else None,
                            categoria=categoria,
                        )
    except Exception:
        pass  # fallback silencioso — não bloqueia o cadastro

    if sugestao:
        return EANLookupResult(status="found_external", sugestao=sugestao)
    return EANLookupResult(status="not_found")


@router.post("/produtos/cadastro-rapido", response_model=CadastroRapidoResponse, status_code=201)
async def cadastro_rapido_produto(
    req: CadastroRapidoRequest,
    gerente: Usuario = Depends(require_perfil(_MIN_PERFIL)),
    session: AsyncSession = Depends(get_async_session),
) -> CadastroRapidoResponse:
    empresa_id = gerente.empresa_id

    # 1. Anti-duplicidade EAN
    if req.ean:
        dup_r = await session.execute(
            select(Produto).where(
                Produto.empresa_id == empresa_id,
                Produto.codigo_barras_principal == req.ean,
            )
        )
        if dup_r.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="EAN já cadastrado nesta empresa.",
            )

    # 2. Local de estoque principal obrigatório
    local_r = await session.execute(
        select(LocalEstoque).where(
            LocalEstoque.empresa_id == empresa_id,
            LocalEstoque.principal.is_(True),
            LocalEstoque.ativo.is_(True),
        )
    )
    local = local_r.scalar_one_or_none()
    if not local:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Local de estoque principal não configurado para esta empresa.",
        )

    # 3. Unidade de medida — usa req.unidade_id ou busca UN primeiro
    if req.unidade_id:
        unid_r = await session.execute(
            select(UnidadeMedida).where(
                UnidadeMedida.id == req.unidade_id,
                UnidadeMedida.empresa_id == empresa_id,
            )
        )
        unidade = unid_r.scalar_one_or_none()
        if not unidade:
            raise HTTPException(status_code=404, detail="Unidade de medida não encontrada.")
    else:
        unid_r = await session.execute(
            select(UnidadeMedida)
            .where(
                UnidadeMedida.empresa_id == empresa_id,
                UnidadeMedida.ativo.is_(True),
            )
            .order_by(
                (UnidadeMedida.codigo != "UN"),
                UnidadeMedida.codigo,
            )
            .limit(1)
        )
        unidade = unid_r.scalar_one_or_none()
        if not unidade:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Nenhuma unidade de medida configurada para esta empresa.",
            )

    # 4. Perfil tributário — usa req ou busca primeiro ativo
    perfil_id: Optional[uuid.UUID] = req.perfil_tributario_id
    aviso: Optional[str] = None

    if not perfil_id:
        perf_r = await session.execute(
            select(PerfilTributario)
            .where(
                PerfilTributario.empresa_id == empresa_id,
                PerfilTributario.ativo.is_(True),
            )
            .limit(1)
        )
        perf = perf_r.scalar_one_or_none()
        if perf:
            perfil_id = perf.id
        else:
            aviso = (
                "Produto cadastrado como inativo: nenhum perfil tributário configurado. "
                "Configure o fiscal para ativar o produto."
            )

    produto_ativo = perfil_id is not None

    # 5. Criar produto
    produto = Produto(
        id=uuid.uuid4(),
        empresa_id=empresa_id,
        codigo_barras_principal=req.ean if req.ean else None,
        descricao=req.descricao,
        descricao_pdv=req.descricao_pdv,
        marca=req.marca,
        preco_venda=req.preco_venda,
        custo_medio=req.preco_custo if req.preco_custo is not None else Decimal("0"),
        unidade_id=unidade.id,
        perfil_tributario_id=perfil_id,
        controla_estoque=True,
        ativo=produto_ativo,
        destaque_pdv=False,
        estoque_minimo=Decimal("0"),
    )
    session.add(produto)
    await session.flush()

    # 6. Criar Estoque no local principal
    estoque_inicial_val = float(req.estoque_inicial)
    estoque = Estoque(
        produto_id=produto.id,
        local_estoque_id=local.id,
        empresa_id=empresa_id,
        saldo_atual=estoque_inicial_val,
        saldo_reservado=0,
        permite_negativo=False,
        versao=1,
        principal=True,
    )
    session.add(estoque)
    await session.flush()

    # 7. Movimentação inicial se estoque > 0
    if estoque_inicial_val > 0:
        mov = MovimentacaoEstoque(
            empresa_id=empresa_id,
            produto_id=produto.id,
            local_estoque_id=local.id,
            usuario_id=gerente.id,
            tipo=TipoMovimentacaoEstoque.AJUSTE_POSITIVO,
            quantidade=estoque_inicial_val,
            saldo_anterior=0.0,
            saldo_posterior=estoque_inicial_val,
            custo_unitario=float(req.preco_custo) if req.preco_custo else None,
            referencia_tipo="cadastro_rapido",
            referencia_id=produto.id,
            motivo="Estoque inicial — Cadastro rápido",
        )
        session.add(mov)
        await session.flush()

    await session.refresh(produto, ["unidade"])

    dto = ProdutoGerencialDTO(
        id=produto.id,
        sku=produto.sku,
        codigo_barras_principal=produto.codigo_barras_principal,
        descricao=produto.descricao,
        descricao_pdv=produto.descricao_pdv,
        preco_venda=Decimal(str(produto.preco_venda)),
        unidade_id=produto.unidade_id,
        unidade_codigo=produto.unidade.codigo if produto.unidade else None,
        perfil_tributario_id=produto.perfil_tributario_id,
        categoria_id=produto.categoria_id,
        controla_estoque=produto.controla_estoque,
        ativo=produto.ativo,
        destaque_pdv=produto.destaque_pdv,
    )
    return CadastroRapidoResponse(
        produto=dto,
        saldo_atual=estoque_inicial_val,
        ativo=produto_ativo,
        aviso=aviso,
    )


@router.post("/produtos/{produto_id}/ajuste-estoque", response_model=AjusteEstoqueResponse)
async def ajuste_estoque(
    produto_id: UUID,
    req: AjusteEstoqueRequest,
    gerente: Usuario = Depends(require_perfil(_MIN_PERFIL)),
    session: AsyncSession = Depends(get_async_session),
) -> AjusteEstoqueResponse:
    empresa_id = gerente.empresa_id

    p_r = await session.execute(
        select(Produto).where(
            Produto.id == produto_id,
            Produto.empresa_id == empresa_id,
        )
    )
    if not p_r.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Produto não encontrado.")

    est_r = await session.execute(
        select(Estoque)
        .join(LocalEstoque, LocalEstoque.id == Estoque.local_estoque_id)
        .where(
            Estoque.produto_id == produto_id,
            Estoque.empresa_id == empresa_id,
            LocalEstoque.principal.is_(True),
        )
        .with_for_update()
    )
    estoque = est_r.scalar_one_or_none()
    if not estoque:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Produto sem estoque no local principal.",
        )

    quantidade = float(req.quantidade)
    saldo_anterior = float(estoque.saldo_atual)
    novo_saldo = saldo_anterior + quantidade

    if novo_saldo < 0 and not estoque.permite_negativo:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                f"Ajuste resultaria em saldo negativo ({novo_saldo:.3f}). "
                f"Saldo atual: {saldo_anterior:.3f}."
            ),
        )

    tipo = (
        TipoMovimentacaoEstoque.AJUSTE_POSITIVO
        if quantidade >= 0
        else TipoMovimentacaoEstoque.AJUSTE_NEGATIVO
    )

    estoque.saldo_atual = novo_saldo
    estoque.versao += 1

    mov = MovimentacaoEstoque(
        empresa_id=empresa_id,
        produto_id=produto_id,
        local_estoque_id=estoque.local_estoque_id,
        usuario_id=gerente.id,
        tipo=tipo,
        quantidade=abs(quantidade),
        saldo_anterior=saldo_anterior,
        saldo_posterior=novo_saldo,
        custo_unitario=None,
        referencia_tipo="ajuste_manual",
        referencia_id=None,
        motivo=req.motivo,
    )
    session.add(mov)
    await session.flush()

    return AjusteEstoqueResponse(
        produto_id=produto_id,
        saldo_anterior=saldo_anterior,
        saldo_atual=novo_saldo,
        tipo_movimentacao=tipo.value,
    )


# ---------------------------------------------------------------------------
# MÓDULO DE ESTOQUE — listagem, entrada e inventário
# ---------------------------------------------------------------------------


class EstoqueProdutoDTO(BaseModel):
    produto_id: UUID
    descricao: str
    codigo_barras: Optional[str] = None
    unidade: Optional[str] = None
    preco_venda: Decimal
    saldo_atual: float
    ativo: bool


class PaginatedEstoque(BaseModel):
    items: List[EstoqueProdutoDTO]
    total: int
    page: int
    per_page: int


class EntradaEstoqueRequest(BaseModel):
    quantidade: Decimal = Field(..., gt=Decimal("0"))
    observacao: Optional[str] = Field(None, max_length=300)


class EntradaEstoqueResponse(BaseModel):
    produto_id: UUID
    saldo_anterior: float
    saldo_atual: float


class InventarioRequest(BaseModel):
    """Ajuste de inventário: o usuário informa o saldo CONTADO atual."""
    saldo_contado: Decimal = Field(..., ge=Decimal("0"))
    observacao: Optional[str] = Field(None, max_length=300)


class InventarioResponse(BaseModel):
    produto_id: UUID
    saldo_anterior: float
    saldo_atual: float
    diferenca: float
    tipo_movimentacao: str


class MovimentacaoDTO(BaseModel):
    id: UUID
    produto_id: UUID
    produto_descricao: str
    tipo: str
    quantidade: float
    saldo_anterior: float
    saldo_posterior: float
    motivo: Optional[str] = None
    criado_em: str


class PaginatedMovimentacoes(BaseModel):
    items: List[MovimentacaoDTO]
    total: int
    page: int
    per_page: int


@router.get("/estoque", response_model=PaginatedEstoque)
async def list_estoque(
    q: Optional[str] = Query(None, max_length=100),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    gerente: Usuario = Depends(require_perfil(_MIN_PERFIL)),
    session: AsyncSession = Depends(get_async_session),
) -> PaginatedEstoque:
    """Lista produtos com saldo do local principal."""
    empresa_id = gerente.empresa_id
    offset = (page - 1) * per_page

    base_q = (
        select(
            Produto.id,
            Produto.descricao,
            Produto.codigo_barras_principal,
            Produto.preco_venda,
            Produto.ativo,
            UnidadeMedida.codigo.label("unidade_codigo"),
            func.coalesce(Estoque.saldo_atual, 0).label("saldo_atual"),
        )
        .outerjoin(
            Estoque,
            (Estoque.produto_id == Produto.id)
            & (Estoque.empresa_id == Produto.empresa_id)
            & (Estoque.principal.is_(True)),
        )
        .outerjoin(UnidadeMedida, UnidadeMedida.id == Produto.unidade_id)
        .where(Produto.empresa_id == empresa_id)
    )

    if q:
        pattern = f"%{q}%"
        base_q = base_q.where(
            Produto.descricao.ilike(pattern)
            | Produto.codigo_barras_principal.ilike(pattern)
        )

    count_r = await session.execute(
        select(func.count()).select_from(base_q.subquery())
    )
    total = int(count_r.scalar() or 0)

    rows_r = await session.execute(
        base_q.order_by(Produto.descricao).offset(offset).limit(per_page)
    )
    rows = rows_r.all()

    return PaginatedEstoque(
        items=[
            EstoqueProdutoDTO(
                produto_id=r.id,
                descricao=r.descricao,
                codigo_barras=r.codigo_barras_principal,
                unidade=r.unidade_codigo,
                preco_venda=Decimal(str(r.preco_venda)),
                saldo_atual=float(r.saldo_atual),
                ativo=r.ativo,
            )
            for r in rows
        ],
        total=total,
        page=page,
        per_page=per_page,
    )


@router.post(
    "/produtos/{produto_id}/entrada-estoque",
    response_model=EntradaEstoqueResponse,
)
async def entrada_estoque(
    produto_id: UUID,
    req: EntradaEstoqueRequest,
    gerente: Usuario = Depends(require_perfil(_MIN_PERFIL)),
    session: AsyncSession = Depends(get_async_session),
) -> EntradaEstoqueResponse:
    """Entrada de estoque (compra / recebimento). Quantidade deve ser > 0."""
    empresa_id = gerente.empresa_id

    p_r = await session.execute(
        select(Produto).where(
            Produto.id == produto_id, Produto.empresa_id == empresa_id
        )
    )
    if not p_r.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Produto não encontrado.")

    est_r = await session.execute(
        select(Estoque)
        .join(LocalEstoque, LocalEstoque.id == Estoque.local_estoque_id)
        .where(
            Estoque.produto_id == produto_id,
            Estoque.empresa_id == empresa_id,
            LocalEstoque.principal.is_(True),
        )
        .with_for_update()
    )
    estoque = est_r.scalar_one_or_none()
    if not estoque:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Produto sem estoque no local principal.",
        )

    quantidade = float(req.quantidade)
    saldo_anterior = float(estoque.saldo_atual)
    novo_saldo = saldo_anterior + quantidade

    estoque.saldo_atual = novo_saldo
    estoque.versao += 1
    estoque.ultima_entrada = datetime.now(timezone.utc)

    mov = MovimentacaoEstoque(
        empresa_id=empresa_id,
        produto_id=produto_id,
        local_estoque_id=estoque.local_estoque_id,
        usuario_id=gerente.id,
        tipo=TipoMovimentacaoEstoque.ENTRADA_COMPRA,
        quantidade=quantidade,
        saldo_anterior=saldo_anterior,
        saldo_posterior=novo_saldo,
        custo_unitario=None,
        referencia_tipo="entrada_manual",
        referencia_id=None,
        motivo=req.observacao,
    )
    session.add(mov)
    await session.flush()

    return EntradaEstoqueResponse(
        produto_id=produto_id,
        saldo_anterior=saldo_anterior,
        saldo_atual=novo_saldo,
    )


@router.post(
    "/produtos/{produto_id}/inventario",
    response_model=InventarioResponse,
)
async def inventario_estoque(
    produto_id: UUID,
    req: InventarioRequest,
    gerente: Usuario = Depends(require_perfil(_MIN_PERFIL)),
    session: AsyncSession = Depends(get_async_session),
) -> InventarioResponse:
    """
    Ajuste de inventário: o gerente informa o saldo real contado.
    O sistema calcula a diferença e registra movimentação como INVENTARIO.
    """
    empresa_id = gerente.empresa_id

    p_r = await session.execute(
        select(Produto).where(
            Produto.id == produto_id, Produto.empresa_id == empresa_id
        )
    )
    if not p_r.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Produto não encontrado.")

    est_r = await session.execute(
        select(Estoque)
        .join(LocalEstoque, LocalEstoque.id == Estoque.local_estoque_id)
        .where(
            Estoque.produto_id == produto_id,
            Estoque.empresa_id == empresa_id,
            LocalEstoque.principal.is_(True),
        )
        .with_for_update()
    )
    estoque = est_r.scalar_one_or_none()
    if not estoque:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Produto sem estoque no local principal.",
        )

    saldo_contado = float(req.saldo_contado)
    saldo_anterior = float(estoque.saldo_atual)
    diferenca = saldo_contado - saldo_anterior

    if diferenca == 0:
        return InventarioResponse(
            produto_id=produto_id,
            saldo_anterior=saldo_anterior,
            saldo_atual=saldo_anterior,
            diferenca=0.0,
            tipo_movimentacao=TipoMovimentacaoEstoque.INVENTARIO.value,
        )

    tipo = (
        TipoMovimentacaoEstoque.INVENTARIO
    )

    estoque.saldo_atual = saldo_contado
    estoque.versao += 1

    mov = MovimentacaoEstoque(
        empresa_id=empresa_id,
        produto_id=produto_id,
        local_estoque_id=estoque.local_estoque_id,
        usuario_id=gerente.id,
        tipo=tipo,
        quantidade=abs(diferenca),
        saldo_anterior=saldo_anterior,
        saldo_posterior=saldo_contado,
        custo_unitario=None,
        referencia_tipo="inventario_manual",
        referencia_id=None,
        motivo=req.observacao,
    )
    session.add(mov)
    await session.flush()

    return InventarioResponse(
        produto_id=produto_id,
        saldo_anterior=saldo_anterior,
        saldo_atual=saldo_contado,
        diferenca=diferenca,
        tipo_movimentacao=tipo.value,
    )


@router.get("/movimentacoes", response_model=PaginatedMovimentacoes)
async def list_movimentacoes(
    produto_id: Optional[UUID] = Query(None),
    page: int = Query(1, ge=1),
    per_page: int = Query(30, ge=1, le=100),
    gerente: Usuario = Depends(require_perfil(_MIN_PERFIL)),
    session: AsyncSession = Depends(get_async_session),
) -> PaginatedMovimentacoes:
    """Histórico das últimas movimentações de estoque."""
    empresa_id = gerente.empresa_id
    offset = (page - 1) * per_page

    base_q = (
        select(
            MovimentacaoEstoque.id,
            MovimentacaoEstoque.produto_id,
            Produto.descricao.label("produto_descricao"),
            MovimentacaoEstoque.tipo,
            MovimentacaoEstoque.quantidade,
            MovimentacaoEstoque.saldo_anterior,
            MovimentacaoEstoque.saldo_posterior,
            MovimentacaoEstoque.motivo,
            MovimentacaoEstoque.criado_em,
        )
        .join(Produto, Produto.id == MovimentacaoEstoque.produto_id)
        .where(MovimentacaoEstoque.empresa_id == empresa_id)
    )

    if produto_id:
        base_q = base_q.where(MovimentacaoEstoque.produto_id == produto_id)

    count_r = await session.execute(
        select(func.count()).select_from(base_q.subquery())
    )
    total = int(count_r.scalar() or 0)

    rows_r = await session.execute(
        base_q.order_by(MovimentacaoEstoque.criado_em.desc())
        .offset(offset)
        .limit(per_page)
    )
    rows = rows_r.all()

    return PaginatedMovimentacoes(
        items=[
            MovimentacaoDTO(
                id=r.id,
                produto_id=r.produto_id,
                produto_descricao=r.produto_descricao,
                tipo=str(r.tipo),
                quantidade=float(r.quantidade),
                saldo_anterior=float(r.saldo_anterior),
                saldo_posterior=float(r.saldo_posterior),
                motivo=r.motivo,
                criado_em=r.criado_em.isoformat() if r.criado_em else "",
            )
            for r in rows
        ],
        total=total,
        page=page,
        per_page=per_page,
    )


# ---------------------------------------------------------------------------
# RELATÓRIO DIÁRIO
# ---------------------------------------------------------------------------

@router.get("/relatorio-diario", response_model=RelatorioDiarioDTO)
async def relatorio_diario(
    data: Optional[str] = Query(None, description="Data YYYY-MM-DD, padrão hoje"),
    gerente: Usuario = Depends(require_perfil(_MIN_PERFIL)),
    session: AsyncSession = Depends(get_async_session),
) -> RelatorioDiarioDTO:
    empresa_id = gerente.empresa_id

    if data:
        try:
            ref_date = date.fromisoformat(data)
        except ValueError:
            raise HTTPException(status_code=400, detail="Data inválida. Use YYYY-MM-DD.")
    else:
        ref_date = date.today()

    # Totais das vendas do dia
    venda_r = await session.execute(
        select(
            func.count(Venda.id).label("qtd"),
            func.coalesce(func.sum(Venda.total_liquido), 0).label("total"),
        ).where(
            Venda.empresa_id == empresa_id,
            Venda.status == StatusVenda.CONCLUIDA,
            cast(Venda.data_venda, Date) == ref_date,
        )
    )
    v = venda_r.one()
    qtd = int(v.qtd)
    total = Decimal(str(v.total))
    ticket = (total / qtd) if qtd else Decimal("0")

    # Por forma de pagamento
    pag_r = await session.execute(
        select(
            PagamentoVenda.forma_pagamento.label("forma"),
            func.count(PagamentoVenda.id).label("qtd"),
            func.coalesce(func.sum(PagamentoVenda.valor), 0).label("total"),
        )
        .join(Venda, PagamentoVenda.venda_id == Venda.id)
        .where(
            Venda.empresa_id == empresa_id,
            Venda.status == StatusVenda.CONCLUIDA,
            cast(Venda.data_venda, Date) == ref_date,
        )
        .group_by(PagamentoVenda.forma_pagamento)
    )
    por_forma = [
        PagamentoPorFormaDTO(
            forma=str(row.forma),
            label=_FORMA_LABEL.get(str(row.forma), str(row.forma)),
            total=Decimal(str(row.total)),
            qtd=int(row.qtd),
        )
        for row in pag_r.all()
    ]

    # Sessões abertas neste dia
    sess_r = await session.execute(
        select(SessaoCaixa)
        .options(
            joinedload(SessaoCaixa.caixa),
            joinedload(SessaoCaixa.operador),
        )
        .where(
            SessaoCaixa.empresa_id == empresa_id,
            cast(SessaoCaixa.data_abertura, Date) == ref_date,
        )
        .order_by(SessaoCaixa.data_abertura.desc())
    )
    sessoes = sess_r.unique().scalars().all()

    sessoes_abertas = sum(1 for s in sessoes if str(s.status) == StatusSessaoCaixa.ABERTA)
    sessoes_fechadas = sum(1 for s in sessoes if str(s.status) == StatusSessaoCaixa.FECHADA)
    diferenca_total = sum(
        Decimal(str(s.diferenca_fechamento or 0))
        for s in sessoes
        if s.diferenca_fechamento is not None
    )

    return RelatorioDiarioDTO(
        data_referencia=ref_date.isoformat(),
        total_vendas=total,
        qtd_vendas=qtd,
        ticket_medio=ticket.quantize(Decimal("0.01")),
        por_forma_pagamento=por_forma,
        sessoes_abertas=sessoes_abertas,
        sessoes_fechadas=sessoes_fechadas,
        diferenca_total=diferenca_total,
        sessoes=[_sessao_to_dto(s) for s in sessoes],
    )

