from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from pressao_api.core.database import get_db
from pressao_api.core.security import get_current_user
from pressao_api.repositories.campanha_repository import CampanhaRepository
from pressao_api.repositories.template_repository import TemplateRepository
from pressao_api.schemas.acao import CanalEnum
from pressao_api.schemas.template import TemplateCreate, TemplateResponse, TemplateUpdate

router = APIRouter(prefix="/templates", tags=["Templates"])


@router.post("/", response_model=TemplateResponse, status_code=status.HTTP_201_CREATED)
async def criar_template(
    request: TemplateCreate,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Cria um novo template de mensagem para uma campanha (apenas admin)"""
    if not current_user.get("is_admin", False):
        raise HTTPException(status_code=403, detail="Apenas administradores podem criar templates")

    campanha_repo = CampanhaRepository(db)
    campanha = await campanha_repo.buscar_por_id(request.campanha_id)
    if not campanha:
        raise HTTPException(status_code=404, detail="Campanha não encontrada")

    repo = TemplateRepository(db)
    dados = request.model_dump()
    dados["canal"] = request.canal.value
    template = await repo.criar(dados)
    return template


@router.get("/campanha/{campanha_id}", response_model=list[TemplateResponse])
async def listar_templates_por_campanha(
    campanha_id: UUID,
    canal: CanalEnum | None = None,
    ativo: bool | None = None,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Lista os templates de uma campanha, com filtros opcionais de canal e ativo"""
    repo = TemplateRepository(db)
    templates = await repo.listar_por_campanha(
        campanha_id, canal=canal.value if canal else None, ativo=ativo
    )
    return templates


@router.get("/{template_id}", response_model=TemplateResponse)
async def obter_template(
    template_id: UUID,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    repo = TemplateRepository(db)
    template = await repo.buscar_por_id(template_id)
    if not template:
        raise HTTPException(status_code=404, detail="Template não encontrado")
    return template


@router.put("/{template_id}", response_model=TemplateResponse)
async def atualizar_template(
    template_id: UUID,
    request: TemplateUpdate,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if not current_user.get("is_admin", False):
        raise HTTPException(
            status_code=403, detail="Apenas administradores podem atualizar templates"
        )

    dados = request.model_dump(exclude_none=True)
    if request.canal is not None:
        dados["canal"] = request.canal.value

    repo = TemplateRepository(db)
    template = await repo.atualizar(template_id, dados)
    if not template:
        raise HTTPException(status_code=404, detail="Template não encontrado")
    return template


@router.delete("/{template_id}", status_code=status.HTTP_204_NO_CONTENT)
async def deletar_template(
    template_id: UUID,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if not current_user.get("is_admin", False):
        raise HTTPException(
            status_code=403, detail="Apenas administradores podem deletar templates"
        )

    repo = TemplateRepository(db)
    deletado = await repo.deletar(template_id)
    if not deletado:
        raise HTTPException(status_code=404, detail="Template não encontrado")
