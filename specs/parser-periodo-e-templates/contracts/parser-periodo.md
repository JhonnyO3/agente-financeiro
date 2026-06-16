# Contrato: Parser de Período Natural

**Status:** Congelado
**Fronteira:** `agent/services/parser_periodo.py` (novo), consumido por `agent/tools/listar.py`

## Assinatura

```python
# agent/services/parser_periodo.py
from datetime import date
from agent.services.relogio import Relogio

def parsear_periodo(periodo: str | None, relogio: Relogio) -> tuple[date, date, str]:
    """
    Resolve a string de período para (inicio, fim, label).
    NUNCA levanta exceção — fallback silencioso para o mês atual.
    """
```

- `relogio.hoje()` é a única fonte de "hoje" (fuso do usuário). Determinístico em teste via `_fixed`.
- Retorno sempre `(inicio: date, fim: date, label: str)` com `inicio <= fim`.
- Entrada é normalizada com `.strip().lower()` antes de casar nome de mês (datas/`YYYY-MM` casam crus).

## Tabela de mapeamento (a verdade)

Referência de "hoje" para os labels de exemplo: **15/06/2026 (segunda-feira)**.

| Valor recebido | Início | Fim | Label |
|---|---|---|---|
| `"hoje"` | hoje | hoje | `"hoje"` |
| `"ontem"` | hoje − 1 dia | hoje − 1 dia | `"ontem"` |
| `"semana_atual"` | segunda-feira desta semana (ISO) | domingo desta semana | `"semana atual"` |
| `"semana_passada"` | segunda-feira da semana anterior | domingo da semana anterior | `"semana passada"` |
| `"mes_atual"` ou `None` | 1º do mês atual | último dia do mês atual | `"<Mmm>/<ano>"` (ex: `"Jun/2026"`) |
| `"mes_passado"` | 1º do mês anterior | último dia do mês anterior | `"<Mmm>/<ano>"` (ex: `"Mai/2026"`) |
| `"YYYY-MM"` (ex: `"2026-05"`) | 1º do mês | último dia do mês | `"<Mmm>/<ano>"` (ex: `"Mai/2026"`) |
| `"YYYY-MM-DD"` (ex: `"2026-06-10"`) | data exata | data exata | `"dd/mm/yyyy"` (ex: `"10/06/2026"`) |
| nome de mês PT (ex: `"junho"`) | 1º do mês no ano atual | último dia do mês | `"<Mmm>/<ano>"` (ex: `"Jun/2026"`) |
| qualquer outro / inválido | 1º do mês atual | último dia do mês atual | `"<Mmm>/<ano>"` (fallback) |

### Regras de borda (congeladas)

- **Semana ISO:** segunda-feira é o início (`date.weekday() == 0`); domingo é o fim.
  `inicio_semana = hoje - timedelta(days=hoje.weekday())`; `fim_semana = inicio_semana + 6 dias`.
  Quando hoje é domingo, "semana_atual" devolve a seg–dom da semana corrente (em andamento).
  "semana_passada" subtrai 7 dias de cada extremo.
- **Mês anterior:** 1º do mês atual − 1 dia define o mês anterior; usar `calendar.monthrange` para o
  último dia (cobre virada de ano: jan/2026 → dez/2025).
- **`YYYY-MM-DD`:** validado com `date.fromisoformat`; em falha, cai no fallback.
- **`YYYY-MM`:** comprimento 7 e `[4] == "-"`; `int` de ano e mês; em `ValueError` cai no fallback.
- **Nome de mês PT:** dicionário com `janeiro`..`dezembro` incluindo `março` e `marco` (sem acento).
- **Labels de mês:** `Jan, Fev, Mar, Abr, Mai, Jun, Jul, Ago, Set, Out, Nov, Dez`.

## Vocabulário interno (constantes congeladas)

```python
_MESES_PT: dict[str, int]      # nome PT (lower) -> número do mês (com março/marco)
_MESES_LABEL: dict[int, str]   # número -> abreviação ("Jan".."Dez")
```

## Consumo em `ToolListar`

`agent/tools/listar.py`:
- `_resolver_periodo` é **removido** (junto com `_MESES_PT`, `_MESES_LABEL`, `_primeiro_e_ultimo_dia`
  se migrarem inteiramente para o parser).
- A linha de resolução passa a ser `inicio, fim, periodo_label = parsear_periodo(params.periodo, self._relogio)`.
- Nenhuma outra mudança de comportamento em `ToolListar` (filtros, grupos, totais inalterados).

## Garantias

- Função pura sobre `(periodo, relogio)`; sem I/O, sem rede, sem estado global.
- Não levanta exceção para nenhuma entrada `str | None`.
