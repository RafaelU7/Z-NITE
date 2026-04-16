"""
Zênite PDV — ponto de entrada do backend FastAPI.

Padrão application factory:
  create_app() monta a aplicação (útil para testes de integração).
  O objeto `app` é exposto no nível do módulo para o servidor ASGI (uvicorn).

Inicialização:
  uvicorn main:app --reload

Produção:
  uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4
"""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.v1.router import router as api_v1_router
from app.core.config import get_settings
from app.core.exceptions import (
    AuthenticationError,
    AuthorizationError,
    BusinessRuleError,
    ConflictError,
    ExternalServiceError,
    NotFoundError,
    ServiceUnavailableError,
    ZeniteBaseException,
)

settings = get_settings()
log = logging.getLogger(__name__)

logging.basicConfig(
    level=settings.log_level.upper(),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)


# ---------------------------------------------------------------------------
# Lifespan (startup / shutdown)
# ---------------------------------------------------------------------------


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    log.info("Zênite PDV iniciando — env=%s", settings.app_env)

    # Pool ARQ para enfileirar jobs fiscais
    from arq import create_pool
    from arq.connections import RedisSettings

    arq_pool = await create_pool(
        RedisSettings.from_dsn(settings.redis_url),
        default_queue_name="arq:zenite_fiscal",
    )
    app.state.arq_pool = arq_pool
    log.info("ARQ pool conectado")

    yield

    await arq_pool.close(True)
    log.info("ARQ pool encerrado")

    from app.infrastructure.security.redis_blacklist import close_redis
    await close_redis()
    log.info("Zênite PDV encerrando...")


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.app_name,
        version="0.1.0",
        description="Backend do Sistema Zênite PDV — Automação Comercial para Varejo",
        docs_url="/docs" if not settings.is_production else None,
        redoc_url="/redoc" if not settings.is_production else None,
        openapi_url="/openapi.json" if not settings.is_production else None,
        lifespan=lifespan,
    )

    # -------------------------------------------------------------------------
    # CORS
    # -------------------------------------------------------------------------
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # -------------------------------------------------------------------------
    # Exception handlers — mapeiam exceções de domínio para HTTP
    # -------------------------------------------------------------------------

    @app.exception_handler(AuthenticationError)
    async def _auth_handler(request: Request, exc: AuthenticationError) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content={"detail": exc.message, "code": exc.code},
            headers={"WWW-Authenticate": "Bearer"},
        )

    @app.exception_handler(AuthorizationError)
    async def _authz_handler(request: Request, exc: AuthorizationError) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_403_FORBIDDEN,
            content={"detail": exc.message, "code": exc.code},
        )

    @app.exception_handler(NotFoundError)
    async def _not_found_handler(request: Request, exc: NotFoundError) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={"detail": exc.message, "code": exc.code},
        )

    @app.exception_handler(ConflictError)
    async def _conflict_handler(request: Request, exc: ConflictError) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_409_CONFLICT,
            content={"detail": exc.message, "code": exc.code},
        )

    @app.exception_handler(BusinessRuleError)
    async def _business_handler(request: Request, exc: BusinessRuleError) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            content={"detail": exc.message, "code": exc.code},
        )

    @app.exception_handler(ExternalServiceError)
    async def _external_handler(request: Request, exc: ExternalServiceError) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_502_BAD_GATEWAY,
            content={"detail": exc.message, "code": exc.code},
        )

    @app.exception_handler(ServiceUnavailableError)
    async def _unavailable_handler(
        request: Request, exc: ServiceUnavailableError
    ) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={"detail": exc.message, "code": exc.code},
        )

    @app.exception_handler(ZeniteBaseException)
    async def _zenite_fallback(request: Request, exc: ZeniteBaseException) -> JSONResponse:
        log.error("Exceção de domínio não tratada: %s", exc, exc_info=True)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"detail": "Erro interno do servidor", "code": exc.code},
        )

    # -------------------------------------------------------------------------
    # Routers
    # -------------------------------------------------------------------------
    app.include_router(api_v1_router, prefix="/v1")

    # -------------------------------------------------------------------------
    # Health check
    # -------------------------------------------------------------------------
    @app.get("/health", tags=["Sistema"], summary="Health check")
    async def health() -> dict[str, str]:
        return {"status": "ok", "app": settings.app_name, "env": settings.app_env}

    return app


app = create_app()
