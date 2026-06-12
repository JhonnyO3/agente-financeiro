"""Roteador — mapeia Intencao → Tool, guarda pendência e persiste confirmar sem LLM."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from agent.domain.estado import EstadoConversa
from agent.domain.intencao import (
    Intencao,
    ParamsCadastrar,
    ParamsComplementar,
    ParamsExcluir,
    ParamsListar,
    ParamsAtualizar,
    ParamsSelecionar,
)
from agent.domain.resultado import ResultadoTool
from agent.services.estado_store import EstadoStore

_STATUS_PENDENTES = {
    "aguardando_confirmacao",
    "aguardando_selecao",
    "aguardando_escopo",
    "aguardando_complemento",
}

_TTL_PENDENCIA = timedelta(minutes=5)

_MENU = ResultadoTool(acao="menu", status="concluido", dados={})


class Roteador:
    def __init__(
        self,
        tool_cadastrar: Any,
        tool_listar: Any,
        tool_atualizar: Any,
        tool_excluir: Any,
        tool_conversar: Any,
        estado_store: EstadoStore,
        repository: Any,
        llm: Any = None,
    ) -> None:
        self.tool_cadastrar = tool_cadastrar
        self.tool_listar = tool_listar
        self.tool_atualizar = tool_atualizar
        self.tool_excluir = tool_excluir
        self.tool_conversar = tool_conversar
        self._store = estado_store
        self._repo = repository
        self._llm = llm

    async def rotear(
        self,
        intencao: Intencao,
        usuario_id: int,
        agora: datetime,
        contexto: dict[str, Any],
    ) -> ResultadoTool:
        estado = await self._store.obter(usuario_id, agora)
        tem_pendencia = estado.acao_pendente is not None

        acao = intencao.acao

        # Intenções de resposta a pendência
        if acao == "confirmar":
            return await self._handle_confirmar(estado, usuario_id, agora)

        if acao == "cancelar":
            return await self._handle_cancelar(estado, usuario_id)

        if acao == "selecionar":
            return await self._handle_selecionar(
                intencao, estado, usuario_id, agora, contexto
            )

        if acao == "complementar":
            return await self._handle_complementar(
                intencao, estado, usuario_id, agora, contexto
            )

        # Intenções operacionais
        if acao in ("cadastrar", "listar", "atualizar", "excluir", "conversar"):
            # Pendência ativa → cancela antes de processar a nova intenção
            if tem_pendencia:
                await self._store.limpar_pendencia(usuario_id)

            return await self._executar_operacional(
                intencao, estado, usuario_id, agora, contexto
            )

        # Desconhecida ou qualquer outra
        return _MENU

    # ------------------------------------------------------------------
    # Handlers de resposta a pendência
    # ------------------------------------------------------------------

    async def _handle_confirmar(
        self, estado: EstadoConversa, usuario_id: int, agora: datetime
    ) -> ResultadoTool:
        if estado.acao_pendente is None:
            return _MENU

        acao_pendente = estado.acao_pendente
        payload = estado.payload_pendente or {}

        if acao_pendente == "cadastrar":
            registros = payload.get("registros", [])
            await self._repo.criar_lote(registros, usuario_id=usuario_id)

        elif acao_pendente == "atualizar":
            registro = payload.get("registro", {})
            diff = payload.get("diff", {})
            await self._repo.atualizar(registro, diff, usuario_id=usuario_id)

        elif acao_pendente == "excluir":
            registro = payload.get("registro")
            modo = payload.get("modo")

            if modo == "lote":
                periodo = payload.get("periodo")
                categoria = payload.get("categoria")
                await self._repo.excluir_por_filtros(
                    periodo=periodo, categoria=categoria, usuario_id=usuario_id
                )
            elif registro is not None:
                grupo_parcela_id = registro.get("grupo_parcela_id")
                if grupo_parcela_id:
                    await self._repo.excluir_grupo(
                        grupo_parcela_id, usuario_id=usuario_id
                    )
                else:
                    registro_id = registro.get("id")
                    await self._repo.excluir(registro_id, usuario_id=usuario_id)
            else:
                await self._repo.excluir(None, usuario_id=usuario_id)

        await self._store.limpar_pendencia(usuario_id)
        return ResultadoTool(acao=acao_pendente, status="concluido", dados={})  # type: ignore[arg-type]

    async def _handle_cancelar(
        self, estado: EstadoConversa, usuario_id: int
    ) -> ResultadoTool:
        if estado.acao_pendente is not None:
            await self._store.limpar_pendencia(usuario_id)
        return _MENU

    async def _handle_selecionar(
        self,
        intencao: Intencao,
        estado: EstadoConversa,
        usuario_id: int,
        agora: datetime,
        contexto: dict[str, Any],
    ) -> ResultadoTool:
        if estado.acao_pendente is None or estado.opcoes is None:
            return _MENU

        params = intencao.parametros
        opcao_num = params.opcao if isinstance(params, ParamsSelecionar) else 1

        opcao_selecionada = next(
            (op for op in estado.opcoes if op.numero == opcao_num), None
        )
        if opcao_selecionada is None:
            return _MENU

        # Resolve a seleção: avança o fluxo da ação pendente com a ref selecionada
        acao_pendente = estado.acao_pendente

        # Atualiza o payload com a ref selecionada e limpa as opcoes
        novo_payload = dict(estado.payload_pendente or {})
        novo_payload["registro"] = opcao_selecionada.ref

        # Limpa pendencia e re-executa a tool correspondente com a ref resolvida
        await self._store.limpar_pendencia(usuario_id)

        if acao_pendente == "excluir":
            resultado = await self.tool_excluir.executar(
                ParamsExcluir(referencia=None), usuario_id
            )
            # Override com a ref da opção selecionada
            resultado = ResultadoTool(
                acao="excluir",
                status=resultado.status,
                dados={**resultado.dados, "registro": opcao_selecionada.ref},
            )
        elif acao_pendente == "atualizar":
            resultado = await self.tool_atualizar.executar(
                ParamsAtualizar(), usuario_id
            )
            resultado = ResultadoTool(
                acao="atualizar",
                status=resultado.status,
                dados={**resultado.dados, "registro": opcao_selecionada.ref},
            )
        else:
            return _MENU

        await self._salvar_pendencia_se_necessario(resultado, usuario_id, agora)
        return resultado

    async def _handle_complementar(
        self,
        intencao: Intencao,
        estado: EstadoConversa,
        usuario_id: int,
        agora: datetime,
        contexto: dict[str, Any],
    ) -> ResultadoTool:
        if estado.acao_pendente is None:
            return _MENU

        params = intencao.parametros
        if not isinstance(params, ParamsComplementar):
            return _MENU

        campo = params.campo
        valor = params.valor

        payload = dict(estado.payload_pendente or {})
        campos_faltantes = list(estado.campos_faltantes)

        # Preenche o campo no payload (suporta lista de registros)
        if "registros" in payload:
            for reg in payload["registros"]:
                if isinstance(reg, dict) and reg.get(campo) is None:
                    reg[campo] = valor
        else:
            payload[campo] = valor

        # Remove o campo dos campos_faltantes
        campos_faltantes = [c for c in campos_faltantes if c != campo]

        # Salva o payload atualizado no estado
        novo_estado = estado.model_copy(
            update={
                "payload_pendente": payload,
                "campos_faltantes": campos_faltantes,
            }
        )
        await self._store.salvar(novo_estado)

        # Se ainda há campos faltantes, mantém pendência e retorna aguardando
        if campos_faltantes:
            return ResultadoTool(
                acao=estado.acao_pendente,  # type: ignore[arg-type]
                status="aguardando_complemento",
                dados={"campos_faltantes": campos_faltantes},
            )

        # Todos os campos preenchidos: avança o fluxo executando a tool com o payload atualizado
        acao_pendente = estado.acao_pendente

        if acao_pendente == "cadastrar":
            from agent.domain.intencao import ItemCadastro

            itens_raw = payload.get("registros", [])
            itens = [
                ItemCadastro.model_validate(item) if isinstance(item, dict) else item
                for item in itens_raw
            ]
            resultado = await self.tool_cadastrar.executar(itens, contexto)
        else:
            resultado = ResultadoTool(
                acao=acao_pendente,  # type: ignore[arg-type]
                status="concluido",
                dados=payload,
            )

        await self._salvar_pendencia_se_necessario(resultado, usuario_id, agora)
        return resultado

    # ------------------------------------------------------------------
    # Execução de intenções operacionais
    # ------------------------------------------------------------------

    async def _executar_operacional(
        self,
        intencao: Intencao,
        estado: EstadoConversa,
        usuario_id: int,
        agora: datetime,
        contexto: dict[str, Any],
    ) -> ResultadoTool:
        acao = intencao.acao
        params = intencao.parametros

        if acao == "cadastrar":
            itens = params.itens if isinstance(params, ParamsCadastrar) else []
            resultado = await self.tool_cadastrar.executar(itens, contexto)

        elif acao == "listar":
            p = params if isinstance(params, ParamsListar) else ParamsListar()
            resultado = await self.tool_listar.executar(p, contexto)

        elif acao == "atualizar":
            p = params if isinstance(params, ParamsAtualizar) else ParamsAtualizar()
            resultado = await self.tool_atualizar.executar(p, usuario_id)

        elif acao == "excluir":
            p = params if isinstance(params, ParamsExcluir) else ParamsExcluir()
            resultado = await self.tool_excluir.executar(p, usuario_id)

        elif acao == "conversar":
            mensagem = contexto.get("mensagem", "")
            historico = estado.historico
            resultado = await self.tool_conversar.executar(mensagem, historico)

        else:
            return _MENU

        await self._salvar_pendencia_se_necessario(resultado, usuario_id, agora)
        return resultado

    # ------------------------------------------------------------------
    # Persistência de estado pós-tool
    # ------------------------------------------------------------------

    async def _salvar_pendencia_se_necessario(
        self,
        resultado: ResultadoTool,
        usuario_id: int,
        agora: datetime,
    ) -> None:
        if resultado.status not in _STATUS_PENDENTES:
            return

        dados = resultado.dados
        payload_pendente = dict(dados) if dados else {}
        opcoes_raw = dados.get("opcoes") if dados else None
        campos_faltantes = dados.get("campos_faltantes", []) if dados else []

        from agent.domain.estado import OpcaoPendente

        opcoes = None
        if opcoes_raw is not None:
            opcoes = [
                OpcaoPendente.model_validate(op) if isinstance(op, dict) else op
                for op in opcoes_raw
            ]

        estado_atual = await self._store.obter(usuario_id, agora)
        novo_estado = estado_atual.model_copy(
            update={
                "acao_pendente": resultado.acao,
                "payload_pendente": payload_pendente,
                "campos_faltantes": campos_faltantes
                if isinstance(campos_faltantes, list)
                else [],
                "opcoes": opcoes,
                "expira_em": agora + _TTL_PENDENCIA,
            }
        )
        await self._store.salvar(novo_estado)
