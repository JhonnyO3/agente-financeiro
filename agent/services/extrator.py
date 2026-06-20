from __future__ import annotations

import json
from datetime import date
from typing import Any

from agent.config import settings
from agent.domain.intencao import ItemCadastro, ParamsCadastrar
from agent.services.prompts import montar_prompt


class Extrator:
    def __init__(self, llm: Any) -> None:
        self._llm = llm

    async def extrair_cadastro(
        self,
        itens_parciais: list[ItemCadastro],
        mensagem_original: str,
        historico: list[str],
        contexto_extra: dict[str, Any] | None = None,
    ) -> list[ItemCadastro]:
        historico_recente = "\n".join(historico) if historico else ""
        parametros_str = json.dumps(
            [item.model_dump(exclude_none=False) for item in itens_parciais],
            ensure_ascii=False,
            default=str,
        )

        ctx: dict[str, Any] = {
            "mensagem": mensagem_original,
            "historico_recente": historico_recente,
            "estado_pendente": "nenhuma",
            "user_name": settings.RESPONSAVEL_PADRAO,
            "data_atual": date.today().strftime("%d/%m/%Y"),
            "parametros": parametros_str,
        }
        if contexto_extra:
            ctx.update(contexto_extra)

        prompt = montar_prompt("cadastrar", ctx)
        chain = self._llm.with_structured_output(ParamsCadastrar, method="function_calling")
        resultado: ParamsCadastrar = await chain.ainvoke(prompt)

        # Mescla: mantém campos já preenchidos pelo classificador, preenche os None
        itens_completos: list[ItemCadastro] = []
        for parcial, completo in zip(itens_parciais, resultado.itens):
            merged = parcial.model_dump()
            for campo, valor in completo.model_dump().items():
                if merged.get(campo) is None and valor is not None:
                    merged[campo] = valor
            itens_completos.append(ItemCadastro.model_validate(merged))

        # Se o extrator retornou mais itens que o classificador, inclui todos
        if len(resultado.itens) > len(itens_parciais):
            itens_completos.extend(resultado.itens[len(itens_parciais):])

        return itens_completos
