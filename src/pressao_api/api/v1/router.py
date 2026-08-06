from fastapi import APIRouter
from pressao_api.api.v1.endpoints import acoes

api_router = APIRouter()

api_router.include_router(acoes.router)