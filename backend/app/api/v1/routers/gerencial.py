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
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import List, Optional
from uuid import UUID

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
)
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
    total_vendas: Decimal
    qtd_vendas: int
    ticket_medio: Decimal
    por_forma_pagamento: List[PagamentoPorFormaDTO]
    sessoes_abertas: int


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

    return DashboardDTO(
        data_referencia=today.isoformat(),
        total_vendas=total,
        qtd_vendas=qtd,
        ticket_medio=ticket.quantize(Decimal("0.01")),
        por_forma_pagamento=por_forma,
        sessoes_abertas=sessoes_abertas,
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

    return [
        SessaoListDTO(
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
        )
        for s in sessoes
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
