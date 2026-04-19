"""API v1 — agrega todos os routers."""
from __future__ import annotations

from fastapi import APIRouter

from app.api.v1.routers.auth import router as auth_router
from app.api.v1.routers.caixa import router as caixa_router
from app.api.v1.routers.fiscal import router as fiscal_router
from app.api.v1.routers.gerencial import router as gerencial_router
from app.api.v1.routers.produto import router as produto_router
from app.api.v1.routers.sync import router as sync_router
from app.api.v1.routers.venda import router as venda_router

router = APIRouter()
router.include_router(auth_router)
router.include_router(produto_router)
router.include_router(caixa_router)
router.include_router(venda_router)
router.include_router(fiscal_router)
router.include_router(sync_router)
router.include_router(gerencial_router)
