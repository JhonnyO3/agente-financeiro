# Contrato: Extração v2 (ExtracaoResult)

**Status:** Congelado
**Usado por:** T02 (produz), T03 (consome)

## `app/agents/extrator.py` — `ExtracaoResult` passa a ser

```python
class ExtracaoResult(BaseModel):
    tipo: Literal["GASTO", "INVESTIMENTO", "RECEITA"]   # + RECEITA
    valor_total: Decimal          # quando o usuário deu o total; se deu valor da
                                  # parcela, = valor_por_parcela * parcela_total
    valor_por_parcela: Decimal | None   # preenchido quando o usuário deu o valor DA PARCELA
    parcela_total: int = 1
    parcela_atual: int = 1        # NOVO — "parcela 2/4" → 2; ausente → 1
    descricao: str | None         # nome curto (como hoje)
    detalhes: str | None = None   # NOVO — contexto extra da mensagem; seca → None
    data_referencia: date         # data informada = data da PARCELA ATUAL
    menciona_cartao: bool
    forma_pagamento: Literal["PIX", "CARTAO", "OUTRO"] = "OUTRO"  # NOVO
    responsavel: str = "Jhonatas" # NOVO — capturado se mencionado
```

## Semântica (vale para o prompt `prompts/sistema.md`)

- "R$ 200, parcela 2/4" → `valor_por_parcela=200, valor_total=800, parcela_total=4, parcela_atual=2`
- "900 em 6x" → `valor_por_parcela=None, valor_total=900, parcela_total=6, parcela_atual=1`
- "paguei no pix" → `forma_pagamento=PIX`; "no cartão" → `CARTAO` e `menciona_cartao=True`
- "minha mãe comprou..." → `responsavel="Mãe"`
- "recebi salário 5000" → `tipo=RECEITA`
- Mensagem com contexto extra → `detalhes` com o contexto em frase curta; sem contexto → `None`

## Compatibilidade

Campos novos têm default — chamadas existentes (`executar_com_parcelas_confirmadas`,
fluxo AGUARDAR_PARCELAS) seguem funcionando sem mudança de assinatura de `extrair()`.
