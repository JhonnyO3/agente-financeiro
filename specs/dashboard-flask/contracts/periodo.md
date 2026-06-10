# Contrato: Resolução de Período

**Status:** Congelado
**Usado por:** T01 (implementa), T02, T03, T04, T05 (consomem)

---

## Módulo: `dashboard/periodo.py`

### Função principal

```python
from datetime import date
from dateutil.relativedelta import relativedelta  # ou cálculo manual

def resolver_periodo(periodo: str) -> tuple[date, date]:
    ...
```

### Mapeamento de valores

| `periodo` (query param) | `inicio` | `fim` |
|------------------------|----------|-------|
| `mes_atual` (padrão) | `date(hoje.year, hoje.month, 1)` | `hoje` |
| `mes_anterior` | Primeiro dia do mês anterior | Último dia do mês anterior |
| `ultimos_3_meses` | `hoje - 90 dias` | `hoje` |
| `ultimos_6_meses` | `hoje - 180 dias` | `hoje` |
| `ano_atual` | `date(hoje.year, 1, 1)` | `hoje` |
| `tudo` | `date(2000, 1, 1)` | `hoje` |
| qualquer outro | `date(hoje.year, hoje.month, 1)` | `hoje` (fallback seguro) |

### Regra para `mes_anterior`

```python
primeiro_mes_atual = date(hoje.year, hoje.month, 1)
ultimo_mes_anterior = primeiro_mes_atual - timedelta(days=1)
inicio = date(ultimo_mes_anterior.year, ultimo_mes_anterior.month, 1)
fim = ultimo_mes_anterior
```

### Constante de piso

```python
DATA_PISO = date(2000, 1, 1)  # consistente com o agente
```

### Valores válidos (para validação nos blueprints)

```python
PERIODOS_VALIDOS = frozenset({
    "mes_atual", "mes_anterior",
    "ultimos_3_meses", "ultimos_6_meses",
    "ano_atual", "tudo"
})
```

## Uso nos blueprints

```python
from dashboard.periodo import resolver_periodo

periodo = request.args.get("periodo", "mes_atual")
inicio, fim = resolver_periodo(periodo)
```
