from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING

from agent.graph.state import AgentState

if TYPE_CHECKING:
    from collections.abc import Callable
    from agent.agents_llm import Embedder
    from agent.services.relogio import Relogio
    from backend.repositories.transacao_repository import TransacaoRepository

_TTL_PENDENCIA = timedelta(minutes=5)


def _limpar_pendencia() -> dict:
    return {
        "acao_pendente": None,
        "fase_pendente": None,
        "payload_pendente": None,
        "campos_faltantes": [],
        "opcoes": None,
        "expira_em": None,
    }


def _salvar_pendencia(fase: str, payload: dict, opcoes: list[dict] | None = None) -> dict:
    return {
        "acao_pendente": "atualizar",
        "fase_pendente": fase,
        "payload_pendente": payload,
        "campos_faltantes": [],
        "opcoes": opcoes,
        "expira_em": (datetime.now(timezone.utc) + _TTL_PENDENCIA).isoformat(),
    }


class Atualizar:
    def __init__(
        self,
        *,
        relogio: Relogio,
        repo_factory: Callable[[int], TransacaoRepository],
        embedder: Embedder,
    ) -> None:
        self._relogio = relogio
        self._repo_factory = repo_factory
        self._embedder = embedder

    async def executar(self, state: AgentState) -> dict:
        fase = state.get("fase_pendente")
        match fase:
            case "aguardando_selecao":
                return await self._selecionar(state)
            case "aguardando_confirmacao":
                return await self._confirmar(state)
            case _:
                return await self._novo(state)

    async def _novo(self, state: AgentState) -> dict:
        from agent.domain.intencao import ParamsAtualizar
        from agent.services.rag import BuscaRAG
        from agent.tools.atualizar import ToolAtualizar

        updates: dict = _limpar_pendencia()

        intencao = state.get("intencao") or {}
        params_raw = intencao.get("parametros") or {}
        params = ParamsAtualizar.model_validate(params_raw) if isinstance(params_raw, dict) else params_raw
        if not isinstance(params, ParamsAtualizar):
            params = ParamsAtualizar()

        usuario_id = state["usuario_id"]
        repo = self._repo_factory(usuario_id)
        rag = BuscaRAG(embedder=self._embedder, adapter=repo)
        tool = ToolAtualizar(rag=rag, repository=repo, relogio=self._relogio)

        resultado = await tool.executar(params, usuario_id)
        updates["resultado"] = resultado.model_dump(mode="json")

        if resultado.status == "aguardando_selecao":
            opcoes = resultado.dados.get("opcoes", [])
            updates.update(_salvar_pendencia("aguardando_selecao", resultado.dados, opcoes=opcoes))
        elif resultado.status == "aguardando_confirmacao":
            updates.update(_salvar_pendencia("aguardando_confirmacao", resultado.dados))

        return updates

    async def _selecionar(self, state: AgentState) -> dict:
        from agent.domain.intencao import ParamsAtualizar, ParamsSelecionar
        from agent.services.rag import BuscaRAG
        from agent.tools.atualizar import ToolAtualizar

        intencao = state.get("intencao") or {}
        params_raw = intencao.get("parametros") or {}
        params_sel = ParamsSelecionar.model_validate(params_raw) if isinstance(params_raw, dict) else params_raw

        if not isinstance(params_sel, ParamsSelecionar):
            return {"resultado": {"acao": "atualizar", "status": "nao_encontrado", "dados": {}}, **_limpar_pendencia()}

        opcoes = state.get("opcoes") or []
        opcao = next((o for o in opcoes if o.get("numero") == params_sel.opcao), None)
        if opcao is None:
            return {"resultado": {"acao": "atualizar", "status": "nao_encontrado", "dados": {}}, **_limpar_pendencia()}

        # Monta params de atualizar com a ref resolvida
        payload_anterior = state.get("payload_pendente") or {}
        params_atualizar = ParamsAtualizar(
            referencia=opcao.get("descricao", ""),
            campo=payload_anterior.get("diff", {}).get("campo"),
            novo_valor=payload_anterior.get("diff", {}).get("novo"),
        )

        usuario_id = state["usuario_id"]
        repo = self._repo_factory(usuario_id)
        rag = BuscaRAG(embedder=self._embedder, adapter=repo)
        tool = ToolAtualizar(rag=rag, repository=repo, relogio=self._relogio)

        resultado = await tool.executar(params_atualizar, usuario_id)
        updates: dict = {"resultado": resultado.model_dump(mode="json"), **_limpar_pendencia()}

        if resultado.status == "aguardando_confirmacao":
            updates.update(_salvar_pendencia("aguardando_confirmacao", resultado.dados))

        return updates

    async def _confirmar(self, state: AgentState) -> dict:
        payload = state.get("payload_pendente") or {}
        registro = payload.get("registro", {})
        diff = payload.get("diff", {})
        usuario_id = state["usuario_id"]

        repo = self._repo_factory(usuario_id)
        await repo.atualizar(registro, diff, usuario_id=usuario_id)

        return {
            "resultado": {"acao": "atualizar", "status": "concluido", "dados": payload},
            **_limpar_pendencia(),
        }
