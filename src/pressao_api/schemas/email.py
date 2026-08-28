from pydantic import BaseModel, Field


class ResultadoEnvioEmail(BaseModel):
    """Resultado do disparo de e-mail de pressão."""

    sucesso: bool
    message_id: str | None = None
    sandbox: bool = False
    status: str = Field(description="enviado, sandbox ou falha")
    erro: str | None = None
    destinatario: str | None = None
    remetente: str | None = None
