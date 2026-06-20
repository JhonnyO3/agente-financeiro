# Tarefa 04 — ToolCadastrar: pedir `forma_pagamento` quando ambígua

**Stack:** python  
**Estado:** todo  
**Depende de:** nenhuma (independente de 01 e 03)  
**Bloqueia:** nenhuma

## Objetivo

Modificar `ToolCadastrar.executar` para adicionar `"forma_pagamento"` a `campos_faltantes` quando o item não tem forma e não tem pista clara de parcelamento/vencimento. Implementar `_tem_pista_clara`.

## Arquivos que esta tarefa possui

- `agent/tools/cadastrar.py` ← modificar

## NÃO toca em

- `agent/services/extrator.py`
- `agent/services/roteador.py`

## Mudanças em `cadastrar.py`

### Adicionar função `_tem_pista_clara`

```python
def _tem_pista_clara(item: ItemCadastro) -> bool:
    """Retorna True se há pista suficiente para inferir forma sem perguntar."""
    return (
        item.parcela_atual is not None
        or item.total_parcelas is not None
        or item.dia_vencimento is not None
    )
```

### Modificar `executar` — loop de campos faltantes

```python
campos_faltantes: list[str] = []
for item in itens:
    if item.valor is None:
        if "valor" not in campos_faltantes:
            campos_faltantes.append("valor")
    if item.forma_pagamento is None and not _tem_pista_clara(item):
        if "forma_pagamento" not in campos_faltantes:
            campos_faltantes.append("forma_pagamento")
```

## Critério de verificação local

```bash
uv run pytest tests/test_tool_cadastrar.py -v
```

Casos a cobrir (novos testes na tarefa 07):
- `test_forma_pagamento_ausente_sem_pista_pergunta`: item sem forma e sem parcelas → `campos_faltantes=["forma_pagamento"]`
- `test_forma_pagamento_ausente_com_parcelas_nao_pergunta`: item sem forma mas `total_parcelas=3` → não adiciona forma_pagamento a faltantes
- `test_forma_pagamento_ausente_com_vencimento_nao_pergunta`: item sem forma mas `dia_vencimento=10` → não pergunta
- `test_forma_e_valor_ambos_faltantes`: ambos ausentes → `campos_faltantes=["valor", "forma_pagamento"]`
