from sqlalchemy import Column, ForeignKey
from sqlalchemy.dialects.postgresql import UUID

from pressao_api.core.database import Base


class AlvoMembro(Base):
    """Associa um alvo agregado aos alvos individuais (membros)."""

    __tablename__ = "alvo_membros"

    agregado_id = Column(
        UUID(as_uuid=True),
        ForeignKey("alvos.id", ondelete="CASCADE"),
        primary_key=True,
    )
    membro_id = Column(
        UUID(as_uuid=True),
        ForeignKey("alvos.id", ondelete="CASCADE"),
        primary_key=True,
    )

    def __repr__(self):
        return f"<AlvoMembro agregado={self.agregado_id} membro={self.membro_id}>"
