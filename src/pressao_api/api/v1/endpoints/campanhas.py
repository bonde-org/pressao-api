from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from pressao_api.core.database import get_db
from pressao_api.core.security import get_current_user
from pressao_api.repositories.campanha_repository import CampanhaRepository
from pressao_api.schemas.campanha import (
    CampanhaCreate,
    CampanhaResponse,
    CampanhaUpdate,
    ReconciliarContadorResponse,
)

router = APIRouter(prefix="/campanhas", tags=["Campanhas"])


@router.post("/", response_model=CampanhaResponse, status_code=status.HTTP_201_CREATED)
async def criar_campanha(
    request: CampanhaCreate,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Cria uma nova campanha (apenas admin)"""
    if not current_user.get("is_admin", False):
        raise HTTPException(status_code=403, detail="Apenas administradores podem criar campanhas")

    repo = CampanhaRepository(db)

    # Verifica se já existe campanha com esse nome
    existente = await repo.buscar_por_nome(request.nome)
    if existente:
        raise HTTPException(status_code=400, detail="Já existe uma campanha com este nome")

    campanha = await repo.criar(request.model_dump())
    return campanha


@router.get("/", response_model=list[CampanhaResponse])
async def listar_campanhas(
    ativa: bool | None = None,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Lista todas as campanhas"""
    repo = CampanhaRepository(db)
    campanhas = await repo.listar_todas(ativa)
    return campanhas


@router.get("/{campanha_id}", response_model=CampanhaResponse)
async def obter_campanha(
    campanha_id: UUID,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    repo = CampanhaRepository(db)
    campanha = await repo.buscar_por_id(campanha_id)
    if not campanha:
        raise HTTPException(status_code=404, detail="Campanha não encontrada")
    return campanha


@router.put("/{campanha_id}", response_model=CampanhaResponse)
async def atualizar_campanha(
    campanha_id: UUID,
    request: CampanhaUpdate,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if not current_user.get("is_admin", False):
        raise HTTPException(
            status_code=403, detail="Apenas administradores podem atualizar campanhas"
        )

    repo = CampanhaRepository(db)
    campanha = await repo.atualizar(campanha_id, request.model_dump(exclude_none=True))
    if not campanha:
        raise HTTPException(status_code=404, detail="Campanha não encontrada")
    return campanha


@router.delete("/{campanha_id}", status_code=status.HTTP_204_NO_CONTENT)
async def deletar_campanha(
    campanha_id: UUID,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if not current_user.get("is_admin", False):
        raise HTTPException(
            status_code=403, detail="Apenas administradores podem deletar campanhas"
        )

    repo = CampanhaRepository(db)
    deletado = await repo.deletar(campanha_id)
    if not deletado:
        raise HTTPException(status_code=404, detail="Campanha não encontrada")


@router.post(
    "/{campanha_id}/reconciliar-contador",
    response_model=ReconciliarContadorResponse,
    summary="Reconciliar contador de ações confirmadas",
)
async def reconciliar_contador(
    campanha_id: UUID,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if not current_user.get("is_admin", False):
        raise HTTPException(status_code=403, detail="Apenas administradores")

    repo = CampanhaRepository(db)
    campanha = await repo.buscar_por_id(campanha_id)
    if not campanha:
        raise HTTPException(status_code=404, detail="Campanha não encontrada")

    antes, depois = await repo.reconciliar_acoes_confirmadas(campanha_id)
    return ReconciliarContadorResponse(antes=antes, depois=depois, divergencia=depois - antes)
