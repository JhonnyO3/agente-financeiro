# Tarefa 02 — API Resumo e Categorias

**Stack:** python
**Dependências:** 01
**Contratos:** `contracts/db-session.md`, `contracts/periodo.md`, `contracts/api-json.md`, `contracts/repository-reuse.md`

---

## Objetivo

Implementar os endpoints que alimentam os cards de resumo (RF-02) e o gráfico de pizza de categorias (RF-03).

---

## Arquivos que esta tarefa possui

- `dashboard/blueprints/api_resumo.py`

---

## O que implementar

### Blueprint `api_resumo` com prefixo `/api`

#### `GET /api/resumo`

1. Ler `?periodo` da query string (default `mes_atual`)
2. Chamar `resolver_periodo(periodo)` → `(inicio, fim)`
3. `listar_por_periodo(inicio, fim)` → lista de `Transacao`
4. Somar `valor` por tipo usando `Decimal` (nunca float):
   - `gastos = sum(t.valor for t in transacoes if t.tipo == "GASTO")`
   - `investimentos = sum(t.valor for t in transacoes if t.tipo == "INVESTIMENTO")`
   - `saldo = investimentos - gastos`
5. Retornar JSON conforme `contracts/api-json.md`:
   ```json
   {"gastos": "350.00", "investimentos": "500.00", "saldo": "150.00", "periodo": "mes_atual"}
   ```

#### `GET /api/grafico/categorias`

1. Ler `?periodo`
2. `listar_por_periodo(inicio, fim)` e filtrar `tipo == GASTO` em Python
   — **não usar `agregar_por_categoria`**: verificado que o método não filtra
   por tipo e misturaria investimentos (ver `contracts/repository-reuse.md`)
3. Agregar por categoria com `Decimal`
4. Calcular `total_geral = sum(totais)`
5. Calcular `percentual = round(float(total / total_geral * 100), 2)`
6. Filtrar itens com `total > 0`
7. Retornar array ordenado por `total DESC`

---

## Critérios de aceite

- [ ] `GET /api/resumo` retorna `gastos`, `investimentos`, `saldo` como strings decimais
- [ ] Saldo é `investimentos - gastos` (pode ser negativo)
- [ ] `GET /api/grafico/categorias` exclui categorias com total = 0
- [ ] Percentuais somam 100 (ou próximo de 100 por arredondamento)
- [ ] Mudando `?periodo` muda os valores retornados
- [ ] `periodo=tudo` soma todos os registros desde 2000-01-01

---

## Comando de verificação

```bash
curl "http://localhost:5000/api/resumo?periodo=mes_atual"
curl "http://localhost:5000/api/grafico/categorias?periodo=mes_atual"
```
