from typing import Any

import jwt
import structlog
from fastapi import HTTPException, Security
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt import PyJWKClient

from pressao_api.core.config import settings

logger = structlog.get_logger()


class KeycloakAuth:
    """Autenticação via Keycloak."""

    def __init__(self):
        self.jwks_client = PyJWKClient(
            f"{settings.KEYCLOAK_URL}/realms/{settings.KEYCLOAK_REALM}/protocol/openid-connect/certs"
        )
        self.audience = settings.KEYCLOAK_CLIENT_ID
        self.issuer = f"{settings.KEYCLOAK_URL}/realms/{settings.KEYCLOAK_REALM}"

    def get_username(self, payload: dict[str, Any]) -> str:
        """Extrai username do payload."""
        return payload.get("preferred_username", "")

    async def validate_token(self, token: str) -> dict[str, Any]:
        """Valida token JWT do Keycloak."""
        try:
            # Obtém a chave pública
            signing_key = self.jwks_client.get_signing_key_from_jwt(token)

            # Valida o token
            # Tenta o audience principal (para usuários)
            try:
                payload = jwt.decode(
                    token,
                    signing_key.key,
                    algorithms=["RS256"],
                    audience=self.audience,  # "pressao-api"
                    issuer=self.issuer,
                    options={"verify_exp": True},
                )
            except jwt.InvalidAudienceError:
                # 2. Fallback para Service Account
                payload = jwt.decode(
                    token,
                    signing_key.key,
                    algorithms=["RS256"],
                    audience="account",  # Padrão do Keycloak para M2M
                    issuer=self.issuer,
                    options={"verify_exp": True},
                )

            logger.info("Token validated", user_id=payload.get("sub"))
            return payload

        except jwt.ExpiredSignatureError:
            raise HTTPException(status_code=401, detail="Token expired")
        except jwt.InvalidTokenError as e:
            logger.error("Invalid token", error=str(e))
            raise HTTPException(status_code=401, detail="Invalid token")
        except Exception as e:  # noqa
            logger.error("Token validation error", error=str(e))
            raise HTTPException(status_code=401, detail="Authentication failed")

    def extract_user_id(self, payload: dict[str, Any]) -> str:
        """Extrai ID do usuário do payload."""
        return payload.get("sub", "")

    def is_admin(self, payload: dict[str, Any]) -> bool:
        """Verifica se usuário é admin."""
        roles = payload.get("realm_access", {}).get("roles", [])
        return "admin" in roles


security = HTTPBearer()
auth = KeycloakAuth()


async def get_current_user(credentials: HTTPAuthorizationCredentials = Security(security)) -> dict:
    """
    Dependência para obter usuário atual (OBRIGATÓRIA).
    Levanta exceção se não autenticado.
    """
    token = credentials.credentials

    try:
        payload = await auth.validate_token(token)
        user_id = auth.extract_user_id(payload)

        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid user")

        is_service = "service-account" in auth.get_username(payload)

        return {
            "id": auth.extract_user_id(payload),
            "is_admin": auth.is_admin(payload) or is_service,
            "username": auth.get_username(payload),
            # Busca campos do Keycloak
            "nome": payload.get("nome") or payload.get("name") or payload.get("given_name"),
            "email": payload.get("email"),
            "telefone": payload.get("telefone") or payload.get("phone_number"),
            "is_service": is_service,
            "payload": payload,
        }
    except Exception:  # noqa
        raise HTTPException(status_code=401, detail="Authentication failed")


async def get_current_user_optional(
    credentials: HTTPAuthorizationCredentials | None = Security(security),
):
    """Dependência para obter usuário opcional."""
    if not credentials:
        return None

    try:
        payload = await auth.validate_token(credentials.credentials)
        user_id = auth.extract_user_id(payload)

        if not user_id:
            return None

        return {
            "id": auth.extract_user_id(payload),
            "is_admin": auth.is_admin(payload),
            "username": auth.get_username(payload),
            # Busca campos do Keycloak
            "nome": payload.get("nome") or payload.get("name") or payload.get("given_name"),
            "email": payload.get("email"),
            "telefone": payload.get("telefone") or payload.get("phone_number"),
            "is_service": "service-account" in auth.get_username(payload),
            "payload": payload,
        }
    except:  # noqa
        return None
