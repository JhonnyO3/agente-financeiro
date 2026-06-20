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
_PALAVRAS_GRUPO = {"todas", "todos", "grupo", "parcelas", "grupo todo", "todas as parcelas"}


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
        "acao_pendente": "excluir",
        "fase_pendente": fase,
        "payload_pendente": payload,
        "campos_faltantes": [],
        "opcoes": opcoes,
        "expira_em": (datetime.now(timezone.utc) + _TTL_PENDENCIA).isoformat(),
    }


def _usuario_quer_grupo(mensagem: str) -> bool:
    texto = mensagem.lower()
    return any(p in texto for p in _PALAVRAS_GRUPO)


class Excluir:
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
            case "aguardando_escopo":
                return await self._escopo(state)
            case "aguardando_confirmacao":
                return await self._confirmar(state)
            case _:
                return await self._novo(state)

    async def _novo(self, state: AgentState) -> dict:
        from agent.domain.intencao import ParamsExcluir
        from agent.services.rag import BuscaRAG
        from agent.tools.excluir import ToolExcluir

        updates: dict = _limpar_pendencia()

        intencao = state.get("intencao") or {}
        params_raw = intencao.get("parametros") or {}
        params = ParamsExcluir.model_validate(params_raw) if isinstance(params_raw, dict) else params_raw
        if not isinstance(params, ParamsExcluir):
            params = ParamsExcluir()

        usuario_id = state["usuario_id"]
        repo = self._repo_factory(usuario_id)
        rag = BuscaRAG(embedder=self._embedder, adapter=repo)
        tool = ToolExcluir(rag=rag, repository=repo, relogio=self._relogio)

        resultado = await tool.executar(params, usuario_id)
        updates["resultado"] = resultado.model_dump(mode="json")

        if resultado.status == "aguardando_selecao":
            opcoes = resultado.dados.get("opcoes", [])
            updates.update(_salvar_pendencia("aguardando_selecao", resultado.dados, opcoes=opcoes))
        elif resultado.status == "aguardando_escopo":
            updates.update(_salvar_pendencia("aguardando_escopo", resultado.dados))
        elif resultado.status == "aguardando_confirmacao":
            updates.update(_salvar_pendencia("aguardando_confirmacao", resultado.dados))

        return updates

    async def _selecionar(self, state: AgentState) -> dict:
        from agent.domain.intencao import ParamsExcluir, ParamsSelecionar
        from agent.services.rag import BuscaRAG
        from agent.tools.excluir import ToolExcluir

        intencao = state.get("intencao") or {}
        params_raw = intencao.get("parametros") or {}
        params_sel = ParamsSelecionar.model_validate(params_raw) if isinstance(params_raw, dict) else params_raw

        if not isinstance(params_sel, ParamsSelecionar):
            return {"resultado": {"acao": "excluir", "status": "nao_encontrado", "dados": {}}, **_limpar_pendencia()}

        opcoes = state.get("opcoes") or []
        opcao = next((o for o in opcoes if o.get("numero") == params_sel.opcao), None)
        if opcao is None:
            return {"resultado": {"acao": "excluir", "status": "nao_encontrado", "dados": {}}, **_limpar_pendencia()}

        # Re-executa ToolExcluir com referência resolvida
        usuario_id = state["usuario_id"]
        repo = self._repo_factory(usuario_id)
        rag = BuscaRAG(embedder=self._embedder, adapter=repo)
        tool = ToolExcluir(rag=rag, repository=repo, relogio=self._relogio)

        params_excluir = ParamsExcluir(referencia=opcao.get("descricao", ""))
        resultado = await tool.executar(params_excluir, usuario_id)
        # Injeta o registro resolvido no resultado se MATCH
        if resultado.status in ("aguardando_escopo", "aguardando_confirmacao") and "registro" not in resultado.dados:
            resultado.dados["registro"] = opcao

        updates: dict = {"resultado": resultado.model_dump(mode="json"), **_limpar_pendencia()}
        if resultado.status == "aguardando_escopo":
            updates.update(_salvar_pendencia("aguardando_escopo", resultado.dados))
        elif resultado.status == "aguardando_confirmacao":
            updates.update(_salvar_pendencia("aguardando_confirmacao", resultado.dados))
        return updates

    async def _escopo(self, state: AgentState) -> dict:
        mensagem = state["messages"][-1].content if state.get("messages") else ""
        payload = dict(state.get("payload_pendente") or {})

        if _usuario_quer_grupo(str(mensagem)):
            payload["modo"] = "grupo"
        else:
            payload["modo"] = "individual"

        resultado_dict = {"acao": "excluir", "status": "aguardando_confirmacao", "dados": payload}
        return {
            "resultado": resultado_dict,
            **_salvar_pendencia("aguardando_confirmacao", payload),
        }

    async def _confirmar(self, state: AgentState) -> dict:
        from agent.services.parser_periodo import parsear_periodo

        payload = state.get("payload_pendente") or {}
        usuario_id = state["usuario_id"]
        repo = self._repo_factory(usuario_id)
        modo = payload.get("modo", "individual")

        if modo == "lote":
            periodo = payload.get("periodo")
            categoria = payload.get("categoria")
            inicio, fim, _ = parsear_periodo(periodo, self._relogio)
            await repo.excluir_por_filtros(inicio, fim, categoria, usuario_id=usuario_id)
        elif modo == "grupo":
            registro = payload.get("registro", {})
            grupo_id = registro.get("grupo_parcela_id")
            if grupo_id:
                await repo.excluir_grupo(grupo_id, usuario_id=usuario_id)
            else:
                await repo.excluir(registro.get("id"), usuario_id=usuario_id)
        else:
            # individual
            registro = payload.get("registro", {})
            await repo.excluir(registro.get("id"), usuario_id=usuario_id)

        return {
            "resultado": {"acao": "excluir", "status": "concluido", "dados": payload},
            **_limpar_pendencia(),
        }
