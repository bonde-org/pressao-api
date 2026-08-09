import time

from fastapi import Request
from prometheus_client import Counter, Gauge, Histogram, Info
from starlette.middleware.base import BaseHTTPMiddleware

# Configuraçõe de Métricas
APP_NAMESPACE = "pressao_api"

# Info sobre a Aplicação
app_info = Info("app_info", "Informações da aplicação", namespace=APP_NAMESPACE)
app_info.info({"version": "0.1.0", "environment": "production"})


# Contador de requisições
http_requests_total = Counter(
    "http_requests_total",
    "Total de requisições HTTP",
    ["method", "endpoint", "status"],  # Labels para filtrar
    namespace=APP_NAMESPACE,
)

# Histograma de duração das requisições
http_request_duration_seconds = Histogram(
    "http_request_duration_seconds",
    "Duração das requisições HTTP em segundos",
    ["method", "endpoint", "status"],
    buckets=[0.01, 0.05, 0.1, 0.5, 1.0, 2.5, 5.0, 10.0],
    namespace=APP_NAMESPACE,
)

# Gauge de requisições ativas (para monitorar carga)
http_requests_in_progress = Gauge(
    "http_requests_in_progress",
    "Requisições HTTP em andamento",
    ["method", "endpoint"],
    namespace=APP_NAMESPACE,
)


# MIDDLEWARE PARA COLETAR MÉTRICAS HTTP
class MetricsMiddleware(BaseHTTPMiddleware):
    """Middleware para coletar métricas HTTP automaticamente"""

    async def dispatch(self, request: Request, call_next):
        # Incrementa requisições em andamento
        endpoint = request.url.path

        # Ignora o endpoint /metrics para não causar contagem negativa
        if endpoint == "/api/metrics" or endpoint.startswith("/api/metrics/"):
            return await call_next(request)

        method = request.method
        labels = {"method": method, "endpoint": endpoint}

        http_requests_in_progress.labels(**labels).inc()

        # Mede o tempo
        start_time = time.time()

        try:
            response = await call_next(request)
            duration = time.time() - start_time
            status = response.status_code

            # Registra métricas
            http_requests_total.labels(method=method, endpoint=endpoint, status=status).inc()
            http_request_duration_seconds.labels(
                method=method, endpoint=endpoint, status=status
            ).observe(duration)

            return response
        except Exception:
            # Em caso de erro, ainda registra a métrica
            http_requests_total.labels(method=method, endpoint=endpoint, status=500).inc()
            raise
        finally:
            # ⭐ Garante o decremento (apenas 1 vez)
            http_requests_in_progress.labels(**labels).dec()


# MÉTRICAS DE CONEXÕES DO BANCO
db_connections_active = Gauge(
    "db_connections_active", "Número de conexões ativas no banco de dados", namespace=APP_NAMESPACE
)

db_connections_idle = Gauge(
    "db_connections_idle", "Número de conexões ociosas no pool", namespace=APP_NAMESPACE
)


def setup_db_metrics(engine):
    """Configura métricas do banco de dados"""
    from sqlalchemy import event

    @event.listens_for(engine.sync_engine, "checkout")
    def on_checkout(dbapi_conn, connection_record, connection_proxy):
        db_connections_active.inc()

    @event.listens_for(engine.sync_engine, "checkin")
    def on_checkin(dbapi_conn, connection_record):
        db_connections_active.dec()


# Métricas de Negócio
# Ações criadas por canal
acoes_criadas_total = Counter(
    "acoes_criadas_total",
    "Total de ações de pressão criadas",
    ["canal", "status"],  # status: success, error
    namespace=APP_NAMESPACE,
)

# Tempo de confirmação
acoes_tempo_confirmacao_seconds = Histogram(
    "acoes_tempo_confirmacao_seconds",
    "Tempo entre criação e confirmação da ação em segundos",
    ["campanha_id", "canal"],
    buckets=[1, 5, 10, 30, 60, 120, 300, 600],
    namespace=APP_NAMESPACE,
)

# Ações por campanha
acoes_por_campanha_total = Counter(
    "acoes_por_campanha_total",
    "Ações realizadas por campanha",
    ["campanha_id", "canal"],
    namespace=APP_NAMESPACE,
)

# Ações aguardando confirmação (Backlog)
acoes_aguardando_confirmacao = Gauge(
    "acoes_aguardando_confirmacao",
    "Ações aguardando confirmação manual",
    ["campanha_id", "canal"],
    namespace=APP_NAMESPACE,
)
