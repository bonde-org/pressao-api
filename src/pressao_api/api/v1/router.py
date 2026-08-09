from fastapi import APIRouter
from pressao_api.api.v1.endpoints import acoes, alvos, campanhas

api_router = APIRouter()

api_router.include_router(acoes.router)
api_router.include_router(alvos.router)
api_router.include_router(campanhas.router)