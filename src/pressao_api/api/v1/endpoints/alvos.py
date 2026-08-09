from fastapi import APIRouter, Depends, HTTPException, status
from uuid import UUID
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession

from pressao_api.core.database import get_db
from pressao_api.core.security import get_current_user
from pressao_api.schemas.alvo import AlvoCreate, AlvoUpdate, AlvoResponse
from pressao_api.repositories.alvo_repository import AlvoRepository
from pressao_api.repositories.campanha_repository import CampanhaRepository

router = APIRouter(prefix="/alvos", tags=["Alvos"])

@router.post("/", response_model=AlvoResponse, status_code=status.HTTP_201_CREATED)
async def criar_alvo(
    request: AlvoCreate,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Cria um novo alvo para uma campanha"""
    # Verifica se a campanha existe
    campanha_repo = CampanhaRepository(db)
    campanha = await campanha_repo.buscar_por_id(request.campanha_id)
    if not campanha:
        raise HTTPException(status_code=404, detail="Campanha não encontrada")
    
    # Verifica se já existe alvo com este contato na mesma campanha
    alvo_repo = AlvoRepository(db)
    alvos_existentes = await alvo_repo.buscar_por_contato(request.contato)
    for alvo in alvos_existentes:
        if alvo.campanha_id == request.campanha_id:
            raise HTTPException(
                status_code=400, 
                detail="Este contato já está cadastrado nesta campanha"
            )
    
    alvo = await alvo_repo.criar(request.model_dump())
    return alvo

@router.get("/campanha/{campanha_id}", response_model=List[AlvoResponse])
async def listar_alvos_por_campanha(
    campanha_id: UUID,
    ativo: Optional[bool] = None,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Lista todos os alvos de uma campanha"""
    repo = AlvoRepository(db)
    alvos = await repo.listar_por_campanha(campanha_id, ativo)
    return alvos

@router.get("/{alvo_id}", response_model=AlvoResponse)
async def obter_alvo(
    alvo_id: UUID,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    repo = AlvoRepository(db)
    alvo = await repo.buscar_por_id(alvo_id)
    if not alvo:
        raise HTTPException(status_code=404, detail="Alvo não encontrado")
    return alvo

@router.put("/{alvo_id}", response_model=AlvoResponse)
async def atualizar_alvo(
    alvo_id: UUID,
    request: AlvoUpdate,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    repo = AlvoRepository(db)
    alvo = await repo.atualizar(alvo_id, request.model_dump(exclude_none=True))
    if not alvo:
        raise HTTPException(status_code=404, detail="Alvo não encontrado")
    return alvo

@router.delete("/{alvo_id}", status_code=status.HTTP_204_NO_CONTENT)
async def deletar_alvo(
    alvo_id: UUID,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    repo = AlvoRepository(db)
    deletado = await repo.deletar(alvo_id)
    if not deletado:
        raise HTTPException(status_code=404, detail="Alvo não encontrado")