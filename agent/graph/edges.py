from __future__ import annotations

from agent.graph.state import AgentState

# Ações que representam resposta do usuário a uma pendência (não nova operação)
_ACOES_RESPOSTA = frozenset({"confirmar", "cancelar", "selecionar", "complementar"})

# Mapeamento acao → nome do nó no grafo
_MAPA_OPERACOES: dict[str, str] = {
    "cadastrar": "no_cadastrar",
    "listar": "no_listar",
    "atualizar": "no_atualizar",
    "excluir": "no_excluir",
    "conversar": "no_conversar",
}


def rotear(state: AgentState) -> str:
    intencao = state.get("intencao") or {}
    acao = intencao.get("acao", "desconhecida")
    acao_pendente = state.get("acao_pendente")

    if acao_pendente and acao in _ACOES_RESPOSTA:
        if acao == "cancelar":
            return "no_cancelar"
        return _MAPA_OPERACOES.get(acao_pendente, "no_conversar")

    return _MAPA_OPERACOES.get(acao, "no_conversar")
