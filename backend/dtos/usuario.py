from pydantic import BaseModel

from backend.models.enums import RoleEnum


class UsuarioCreateRequest(BaseModel):
    nome: str
    username: str
    email: str
    senha: str
    telefone: str | None = None
    role: RoleEnum = RoleEnum.USER


class UsuarioUpdateRequest(BaseModel):
    model_config = {"extra": "ignore"}

    nome: str | None = None
    username: str | None = None
    email: str | None = None
    telefone: str | None = None
    role: RoleEnum | None = None
    ativo: bool | None = None
    senha: str | None = None


class UsuarioResponse(BaseModel):
    id: int
    nome: str
    username: str
    email: str
    telefone: str | None = None
    role: RoleEnum
    ativo: bool
    criado_em: str

    @classmethod
    def de_modelo(cls, usuario) -> "UsuarioResponse":
        role = usuario.role
        role_valor = role.value if hasattr(role, "value") else str(role)
        criado_em = usuario.criado_em
        criado_em_iso = criado_em.isoformat() if hasattr(criado_em, "isoformat") else str(criado_em)
        return cls(
            id=usuario.id,
            nome=usuario.nome,
            username=usuario.username,
            email=usuario.email,
            telefone=usuario.telefone,
            role=RoleEnum(role_valor),
            ativo=usuario.ativo,
            criado_em=criado_em_iso,
        )
