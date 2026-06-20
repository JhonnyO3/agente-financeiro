# Tarefa 07 — Testes mínimos (smoke tests das novas classes)

**Stack:** python  
**Estado:** todo  
**Depende de:** 01, 03, 04  
**Bloqueia:** nenhuma

## Objetivo

Só o mínimo necessário para CI não passar cego: um smoke test por classe nova e dois casos de regressão críticos. Não duplicar cobertura já existente.

## Arquivos que esta tarefa possui

- `tests/test_extrator.py` ← criar (novo, classe nova)
- `tests/test_tool_cadastrar.py` ← 2 casos novos apenas

## NÃO toca em

- `tests/test_roteador.py` (os existentes já cobrem o fluxo)
- `tests/test_prompts.py` (já tem cobertura de renderização)

## `tests/test_extrator.py` — 3 casos

```python
import pytest
from unittest.mock import AsyncMock, MagicMock
from decimal import Decimal
from agent.domain.intencao import ItemCadastro, ParamsCadastrar
from agent.services.extrator import Extrator


def _llm_mock(itens: list[dict]):
    chain = AsyncMock()
    chain.ainvoke = AsyncMock(
        return_value=ParamsCadastrar(itens=[ItemCadastro(**i) for i in itens])
    )
    llm = MagicMock()
    llm.with_structured_output.return_value = chain
    return llm, chain


@pytest.mark.asyncio
async def test_extrator_preenche_campo_none():
    llm, _ = _llm_mock([{"descricao": "mercado", "valor": Decimal("200"), "forma_pagamento": "PIX"}])
    resultado = await Extrator(llm).extrair_cadastro(
        [ItemCadastro(descricao="mercado", valor=Decimal("200"))], "comprei", []
    )
    assert resultado[0].forma_pagamento == "PIX"


@pytest.mark.asyncio
async def test_extrator_nao_sobrescreve_valor_existente():
    llm, _ = _llm_mock([{"descricao": "roupa", "valor": None, "forma_pagamento": "CARTAO_CREDITO"}])
    resultado = await Extrator(llm).extrair_cadastro(
        [ItemCadastro(descricao="roupa", valor=Decimal("150"))], "comprei roupa", []
    )
    assert resultado[0].valor == Decimal("150")


@pytest.mark.asyncio
async def test_extrator_inclui_historico_no_prompt():
    llm, chain = _llm_mock([{"descricao": "roupa"}])
    await Extrator(llm).extrair_cadastro(
        [ItemCadastro(descricao="roupa")], "foi 350",
        ["usuario: comprei roupa", "assistente: quanto custou?"]
    )
    prompt = chain.ainvoke.call_args[0][0]
    assert "comprei roupa" in prompt
```

## Novos casos em `tests/test_tool_cadastrar.py` — 2 apenas

```python
@pytest.mark.asyncio
async def test_forma_pagamento_ausente_sem_pista_entra_em_campos_faltantes(tool_cadastrar):
    item = ItemCadastro(descricao="açougue", valor=Decimal("50"))
    resultado = await tool_cadastrar.executar([item], {})
    assert resultado.status == "aguardando_complemento"
    assert "forma_pagamento" in resultado.dados["campos_faltantes"]


@pytest.mark.asyncio
async def test_forma_pagamento_ausente_com_parcelas_nao_pergunta(tool_cadastrar):
    item = ItemCadastro(descricao="notebook", valor=Decimal("3000"), total_parcelas=12, parcela_atual=1)
    resultado = await tool_cadastrar.executar([item], {})
    assert "forma_pagamento" not in resultado.dados.get("campos_faltantes", [])
```

## Critério de verificação local

```bash
uv run pytest tests/test_extrator.py tests/test_tool_cadastrar.py -v
uv run pytest tests/ -v  # suite completa verde (sem regressões)
```
