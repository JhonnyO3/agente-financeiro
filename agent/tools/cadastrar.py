"""ToolCadastrar: monta registros de cadastro sem persistir.

Regras conforme specs/melhorias-agente/fluxo-atendimento-cadastro.md (regras 1–9)
e contracts/resultado-tools.md.
"""

from __future__ import annotations

from datetime import date, timezone
from typing import Any
from uuid import uuid4

from agent.config import settings
from agent.domain.intencao import ItemCadastro
from agent.domain.resultado import ResultadoTool
from agent.services.relogio import Relogio
from agent.tools._parcelas import (
    adicionar_meses,
    status_por_data,
    valores_das_parcelas,
)

# Meses em português (1-indexed)
_MESES_PT = [
    "Jan",
    "Fev",
    "Mar",
    "Abr",
    "Mai",
    "Jun",
    "Jul",
    "Ago",
    "Set",
    "Out",
    "Nov",
    "Dez",
]

# Forma de pagamento inferida quando ausente
_FORMA_PIX = "PIX"
_FORMA_CARTAO = "CARTAO_CREDITO"

# Formas que mapeiam para PAGO imediatamente
_FORMAS_PAGO = {"PIX", "CARTAO_DEBITO"}


def _inferir_forma(item: ItemCadastro) -> str:
    """Regras 1–3 do fluxo: ausente → PIX; parcela/cartão → CARTAO_CREDITO."""
    if item.forma_pagamento is None:
        if item.parcela_atual is not None or item.total_parcelas is not None:
            return _FORMA_CARTAO
        return _FORMA_PIX
    if item.forma_pagamento == "DINHEIRO":
        return _FORMA_PIX
    return item.forma_pagamento


def _tem_pista_clara(item: ItemCadastro) -> bool:
    """Retorna True se há pista suficiente para inferir forma sem perguntar ao usuário."""
    return (
        item.parcela_atual is not None
        or item.total_parcelas is not None
        or item.dia_vencimento is not None
    )


def _label_mes(d: date) -> str:
    return f"{_MESES_PT[d.month - 1]}/{str(d.year)[2:]}"


def _processar_item(
    item: ItemCadastro, hoje: date, responsavel: str
) -> list[dict[str, Any]]:
    """Retorna lista de registros (dicts) para um ItemCadastro."""
    forma = _inferir_forma(item)
    detalhes: str | None = None
    if item.forma_pagamento == "DINHEIRO":
        detalhes = "dinheiro"

    eh_parcelado = (
        item.parcela_atual is not None
        and item.total_parcelas is not None
        and item.total_parcelas > 1
    )

    if eh_parcelado:
        parcela_atual: int = item.parcela_atual  # type: ignore[assignment]
        total_parcelas: int = item.total_parcelas  # type: ignore[assignment]

        # Data da parcela atual: usa dia_vencimento no mês corrente se informado
        if item.dia_vencimento is not None:
            try:
                data_atual = date(hoje.year, hoje.month, item.dia_vencimento)
            except ValueError:
                # dia inválido para o mês, clampa
                import calendar as _cal

                ultimo = _cal.monthrange(hoje.year, hoje.month)[1]
                data_atual = date(
                    hoje.year, hoje.month, min(item.dia_vencimento, ultimo)
                )
        else:
            data_atual = hoje

        # Datas de todas as parcelas do grupo (índice 0 = parcela 1)
        todas_datas = [
            adicionar_meses(data_atual, i + 1 - parcela_atual)
            for i in range(total_parcelas)
        ]

        # Só atual + futuras (slice a partir de parcela_atual - 1)
        datas_restantes = todas_datas[parcela_atual - 1 :]

        # Valores das parcelas restantes
        if item.valor is not None:
            n_restantes = len(datas_restantes)
            valors = valores_das_parcelas(item.valor, n_restantes)
        else:
            valors = [None] * len(datas_restantes)  # type: ignore[list-item]

        grupo_id = str(uuid4())

        registros: list[dict[str, Any]] = []
        tipo = item.tipo or "GASTO"
        categoria = item.categoria or ("INVESTIMENTO" if tipo == "INVESTIMENTO" else "RECEITA" if tipo == "RECEITA" else "GASTOS_PONTUAIS")

        for idx, d in enumerate(datas_restantes):
            if idx == 0:
                # parcela atual: status por vencimento
                status = status_por_data(d, hoje).value
            else:
                # futuras: sempre PENDENTE
                status = "PENDENTE"

            reg: dict[str, Any] = {
                "descricao": item.descricao,
                "valor": valors[idx],
                "forma_pagamento": forma,
                "data": d,
                "status": status,
                "responsavel": responsavel,
                "grupo_parcela_id": grupo_id,
                "parcela_numero": parcela_atual + idx,
                "parcela_total": total_parcelas,
                "tipo": tipo,
                "categoria": categoria,
            }
            if detalhes is not None:
                reg["detalhes"] = detalhes
            registros.append(reg)
        return registros

    else:
        # Simples (não parcelado)
        if item.data is not None:
            try:
                from datetime import datetime

                data_reg = datetime.strptime(item.data, "%Y-%m-%d").date()
            except ValueError:
                data_reg = hoje
        else:
            data_reg = hoje

        if forma in _FORMAS_PAGO:
            status = "PAGO"
        else:
            status = "PENDENTE"

        tipo = item.tipo or "GASTO"
        categoria = item.categoria or ("INVESTIMENTO" if tipo == "INVESTIMENTO" else "RECEITA" if tipo == "RECEITA" else "GASTOS_PONTUAIS")

        reg = {
            "descricao": item.descricao,
            "valor": item.valor,
            "forma_pagamento": forma,
            "data": data_reg,
            "status": status,
            "responsavel": responsavel,
            "grupo_parcela_id": str(uuid4()),
            "parcela_numero": 1,
            "parcela_total": 1,
            "tipo": tipo,
            "categoria": categoria,
        }
        if detalhes is not None:
            reg["detalhes"] = detalhes
        return [reg]


class ToolCadastrar:
    """Tool determinística que monta registros sem persistir."""

    def __init__(self, relogio: Relogio, repository: Any) -> None:
        self._relogio = relogio
        self._repository = repository

    async def executar(
        self, itens: list[ItemCadastro], contexto: dict[str, Any]
    ) -> ResultadoTool:
        # Usa a data UTC do instante fixado no relógio para que testes com
        # _fixed=datetime(..., tzinfo=UTC) obtenham a data correta.
        hoje = self._relogio.agora().astimezone(timezone.utc).date()
        responsavel: str = contexto.get("responsavel") or settings.RESPONSAVEL_PADRAO

        # Verifica campos obrigatórios faltantes
        campos_faltantes: list[str] = []
        for item in itens:
            if item.valor is None:
                if "valor" not in campos_faltantes:
                    campos_faltantes.append("valor")
            if item.forma_pagamento is None and not _tem_pista_clara(item):
                if "forma_pagamento" not in campos_faltantes:
                    campos_faltantes.append("forma_pagamento")

        if campos_faltantes:
            return ResultadoTool(
                acao="cadastrar",
                status="aguardando_complemento",
                dados={"campos_faltantes": campos_faltantes},
            )

        todos_registros: list[dict[str, Any]] = []
        for item in itens:
            registros = _processar_item(item, hoje, responsavel)
            todos_registros.extend(registros)

        # Monta parcelas_futuras para itens parcelados
        parcelas_futuras: list[str] = []
        for item in itens:
            eh_parcelado = (
                item.parcela_atual is not None
                and item.total_parcelas is not None
                and item.total_parcelas > 1
            )
            if eh_parcelado:
                assert item.parcela_atual is not None
                assert item.total_parcelas is not None
                parcela_atual = item.parcela_atual
                total_parcelas = item.total_parcelas
                if item.dia_vencimento is not None:
                    try:
                        data_atual = date(hoje.year, hoje.month, item.dia_vencimento)
                    except ValueError:
                        import calendar as _cal

                        ultimo = _cal.monthrange(hoje.year, hoje.month)[1]
                        data_atual = date(
                            hoje.year, hoje.month, min(item.dia_vencimento, ultimo)
                        )
                else:
                    data_atual = hoje

                todas_datas = [
                    adicionar_meses(data_atual, i + 1 - parcela_atual)
                    for i in range(total_parcelas)
                ]
                # Parcelas futuras = após a atual
                for d in todas_datas[parcela_atual:]:
                    label = _label_mes(d)
                    if label not in parcelas_futuras:
                        parcelas_futuras.append(label)

        if not todos_registros:
            return ResultadoTool(
                acao="cadastrar",
                status="aguardando_complemento",
                dados={"campos_faltantes": ["descricao", "valor"]},
            )

        dados: dict[str, Any] = {"registros": todos_registros}
        if parcelas_futuras:
            dados["parcelas_futuras"] = parcelas_futuras

        return ResultadoTool(
            acao="cadastrar",
            status="aguardando_confirmacao",
            dados=dados,
        )
