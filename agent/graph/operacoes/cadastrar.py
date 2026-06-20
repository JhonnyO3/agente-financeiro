from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING

from agent.graph.state import AgentState

if TYPE_CHECKING:
    from collections.abc import Callable
    from agent.services.relogio import Relogio
    from agent.services.extrator import Extrator
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


def _salvar_pendencia(
    fase: str,
    payload: dict,
    campos_faltantes: list[str] | None = None,
    opcoes: list[dict] | None = None,
) -> dict:
    return {
        "acao_pendente": "cadastrar",
        "fase_pendente": fase,
        "payload_pendente": payload,
        "campos_faltantes": campos_faltantes or [],
        "opcoes": opcoes,
        "expira_em": (datetime.now(timezone.utc) + _TTL_PENDENCIA).isoformat(),
    }


class Cadastrar:
    def __init__(
        self,
        *,
        relogio: Relogio,
        repo_factory: Callable[[int], TransacaoRepository],
        extrator: Extrator,
    ) -> None:
        self._relogio = relogio
        self._repo_factory = repo_factory
        self._extrator = extrator

    async def executar(self, state: AgentState) -> dict:
        fase = state.get("fase_pendente")
        match fase:
            case "aguardando_confirmacao":
                return await self._confirmar(state)
            case "aguardando_complemento":
                return await self._complementar(state)
            case _:
                return await self._novo(state)

    async def _novo(self, state: AgentState) -> dict:
        from agent.domain.intencao import ParamsCadastrar, ItemCadastro
        from agent.tools.cadastrar import ToolCadastrar

        # Limpa pendência stale de outra operação
        updates: dict = _limpar_pendencia()

        intencao = state.get("intencao") or {}
        params_raw = intencao.get("parametros") or {}
        params = (
            ParamsCadastrar.model_validate(params_raw)
            if isinstance(params_raw, dict)
            else params_raw
        )

        itens: list[ItemCadastro] = (
            params.itens if isinstance(params, ParamsCadastrar) else []
        )

        # Extrai campos faltantes via extrator se disponível
        mensagem = (
            state["messages"][-1].content if state.get("messages") else ""
        )
        historico = (
            [f"{m.type}: {m.content}" for m in state["messages"][:-1]]
            if state.get("messages")
            else []
        )
        if itens:
            itens = await self._extrator.extrair_cadastro(
                itens_parciais=itens,
                mensagem_original=mensagem,
                historico=historico,
            )

        repo = self._repo_factory(state["usuario_id"])
        tool = ToolCadastrar(relogio=self._relogio, repository=repo)
        resultado = await tool.executar(itens, {"mensagem": mensagem})

        updates["resultado"] = resultado.model_dump(mode="json")

        if resultado.status == "aguardando_complemento":
            campos = resultado.dados.get("campos_faltantes", [])
            updates.update(
                _salvar_pendencia(
                    "aguardando_complemento",
                    resultado.dados,
                    campos_faltantes=campos,
                )
            )
        elif resultado.status == "aguardando_confirmacao":
            updates.update(
                _salvar_pendencia("aguardando_confirmacao", resultado.dados)
            )

        return updates

    async def _complementar(self, state: AgentState) -> dict:
        from agent.domain.intencao import ParamsComplementar, ItemCadastro
        from agent.tools.cadastrar import ToolCadastrar

        intencao = state.get("intencao") or {}
        params_raw = intencao.get("parametros") or {}
        params = (
            ParamsComplementar.model_validate(params_raw)
            if isinstance(params_raw, dict)
            else params_raw
        )

        if not isinstance(params, ParamsComplementar):
            return {
                "resultado": {"acao": "cadastrar", "status": "concluido", "dados": {}},
                **_limpar_pendencia(),
            }

        campo = params.campo
        valor = params.valor

        payload = dict(state.get("payload_pendente") or {})
        campos_faltantes = list(state.get("campos_faltantes") or [])

        # Preenche o campo nos registros do payload
        if "registros" in payload:
            for reg in payload["registros"]:
                if isinstance(reg, dict) and reg.get(campo) is None:
                    reg[campo] = valor
        elif "campos_faltantes" in payload:
            # payload ainda em fase de coleta, guarda o valor diretamente
            payload[campo] = valor

        campos_faltantes = [c for c in campos_faltantes if c != campo]

        if campos_faltantes:
            novo_payload = {**payload, "campos_faltantes": campos_faltantes}
            return {
                "resultado": {
                    "acao": "cadastrar",
                    "status": "aguardando_complemento",
                    "dados": novo_payload,
                },
                **_salvar_pendencia(
                    "aguardando_complemento",
                    novo_payload,
                    campos_faltantes=campos_faltantes,
                ),
            }

        # Todos os campos preenchidos — re-executa a tool com o payload completo
        itens_raw = payload.get("registros", [])
        itens: list[ItemCadastro] = [
            ItemCadastro.model_validate(item) if isinstance(item, dict) else item
            for item in itens_raw
        ]
        mensagem = (
            state["messages"][-1].content if state.get("messages") else ""
        )
        repo = self._repo_factory(state["usuario_id"])
        tool = ToolCadastrar(relogio=self._relogio, repository=repo)
        resultado = await tool.executar(itens, {"mensagem": mensagem})

        updates: dict = {"resultado": resultado.model_dump(mode="json")}
        if resultado.status == "aguardando_confirmacao":
            updates.update(
                _salvar_pendencia("aguardando_confirmacao", resultado.dados)
            )
        else:
            updates.update(_limpar_pendencia())
        return updates

    async def _confirmar(self, state: AgentState) -> dict:
        payload = state.get("payload_pendente") or {}
        registros = payload.get("registros", [])
        usuario_id = state["usuario_id"]

        repo = self._repo_factory(usuario_id)
        await repo.criar_lote(registros, usuario_id=usuario_id)

        return {
            "resultado": {"acao": "cadastrar", "status": "concluido", "dados": payload},
            **_limpar_pendencia(),
        }
