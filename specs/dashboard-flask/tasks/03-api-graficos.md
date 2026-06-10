# Tarefa 03 — API Gráficos Temporais

**Stack:** python
**Dependências:** 01
**Contratos:** `contracts/db-session.md`, `contracts/api-json.md`, `contracts/repository-reuse.md`

---

## Objetivo

Implementar os endpoints que alimentam os gráficos de barras mensais (RF-04) e de linha de evolução (RF-05).

---

## Arquivos que esta tarefa possui

- `dashboard/blueprints/api_graficos.py`

---

## O que implementar

### Blueprint `api_graficos` com prefixo `/api/grafico`

#### `GET /api/grafico/mensal`

Sempre mostra **últimos 6 meses** — ignora `?periodo`.

1. Calcular `inicio = date.today().replace(day=1) - relativedelta(months=5)` (ou equivalente)
   - Equivale ao primeiro dia de 6 meses atrás (inclusive o mês atual)
2. `listar_por_periodo(inicio, date.today())` → lista de `Transacao`
3. Filtrar apenas `tipo == "GASTO"`
4. Gerar lista dos 6 meses (label `"Jun/26"` etc.) em ordem crescente
5. Para cada mês, somar por categoria — resultado: `{"mes": "Jan/26", "ALIMENTACAO": "200.00", ...}`
6. Incluir **todas as 7 categorias de gasto** mesmo com valor `"0.00"`:
   `ALIMENTACAO, TRANSPORTE, LAZER, GASTOS_FIXOS, COMPRAS, GASTOS_PONTUAIS, OUTROS`
   (a categoria `INVESTIMENTO` fica de fora — o gráfico filtra `tipo == GASTO`)
7. Retornar array com 6 elementos

**Helper para formatar mês:**
```python
from datetime import date
MESES_PT = ["Jan","Fev","Mar","Abr","Mai","Jun","Jul","Ago","Set","Out","Nov","Dez"]
def fmt_mes(d: date) -> str:
    return f"{MESES_PT[d.month-1]}/{str(d.year)[2:]}"
```

#### `GET /api/grafico/evolucao`

1. `listar_por_periodo(date(2000,1,1), date.today())` → todos os registros
2. Agrupar por mês (chave: `(ano, mes)`)
3. Para cada mês: somar `gastos` e `investimentos` separados
4. Ordenar por data crescente
5. Retornar apenas meses com pelo menos 1 registro

---

## Critérios de aceite

- [ ] `GET /api/grafico/mensal` sempre retorna exatamente 6 elementos
- [ ] Todas as 7 categorias de gasto estão presentes em cada mês
- [ ] `GET /api/grafico/evolucao` retorna um elemento por mês com dados
- [ ] Meses sem dados não aparecem em `/evolucao`
- [ ] Formato do label: `"Jun/26"` (3 letras + `/` + 2 dígitos do ano)
- [ ] `/mensal` ignora `?periodo`

---

## Comando de verificação

```bash
curl "http://localhost:5000/api/grafico/mensal"
curl "http://localhost:5000/api/grafico/evolucao"
```
