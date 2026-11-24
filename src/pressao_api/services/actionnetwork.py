"""Integração com o Action Network (API v2, OSDI): cria/atualiza o contato e aplica tags.

Usa o "Person Signup Helper" (POST /people/): se o e-mail ou o telefone já existir, o Action Network
atualiza o registro em vez de duplicar, e a operação é idempotente. O status de inscrição do e-mail
NÃO é enviado de propósito: pessoa nova entra inscrita e quem já existe mantém o status atual, então
nunca reinscrevemos quem pediu para sair.
"""

import asyncio
from dataclasses import dataclass

import httpx
import structlog

from pressao_api.core.config import settings
from pressao_api.utils.validadores import (
    normalizar_telefone_e164,
    validar_email,
    validar_telefone,
)

logger = structlog.get_logger()

TENTATIVAS = 3
ESPERA_BASE_SEG = 1.0


@dataclass(frozen=True)
class ResultadoActionNetwork:
    sucesso: bool
    status_code: int | None = None
    erro: str | None = None


def integracao_ativa() -> bool:
    return bool((settings.ACTIONNETWORK_API_KEY or "").strip())


def separar_nome(nome: str | None) -> tuple[str | None, str | None]:
    partes = (nome or "").split()
    if not partes:
        return None, None
    return partes[0], (" ".join(partes[1:]) or None)


def montar_payload(nome: str | None, email: str, telefone: str | None, tags: list[str]) -> dict:
    given_name, family_name = separar_nome(nome)
    person: dict = {"email_addresses": [{"address": email.strip().lower()}]}
    if given_name:
        person["given_name"] = given_name
    if family_name:
        person["family_name"] = family_name
    if telefone and validar_telefone(telefone):
        person["phone_numbers"] = [{"number": normalizar_telefone_e164(telefone).lstrip("+")}]
    return {"person": person, "add_tags": tags}


async def registrar_contato(
    *,
    nome: str | None,
    email: str,
    telefone: str | None,
    tags: list[str],
    client: httpx.AsyncClient | None = None,
) -> ResultadoActionNetwork:
    """Cria/atualiza o contato com as tags. Nunca levanta exceção: devolve o resultado."""
    if not integracao_ativa():
        return ResultadoActionNetwork(sucesso=False, erro="ACTIONNETWORK_API_KEY não configurada")
    if not validar_email(email or ""):
        return ResultadoActionNetwork(sucesso=False, erro="e-mail inválido")
    if not tags:
        return ResultadoActionNetwork(sucesso=False, erro="nenhuma tag configurada")

    url = f"{settings.ACTIONNETWORK_API_URL.rstrip('/')}/people/"
    headers = {
        "OSDI-API-Token": settings.ACTIONNETWORK_API_KEY,
        "Content-Type": "application/json",
    }
    payload = montar_payload(nome, email, telefone, tags)

    proprio = client is None
    http = client or httpx.AsyncClient(timeout=settings.ACTIONNETWORK_TIMEOUT_SEG)
    ultimo_erro = "erro desconhecido"
    status_code: int | None = None
    try:
        for tentativa in range(1, TENTATIVAS + 1):
            try:
                resp = await http.post(url, json=payload, headers=headers)
                status_code = resp.status_code
                if resp.status_code == 200:
                    logger.info("Contato registrado no Action Network", tags=tags)
                    return ResultadoActionNetwork(sucesso=True, status_code=200)
                ultimo_erro = f"HTTP {resp.status_code}"
                # 4xx (exceto 429) não melhora com nova tentativa
                if resp.status_code < 500 and resp.status_code != 429:
                    break
            except httpx.HTTPError as exc:
                ultimo_erro = f"{type(exc).__name__}"
            if tentativa < TENTATIVAS:
                await asyncio.sleep(ESPERA_BASE_SEG * 2 ** (tentativa - 1))
    finally:
        if proprio:
            await http.aclose()

    # Nunca registrar o token nem o e-mail do ativista nos logs
    logger.error("Falha ao registrar contato no Action Network", erro=ultimo_erro, tags=tags)
    return ResultadoActionNetwork(sucesso=False, status_code=status_code, erro=ultimo_erro)
