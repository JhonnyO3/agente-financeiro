# Contrato: Janela de 13 meses e projeção

**Status:** Congelado
**Fronteira:** services de `mensal`, `evolucao` e `projecao` no backend

## Janela

13 meses fixos: **6 anteriores + mês atual + 6 futuros**, em ordem crescente. Primeiro dia de
cada mês. Função utilitária compartilhada:

```python
def janela_meses(hoje: date) -> list[date]:
    base = hoje.year * 12 + hoje.month - 1 - 6
    return [date((base + i) // 12, (base + i) % 12 + 1, 1) for i in range(13)]
```

Consulta ao repositório: `listar_por_periodo(meses[0], ultimo_dia(meses[-1]))`, onde
`ultimo_dia` é o último dia do mês +6.

## Agregação / projeção (decisão aprovada)

- A soma de cada mês considera **todas as transações** cuja `data` cai no mês — passado e futuro,
  **independente de status** (PAGO ou PENDENTE). Não filtrar por `PENDENTE`.
- Meses futuros são "projeção" no sentido de que seus valores vêm de parcelas e receitas já
  registradas com vencimento futuro (o agente cria as linhas; aqui só somamos).
- **Todos os 13 meses aparecem** na resposta, com `0.00` onde não houver dados (série contínua).

## Aplicação por endpoint

- `mensal`: soma por `CATEGORIAS_GASTO` (tipo GASTO), 13 meses.
- `evolucao`: `gastos` (GASTO), `investimentos` (INVESTIMENTO), `receitas` (RECEITA), 13 meses.
- `projecao`: mantém os campos atuais, 13 meses, somando todas as transações do mês.
