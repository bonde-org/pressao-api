from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from prometheus_client import REGISTRY, make_asgi_app

from pressao_api.api.v1.router import api_router
from pressao_api.core.config import settings
from pressao_api.core.database import engine
from pressao_api.core.metrics import APP_NAMESPACE, MetricsMiddleware, setup_db_metrics
from pressao_api.utils.logger import setup_logging

setup_logging()
logger = structlog.get_logger()

def register_collector(collector_class, name):
    """Registra um collector de forma segura"""
    try:
        REGISTRY.register(collector_class())
        logger.info(f"✅ {name} registrado")
    except Exception as e: # noqa
        if "Duplicated" in str(e) or "already" in str(e).lower():
            logger.info(f"⏭️ {name} já registrado")
        else:
            logger.warning(f"⚠️ {name}: {e}")

# Python GC (Garbage Collector)
try:
    from prometheus_client import GCCollector
    register_collector(GCCollector, "GCCollector")
    logger.info("Metricas do Garbage Collector habilitadas")
except ImportError:
    logger.warning("GCCollector nao disponivel")

# Plataforma (Info do sistema)
try:
    from prometheus_client import PlatformCollector
    register_collector(PlatformCollector, "PlatformCollector")
    logger.info("Metricas de plataforma habilitadas")
except ImportError:
    logger.warning("PlatformCollector nao disponivel")

# CONFIGURA MÉTRICAS DO BANCO
setup_db_metrics(engine)


# LIFESPAN
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Gerencia o ciclo de vida da aplicação."""
    logger.info("Starting application", env=settings.APP_ENV)
    
    # Inicializa a conexão com o banco
    async with engine.begin() as _:
        # Em produção, usar migrations, não criar tabelas automaticamente
        pass
    
    yield
    
    # Cleanup
    await engine.dispose()
    logger.info("Application shutdown")

# Inicializa o app
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="API para orquestração de ações de pressão multicanal",
    lifespan=lifespan,
    docs_url="/api/docs",
    redoc_url="/api/redoc",
)

# Configura CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if settings.APP_ENV == "development" else settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configura monitoramento
if settings.METRICS_ENABLED:
    # Middleware de métricas
    app.add_middleware(MetricsMiddleware)
    
    metrics_app = make_asgi_app()
    app.mount("/api/metrics", metrics_app)
    
    logger.info(f"✅ Métricas habilitadas em /api/metrics (namespace: {APP_NAMESPACE})")

# Registra as rotas
app.include_router(api_router, prefix="/api/v1")

@app.get("/")
async def root():
    return {
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "status": "healthy"
    }

@app.get("/api/health")
async def health_check():
    return {"status": "ok", "environment": settings.APP_ENV}