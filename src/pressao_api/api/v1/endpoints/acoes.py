from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from pressao_api.core.database import get_db
from pressao_api.core.security import get_current_user
from pressao_api.schemas.acao import (
    CriarAcaoRequest,
    RespostaAcaoResponse,
    AcaoDetailResponse,
    AcaoStatusResponse,
    ConfirmarAcaoRequest,
    StatusAcaoEnum,
    ProximoPassoResponse,
    ProximoPassoTipoEnum,
    MetricaQualidadeEnum,
)
from pressao_api.repositories.acao_repository import AcaoRepository
from pressao_api.services.orquestrador import orquestrador
from pressao_api.services.metricas import calculadora
from pressao_api.models.acao import Acao
import structlog

logger = structlog.get_logger()

router = APIRouter(
    prefix="/acoes",
    tags=["Ações"],
)

@router.post(
    "/",
    response_model=RespostaAcaoResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Criar nova ação"
)
async def criar_acao(
    request: CriarAcaoRequest,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Cria uma nova ação de pressão.
    
    - Valida autenticação
    - Valida se alvo pertence à campanha (mock)
    - Valida se canal é suportado
    - Executa estratégia do canal
    - Retorna próximo passo
    """
    # Validações básicas (mock)
    if not current_user:
        raise HTTPException(status_code=401, detail="Usuário não autenticado")
    
    # Mock: valida se alvo pertence à campanha
    # Em implementação real, consultar banco
    
    # Cria ação
    
    canal_value = request.canal.value if hasattr(request.canal, 'value') else request.canal
    acao_data = {
        "ativista_id": current_user["id"],
        "campanha_id": request.campanha_id,
        "alvo_id": request.alvo_id,
        "canal": canal_value,
        "template_id": request.template_id,
        "status": StatusAcaoEnum.PROCESSANDO,
    }
    
    repo = AcaoRepository(db)
    acao = await repo.criar(acao_data)
    
    # Executa orquestrador
    try:
        acao = await orquestrador.executar(acao)
        await repo.salvar(acao)
    except Exception as e:
        logger.error("Falha ao executar ação", error=str(e))
        await repo.salvar(acao)
        raise HTTPException(
            status_code=500,
            detail=f"Erro ao executar ação: {str(e)}"
        )
    
    # Prepara resposta
    return RespostaAcaoResponse(
        acao_id=acao.id,
        ativista_id=acao.ativista_id,
        campanha_id=acao.campanha_id,
        alvo_id=acao.alvo_id,
        status_atual=acao.status,
        proximo_passo=ProximoPassoResponse(
            tipo=acao.proximo_passo_tipo,
            instrucao=acao.proximo_passo_instrucao,
            dados=acao.proximo_passo_dados or {}
        )
    )

@router.get(
    "/{acao_id}",
    response_model=AcaoDetailResponse,
    summary="Obter detalhes da ação"
)
async def obter_acao(
    acao_id: UUID,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Obtém detalhes completos de uma ação específica."""
    repo = AcaoRepository(db)
    acao = await repo.buscar_por_id(acao_id)
    
    if not acao:
        raise HTTPException(status_code=404, detail="Ação não encontrada")
    
    # Valida permissão (é dele ou é admin)
    if acao.ativista_id != current_user["id"] and not current_user["is_admin"]:
        raise HTTPException(
            status_code=403,
            detail="Sem permissão para visualizar esta ação"
        )
    
    return acao

@router.get(
    "/{acao_id}/status",
    response_model=AcaoStatusResponse,
    summary="Obter status da ação"
)
async def obter_status_acao(
    acao_id: UUID,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Obtém apenas o status atual e métricas leves da ação."""
    repo = AcaoRepository(db)
    acao = await repo.buscar_por_id(acao_id)
    
    if not acao:
        raise HTTPException(status_code=404, detail="Ação não encontrada")
    
    # Valida permissão (é dele ou é admin)
    if acao.ativista_id != current_user["id"] and not current_user["is_admin"]:
        raise HTTPException(
            status_code=403,
            detail="Sem permissão para visualizar esta ação"
        )
    
    return AcaoStatusResponse(
        id=acao.id,
        status=acao.status,
        metrica_qualidade=acao.metrica_qualidade,
        confirmado_em=acao.confirmado_em
    )

@router.patch(
    "/{acao_id}/confirmar",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Confirmar ação manual"
)
async def confirmar_acao(
    acao_id: UUID,
    request: ConfirmarAcaoRequest,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Confirma uma ação que está aguardando ação humana.
    
    - Valida se ação está com status AGUARDANDO_ACAO_HUMANA
    - Calcula tempo de resposta
    - Calcula métrica de qualidade
    - Atualiza status para CONCLUIDA
    """
    repo = AcaoRepository(db)
    acao = await repo.buscar_por_id(acao_id)
    
    if not acao:
        raise HTTPException(status_code=404, detail="Ação não encontrada")
    
    # Valida permissão (é dele ou é admin)
    if acao.ativista_id != current_user["id"] and not current_user["is_admin"]:
        raise HTTPException(
            status_code=403,
            detail="Sem permissão para confirmar esta ação"
        )
    
    # Valida se está aguardando ação humana
    if acao.status != StatusAcaoEnum.AGUARDANDO_ACAO_HUMANA:
        raise HTTPException(
            status_code=400,
            detail=f"Ação está com status {acao.status}, não pode ser confirmada"
        )
    
    # Confirma a ação
    from datetime import datetime
    agora = datetime.utcnow()
    
    acao.confirmado_em = agora
    acao.status = StatusAcaoEnum.CONCLUIDA
    
    # Calcula tempo de resposta
    tempo_resposta = calculadora.calcular_tempo_resposta(acao.criado_em, agora)
    acao.tempo_resposta_seg = tempo_resposta
    
    # Calcula métrica de qualidade
    acao.metrica_qualidade = calculadora.calcular_qualidade(tempo_resposta)
    
    # Atualiza próximo passo
    acao.proximo_passo_tipo = ProximoPassoTipoEnum.FINALIZADO
    acao.proximo_passo_instrucao = "Ação concluída com sucesso"
    acao.proximo_passo_dados = {}
    
    await repo.salvar(acao)
    
    logger.info(
        "Ação confirmada",
        acao_id=str(acao.id),
        tempo_resposta=tempo_resposta,
        qualidade=acao.metrica_qualidade
    )