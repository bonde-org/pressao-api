from uuid import UUID

import structlog
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from pressao_api.core.database import get_db
from pressao_api.core.metrics import (
    acoes_aguardando_confirmacao,
    acoes_criadas_total,
    acoes_por_campanha_total,
    acoes_tempo_confirmacao_seconds,
)
from pressao_api.core.security import get_current_user
from pressao_api.repositories.acao_repository import AcaoRepository
from pressao_api.repositories.alvo_repository import AlvoRepository
from pressao_api.repositories.campanha_repository import CampanhaRepository
from pressao_api.repositories.template_repository import TemplateRepository
from pressao_api.schemas.acao import (
    AcaoDetailResponse,
    AcaoStatusResponse,
    CriarAcaoRequest,
    ProximoPassoResponse,
    ProximoPassoTipoEnum,
    RespostaAcaoResponse,
    StatusAcaoEnum,
)
from pressao_api.schemas.campanha import ConfirmacaoContadorResponse
from pressao_api.services.confirmacao import incrementar_contador_se_confirmada
from pressao_api.services.metricas import calculadora
from pressao_api.services.orquestrador import orquestrador
from pressao_api.utils.validadores import (
    obter_mensagem_erro_compatibilidade,
    validar_compatibilidade_canal_alvo,
)

logger = structlog.get_logger()

router = APIRouter(
    prefix="/acoes",
    tags=["Ações"],
)


@router.post(
    "/",
    response_model=RespostaAcaoResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Criar nova ação",
)
async def criar_acao(
    request: CriarAcaoRequest,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Cria uma nova ação de pressão.
    """
    canal = None
    try:
        canal = request.canal.value if hasattr(request.canal, "value") else request.canal

        # ========================
        # Validações iniciais
        # ========================

        # Valida se a campanha existe
        campanha_repo = CampanhaRepository(db)
        campanha = await campanha_repo.buscar_por_id(request.campanha_id)
        if not campanha:
            raise HTTPException(status_code=404, detail="Campanha não encontrada")

        # Valida se a campanha está ativa
        if not campanha.ativa:
            raise HTTPException(status_code=400, detail="Campanha inativa")

        # Valida se o alvo existe e pertence à campanha
        alvo_repo = AlvoRepository(db)
        alvo = await alvo_repo.buscar_por_id(request.alvo_id)
        if not alvo:
            raise HTTPException(status_code=404, detail="Alvo não encontrado")

        # Valida se o alvo pertence à campanha
        if alvo.campanha_id != request.campanha_id:
            raise HTTPException(status_code=400, detail="Alvo não pertence à campanha informada")

        # Valida se o alvo está ativo
        if not alvo.ativo:
            raise HTTPException(status_code=400, detail="Alvo inativo")

        # VALIDA COMPATIBILIDADE CANAL X TIPO DE CONTATO
        if not validar_compatibilidade_canal_alvo(canal, alvo.tipo_contato.value):
            raise HTTPException(
                status_code=400,
                detail=obter_mensagem_erro_compatibilidade(canal, alvo.tipo_contato.value),
            )

        # Valida o template informado (quando houver)
        template = None
        if request.template_id:
            template_repo = TemplateRepository(db)
            template = await template_repo.buscar_por_id(request.template_id)
            if not template:
                raise HTTPException(status_code=404, detail="Template não encontrado")

            if template.campanha_id != request.campanha_id:
                raise HTTPException(
                    status_code=400, detail="Template não pertence à campanha informada"
                )

            if template.canal != canal:
                raise HTTPException(
                    status_code=400,
                    detail=f"Template é do canal {template.canal}, incompatível com {canal}",
                )

            if not template.ativo:
                raise HTTPException(status_code=400, detail="Template inativo")

        # ============================================
        # Preparando dados da Ação
        # ============================================

        acao_data = {
            "campanha_id": request.campanha_id,
            "alvo_id": request.alvo_id,
            "canal": canal,
            "template_id": request.template_id,
            "status": StatusAcaoEnum.PROCESSANDO,
            "sessao_id": request.sessao_id,
        }

        is_service = current_user.get("is_service", False)

        # Usuário comum (logado)
        if not is_service:
            if request.anonimo:
                acao_data.update(
                    {
                        "anonimo": True,
                        "ativista_id": None,
                        "ativista_nome": None,
                        "ativista_email": None,
                        "ativista_telefone": None,
                        "ativista_preenchido": False,
                    }
                )
                logger.info("Ação anônima criada por usuário logado", user_id=current_user["id"])
            else:
                acao_data.update(
                    {
                        "ativista_id": current_user["id"],
                        "ativista_nome": current_user.get("nome"),
                        "ativista_email": current_user.get("email"),
                        "ativista_telefone": current_user.get("telefone"),
                        "anonimo": False,
                        "ativista_preenchido": True,
                    }
                )
                logger.info("Ação criada por usuário logado", user_id=current_user["id"])

        # Service Account
        else:
            if request.anonimo:
                acao_data.update(
                    {
                        "anonimo": True,
                        "ativista_nome": None,
                        "ativista_email": None,
                        "ativista_telefone": None,
                        "ativista_preenchido": False,
                    }
                )
                logger.info("Ação anônima via service account")
            elif request.ativista:
                acao_data.update(
                    {
                        "anonimo": False,
                        "ativista_nome": request.ativista.nome,
                        "ativista_email": request.ativista.email,
                        "ativista_telefone": request.ativista.telefone,
                        "ativista_preenchido": True,
                    }
                )
                logger.info("Ação via service account com dados do ativista")
            else:
                acao_data.update(
                    {
                        "anonimo": False,
                        "ativista_nome": None,
                        "ativista_email": None,
                        "ativista_telefone": None,
                        "ativista_preenchido": False,
                    }
                )
                logger.info("Ação via service account sem dados de ativista (sessão não identificada)")

        # Importante: se for anônimo, garantir que ativista_id seja None
        if acao_data.get("anonimo", False):
            acao_data["ativista_id"] = None

        # ============================================
        # CRIA AÇÃO
        # ============================================

        repo = AcaoRepository(db)
        acao = await repo.criar(acao_data)

        try:
            acao = await orquestrador.executar(
                acao, alvo=alvo, campanha=campanha, template=template
            )
            await repo.salvar(acao)
        except ValueError as e:
            logger.error("Falha ao executar ação", error=str(e))
            await repo.salvar(acao)
            raise HTTPException(status_code=400, detail=str(e)) from e
        except Exception as e:  # noqa
            logger.error("Falha ao executar ação", error=str(e))
            await repo.salvar(acao)
            raise HTTPException(status_code=500, detail=f"Erro ao executar ação: {e!s}")

        # Atualização retroativa de dados do ativista por sessão
        if is_service and request.sessao_id and request.ativista and not request.anonimo:
            atualizadas = await repo.atualizar_ativista_por_sessao(
                sessao_id=request.sessao_id,
                ativista_nome=request.ativista.nome,
                ativista_email=request.ativista.email,
                ativista_telefone=request.ativista.telefone,
            )
            if atualizadas > 0:
                logger.info(
                    "Ações anteriores atualizadas com dados do ativista",
                    sessao_id=request.sessao_id,
                    acoes_atualizadas=atualizadas,
                )

        # ============================================
        # MÉTRICAS DE NEGÓCIO
        # ============================================

        # Ação criada com sucesso por canal
        acoes_criadas_total.labels(canal=canal, status="success").inc()

        # Ação por campanha
        acoes_por_campanha_total.labels(campanha_id=str(request.campanha_id), canal=canal).inc()

        # Ação aguardando confirmação (se aplicável)
        acoes_aguardando_confirmacao.labels(campanha_id=str(request.campanha_id), canal=canal).inc()

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
                dados=acao.proximo_passo_dados or {},
            ),
        )
    except HTTPException:
        if canal:
            # Métrica: Erro na criação
            acoes_criadas_total.labels(canal=canal, status="error").inc()
        raise
    except Exception as e:  # noqa
        if canal:
            # Métrica: Erro na criação
            acoes_criadas_total.labels(canal=canal, status="error").inc()
        logger.error("Erro inesperado ao criar ação", error=str(e))
        raise HTTPException(status_code=500, detail="Erro interno ao criar ação")


@router.get("/{acao_id}", response_model=AcaoDetailResponse, summary="Obter detalhes da ação")
async def obter_acao(
    acao_id: UUID,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Obtém detalhes completos de uma ação específica."""
    repo = AcaoRepository(db)
    acao = await repo.buscar_por_id(acao_id)

    if not acao:
        raise HTTPException(status_code=404, detail="Ação não encontrada")

    # Valida permissão (é dele ou é admin)
    if acao.ativista_id != current_user["id"] and not current_user["is_admin"]:
        raise HTTPException(status_code=403, detail="Sem permissão para visualizar esta ação")

    return acao


@router.get("/{acao_id}/status", response_model=AcaoStatusResponse, summary="Obter status da ação")
async def obter_status_acao(
    acao_id: UUID,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Obtém apenas o status atual e métricas leves da ação."""
    repo = AcaoRepository(db)
    acao = await repo.buscar_por_id(acao_id)

    if not acao:
        raise HTTPException(status_code=404, detail="Ação não encontrada")

    # Valida permissão (é dele ou é admin)
    if acao.ativista_id != current_user["id"] and not current_user["is_admin"]:
        raise HTTPException(status_code=403, detail="Sem permissão para visualizar esta ação")

    return AcaoStatusResponse(
        id=acao.id,
        status=acao.status,
        metrica_qualidade=acao.metrica_qualidade,
        confirmado_em=acao.confirmado_em,
    )


@router.patch(
    "/{acao_id}/confirmar",
    response_model=ConfirmacaoContadorResponse,
    status_code=status.HTTP_200_OK,
    summary="Confirmar ação manual",
)
async def confirmar_acao(
    acao_id: UUID,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Confirma uma ação que está aguardando ação humana.

    - Valida se ação está com status AGUARDANDO_ACAO_HUMANA
    - Calcula tempo de resposta
    - Calcula métrica de qualidade
    - Atualiza status para CONCLUIDA
    - Incrementa contador de ações confirmadas da campanha
    """
    repo = AcaoRepository(db)
    acao = await repo.buscar_por_id(acao_id)

    if not acao:
        raise HTTPException(status_code=404, detail="Ação não encontrada")

    # Valida permissão (é dele ou é admin)
    if acao.ativista_id != current_user["id"] and not current_user["is_admin"]:
        raise HTTPException(status_code=403, detail="Sem permissão para confirmar esta ação")

    # Valida se está aguardando ação humana
    if acao.status != StatusAcaoEnum.AGUARDANDO_ACAO_HUMANA:
        raise HTTPException(
            status_code=400, detail=f"Ação está com status {acao.status}, não pode ser confirmada"
        )

    # Confirma a ação
    from datetime import datetime

    # Usar utcnow() para compatibilidade com o banco
    agora = datetime.utcnow()  # noqa: DTZ003

    status_anterior = acao.status
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

    campanha_repo = CampanhaRepository(db)
    novo_total = await incrementar_contador_se_confirmada(acao, status_anterior, campanha_repo)

    acoes_tempo_confirmacao_seconds.labels(
        canal=acao.canal, campanha_id=str(acao.campanha_id)
    ).observe(tempo_resposta)
    acoes_aguardando_confirmacao.labels(campanha_id=str(acao.campanha_id), canal=acao.canal).dec()

    logger.info(
        "Ação confirmada",
        acao_id=str(acao.id),
        tempo_resposta=tempo_resposta,
        qualidade=acao.metrica_qualidade,
        acoes_confirmadas=novo_total,
    )

    return ConfirmacaoContadorResponse(acoes_confirmadas=novo_total or 0)
