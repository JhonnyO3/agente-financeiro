# Contrato — ToolCadastrar campos faltantes expandidos

**Status: Congelado**

## Regra de `forma_pagamento` como campo faltante

Após receber `itens: list[ItemCadastro]` (já extraídos pelo Extrator):

```python
for item in itens:
    if item.valor is None:
        campos_faltantes.append("valor")
    if item.forma_pagamento is None and not _tem_pista_clara(item):
        if "forma_pagamento" not in campos_faltantes:
            campos_faltantes.append("forma_pagamento")
```

## Critério `_tem_pista_clara`

Retorna `True` (não pergunta) quando:
- `item.parcela_atual is not None` ou `item.total_parcelas is not None` → implica cartão
- `item.dia_vencimento is not None` → implica cartão

Retorna `False` (pergunta) quando todos os três campos acima são None.

## Mensagem de complemento esperada

Quando `campos_faltantes = ["forma_pagamento"]`, o Formatador produz algo como:
> "Como foi o pagamento? PIX, cartão de crédito ou débito?"

## Sem quebra de compatibilidade

- Itens com `forma_pagamento` preenchido: comportamento idêntico ao atual.
- Itens com parcelas: `_inferir_forma` resolve para CARTAO_CREDITO, não pergunta.
- Só pergunta quando `forma_pagamento is None` E sem pista de parcelamento/vencimento.
