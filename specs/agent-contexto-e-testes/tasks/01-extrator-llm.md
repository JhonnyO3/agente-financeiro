# Tarefa 01 — Classe Extrator (segunda etapa de extração)

**Stack:** python  
**Estado:** todo  
**Depende de:** nenhuma  
**Bloqueia:** 03

## Objetivo

Criar `agent/services/extrator.py` com a classe `Extrator` que faz a segunda chamada LLM para preencher campos de `ItemCadastro` usando o prompt `02-extracao-cadastrar.md`.

## Arquivos que esta tarefa possui

- `agent/services/extrator.py` ← criar
- `agent/services/__init__.py` ← pode precisar atualizar (apenas se houver re-export)

## NÃO toca em

- `agent/services/roteador.py` (tarefa 03)
- `agent/tools/cadastrar.py` (tarefa 04)
- Prompts (tarefa 02)

## Implementação

```python
# agent/services/extrator.py
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
        chain = self._llm.with_structured_output(ParamsCadastrar)
        resultado: ParamsCadastrar = await chain.ainvoke(prompt)

        # Mescla: mantém campos preenchidos pelo classificador, preenche os None
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
```

## Critério de verificação local

```bash
uv run pytest tests/test_extrator.py -v
```

Testes a criar (tarefa 07):
- `test_extrator_preenche_forma_pagamento`: mock do LLM retorna forma; verifica que Extrator devolve item com forma preenchida.
- `test_extrator_mantém_valor_do_classificador`: classificador já preencheu valor; Extrator não sobrescreve com None.
- `test_extrator_usa_historico`: verifica que o prompt construído contém o histórico.
