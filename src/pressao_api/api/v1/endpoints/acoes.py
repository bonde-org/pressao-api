from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from pressao_api.core.database import get_db
from pressao_api.core.security import get_current_user, get_current_user_optional
from pressao_api.schemas.acao import (
    CriarAcaoRequest,
    RespostaAcaoResponse,
    AcaoDetailResponse,
    AcaoStatusResponse,
    StatusAcaoEnum,
    ProximoPassoResponse,
    ProximoPassoTipoEnum,
    MetricaQualidadeEnum,
)
from pressao_api.repositories.acao_repository import AcaoRepository
from pressao_api.services.orquestrador import orquestrador
from pressao_api.core.metrics import acoes_criadas_total, acoes_por_campanha_total, acoes_aguardando_confirmacao, acoes_tempo_confirmacao_seconds
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
    """
    canal = None
    try:
        canal = request.canal.value if hasattr(request.canal, 'value') else request.canal
        # Validações básicas (mock)

        # Mock: valida se alvo pertence à campanha
        # Em implementação real, consultar banco
        
        # ============================================
        # PREPARA DADOS DA AÇÃO
        # ============================================
        
        acao_data = {
            "campanha_id": request.campanha_id,
            "alvo_id": request.alvo_id,
            "canal": canal,
            "template_id": request.template_id,
            "status": StatusAcaoEnum.PROCESSANDO,
        }
        
        is_service = current_user.get("is_service", False)
        
        # Usuário comum (logado)
        if not is_service:
            if request.anonimo:
                acao_data.update({
                    "anonimo": True,
                    "ativista_id": None,
                    "ativista_nome": None,
                    "ativista_email": None,
                    "ativista_telefone": None,
                })
                logger.info("Ação anônima criada por usuário logado", user_id=current_user["id"])
            else:
                acao_data.update({
                    "ativista_id": current_user["id"],
                    "ativista_nome": current_user.get("nome"),
                    "ativista_email": current_user.get("email"),
                    "ativista_telefone": current_user.get("telefone"),
                    "anonimo": False,
                })
                logger.info("Ação criada por usuário logado", user_id=current_user["id"])
        
        # Service Account
        else:
            if request.anonimo:
                acao_data.update({
                    "anonimo": True,
                    "ativista_nome": None,
                    "ativista_email": None,
                    "ativista_telefone": None,
                    # ativista_id fica None
                })
                logger.info("Ação anônima via service account")
            else:
                acao_data.update({
                    "anonimo": False,
                    "ativista_nome": request.ativista.nome if request.ativista else None,
                    "ativista_email": request.ativista.email if request.ativista else None,
                    "ativista_telefone": request.ativista.telefone if request.ativista else None,
                    # ativista_id fica None (service account não é o ativista)
                })
                logger.info("Ação via service account para ativista")
        
        # Importante: se for anônimo, garantir que ativista_id seja None
        if acao_data.get("anonimo", False):
            acao_data["ativista_id"] = None
        
        # ============================================
        # CRIA AÇÃO
        # ============================================
        
        repo = AcaoRepository(db)
        acao = await repo.criar(acao_data)
        
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
        
        # ============================================
        # MÉTRICAS DE NEGÓCIO
        # ============================================
        
        # Ação criada com sucesso por canal
        acoes_criadas_total.labels(
            canal=canal,
            status='success'
        ).inc()
        
        # Ação por campanha
        acoes_por_campanha_total.labels(
            campanha_id=str(request.campanha_id),
            canal=canal
        ).inc()
        
        # Ação aguardando confirmação (se aplicável)
        acoes_aguardando_confirmacao.labels(
            campanha_id=str(request.campanha_id),
            canal=canal
        ).inc()
        
        # Prepara resposta
        return RespostaAcaoResponse(
            acao_id=acao.id,
            ativista_id=acao.ativista_id,
            ativista_nome=acao.ativista_nome,
            ativista_email=acao.ativista_email,
            ativista_telefone=acao.ativista_telefone,
            anonimo=acao.anonimo,
            campanha_id=acao.campanha_id,
            alvo_id=acao.alvo_id,
            status_atual=acao.status,
            proximo_passo=ProximoPassoResponse(
                tipo=acao.proximo_passo_tipo,
                instrucao=acao.proximo_passo_instrucao,
                dados=acao.proximo_passo_dados or {}
            )
        )
    except HTTPException:
        if canal:
            # Métrica: Erro na criação
            acoes_criadas_total.labels(
                canal=canal,
                status='error'
            ).inc()
        raise
    except Exception as e:
        if canal:
            # Métrica: Erro na criação
            acoes_criadas_total.labels(
                canal=canal,
                status='error'
            ).inc()
        logger.error("Erro inesperado ao criar ação", error=str(e))
        raise HTTPException(status_code=500, detail="Erro interno ao criar ação")

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
    
    acoes_tempo_confirmacao_seconds.labels(
        canal=acao.canal,
        campanha_id=acao.campanha_id
    ).observe(tempo_resposta)
    acoes_aguardando_confirmacao.labels(
        campanha_id=acao.campanha_id,
        canal=acao.canal
    ).dec()
    
    logger.info(
        "Ação confirmada",
        acao_id=str(acao.id),
        tempo_resposta=tempo_resposta,
        qualidade=acao.metrica_qualidade
    )