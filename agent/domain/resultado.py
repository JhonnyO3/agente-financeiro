from typing import Literal

from pydantic import BaseModel

AcaoTool = Literal[
    "cadastrar", "listar", "atualizar", "excluir", "conversar", "menu", "erro"
]

StatusTool = Literal[
    "aguardando_confirmacao",
    "aguardando_selecao",
    "aguardando_escopo",
    "aguardando_complemento",
    "concluido",
    "nao_encontrado",
    "vazio",
]


class ResultadoTool(BaseModel):
    acao: AcaoTool
    status: StatusTool
    dados: dict
