import asyncio
from datetime import datetime
from uuid import UUID

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from pressao_api.models.acao import Acao
from pressao_api.models.alvo import Alvo
from pressao_api.models.campanha import Campanha
from pressao_api.models.ligacao import Ligacao
from pressao_api.models.template import Template
from pressao_api.repositories.disparo_repository import DisparoRepository
from pressao_api.repositories.ligacao_repository import LigacaoRepository
from pressao_api.repositories.template_repository import TemplateRepository
from pressao_api.schemas.acao import CanalEnum, ProximoPassoTipoEnum, StatusAcaoEnum
from pressao_api.services.alvo_agregado import membro_telefone_publico
from pressao_api.services.telefone_alvo_da_vez import escolher_membro
from pressao_api.services.telefone_service import telefone_service
from pressao_api.services.templates import sortear_template
from pressao_api.utils.validadores import extrair_ddd, normalizar_telefone_e164

logger = structlog.get_logger()


def _dados_publicos_membro(membro: Alvo) -> dict:
    dados = membro_telefone_publico(membro)
    dados["id"] = str(dados["id"])
    return dados


async def iniciar_tentativa(
    session: AsyncSession,
    acao: Acao,
    agregado: Alvo,
    campanha: Campanha,
    membro_id: UUID | None = None,
    template: Template | None = None,
    selecao: str | None = None,
) -> Ligacao:
    """
    Cria disparo + ligação para um membro do agregado e pede a ligação ao provedor.

    Atualiza a ação: `PROCESSANDO` aguardando eventos, ou `FALHA` se o provedor recusar.
    """
    if not acao.ativista_telefone:
        raise ValueError("Canal telefone exige telefone do ativista")
    telefone_ativista = normalizar_telefone_e164(acao.ativista_telefone)
    acao.ativista_telefone = telefone_ativista

    dry_run = telefone_service.modo_dry_run()
    if not campanha.telefone_origem and not dry_run:
        raise ValueError("Campanha sem número de origem para telefone")

    membro, selecao = await escolher_membro(session, agregado.id, membro_id, selecao)
    telefone_alvo = normalizar_telefone_e164(membro.contato)

    if template is None:
        templates = await TemplateRepository(session).listar_ativos_por_canal(
            acao.campanha_id, CanalEnum.TELEFONE.value
        )
        template = sortear_template(templates)

    disparo_repo = DisparoRepository(session)
    ligacao_repo = LigacaoRepository(session)
    agora = datetime.utcnow()  # noqa: DTZ003

    disparo = await disparo_repo.criar(
        {"acao_id": acao.id, "alvo_id": membro.id, "status": "ENVIADO"}
    )
    ligacao = await ligacao_repo.criar(
        {
            "acao_id": acao.id,
            "disparo_id": disparo.id,
            "alvo_id": membro.id,
            "telefone_ativista": telefone_ativista,
            "telefone_alvo": telefone_alvo,
            "etapa": "INICIANDO",
            "provedor": "dry_run" if dry_run else "twilio",
            "selecao": selecao,
            "iniciada_em": agora,
            "eventos": [],
        }
    )
    tentativas = len(await ligacao_repo.listar_por_acao(acao.id))

    resultado = await asyncio.to_thread(
        telefone_service.iniciar_ligacao,
        telefone_origem=campanha.telefone_origem,
        telefone_ativista=telefone_ativista,
        telefone_alvo=telefone_alvo,
        ligacao_id=str(ligacao.id),
        acao_id=str(acao.id),
        campanha_id=str(campanha.id),
    )

    dados = {
        "ligacao_id": str(ligacao.id),
        "disparo_id": str(disparo.id),
        "alvo": _dados_publicos_membro(membro),
        "selecao": selecao,
        "roteiro": telefone_service.montar_roteiro(acao, membro, campanha, template),
        "numero_origem_prefixo": extrair_ddd(campanha.telefone_origem),
        "dry_run": resultado.dry_run,
        "tentativa": tentativas,
        "template_id": str(template.id) if template else None,
    }

    if resultado.sucesso:
        ligacao.provedor_call_id = resultado.call_id
        disparo.message_id = resultado.call_id
        acao.status = StatusAcaoEnum.PROCESSANDO
        acao.proximo_passo_tipo = ProximoPassoTipoEnum.WEBHOOK_AGUARDAR
        acao.proximo_passo_instrucao = "Aguardando a ligação para o ativista"
    else:
        ligacao.etapa = "FALHA"
        ligacao.motivo_falha = "erro_provedor"
        ligacao.finalizada_em = agora
        disparo.status = "ERRO_ENVIO"
        disparo.proximo_passo_dados = {"erro": resultado.erro}
        acao.status = StatusAcaoEnum.FALHA
        acao.proximo_passo_tipo = ProximoPassoTipoEnum.FINALIZADO
        acao.proximo_passo_instrucao = "Falha ao iniciar a ligação"
        dados["erro"] = resultado.erro

    acao.proximo_passo_dados = dados
    await disparo_repo.salvar(disparo)
    await ligacao_repo.salvar(ligacao)

    logger.info(
        "Tentativa de ligação iniciada",
        acao_id=str(acao.id),
        ligacao_id=str(ligacao.id),
        alvo_id=str(membro.id),
        selecao=selecao,
        sucesso=resultado.sucesso,
        dry_run=resultado.dry_run,
    )
    return ligacao
