from dataclasses import asdict, fields

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.usuario import Usuario
from backend.repositories.dtos import UsuarioCreate, UsuarioUpdate

_CAMPOS_USUARIO = {f.name for f in fields(UsuarioCreate)}


class UsuarioRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def criar(self, usuario: UsuarioCreate | None = None, **kwargs) -> Usuario:
        dados = asdict(usuario) if usuario is not None else kwargs
        obj = Usuario(**{k: v for k, v in dados.items() if k in _CAMPOS_USUARIO})
        self._session.add(obj)
        await self._session.flush()
        await self._session.refresh(obj)
        return obj

    async def buscar_por_id(self, id: int) -> Usuario | None:
        result = await self._session.execute(select(Usuario).where(Usuario.id == id))
        return result.scalar_one_or_none()

    async def buscar_por_email(self, email: str) -> Usuario | None:
        result = await self._session.execute(select(Usuario).where(Usuario.email == email))
        return result.scalar_one_or_none()

    async def listar(self) -> list[Usuario]:
        result = await self._session.execute(select(Usuario).order_by(Usuario.id))
        return list(result.scalars().all())

    async def atualizar(self, id: int, dados: UsuarioUpdate | None = None, **kwargs) -> Usuario:
        obj = await self.buscar_por_id(id)
        campos = asdict(dados) if dados is not None else kwargs
        for campo, valor in campos.items():
            if valor is not None:
                setattr(obj, campo, valor)
        await self._session.flush()
        await self._session.refresh(obj)
        return obj

    async def excluir(self, id: int) -> None:
        await self._session.execute(delete(Usuario).where(Usuario.id == id))
        await self._session.flush()
