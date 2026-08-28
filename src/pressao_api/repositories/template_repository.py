from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from pressao_api.models.template import Template


class TemplateRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def criar(self, dados: dict) -> Template:
        template = Template(**dados)
        self.session.add(template)
        await self.session.flush()
        return template

    async def buscar_por_id(self, template_id: UUID) -> Template | None:
        query = select(Template).where(Template.id == template_id)
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def listar_por_campanha(
        self,
        campanha_id: UUID,
        canal: str | None = None,
        ativo: bool | None = None,
    ) -> list[Template]:
        query = select(Template).where(Template.campanha_id == campanha_id)
        if canal is not None:
            query = query.where(Template.canal == canal)
        if ativo is not None:
            query = query.where(Template.ativo == ativo)
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def listar_ativos_por_canal(self, campanha_id: UUID, canal: str) -> list[Template]:
        return await self.listar_por_campanha(campanha_id, canal=canal, ativo=True)

    async def atualizar(self, template_id: UUID, dados: dict) -> Template | None:
        template = await self.buscar_por_id(template_id)
        if not template:
            return None

        for key, value in dados.items():
            if value is not None:
                setattr(template, key, value)

        await self.session.flush()
        return template

    async def deletar(self, template_id: UUID) -> bool:
        template = await self.buscar_por_id(template_id)
        if not template:
            return False

        await self.session.delete(template)
        await self.session.flush()
        return True
