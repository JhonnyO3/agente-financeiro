# Tarefa 01 — Parser de período (`parsear_periodo`)

**Stack:** python
**Depende de:** `parser-periodo.md` (congelado)
**Contrato:** `contracts/parser-periodo.md`

## Objetivo

Criar o módulo puro `agent/services/parser_periodo.py` que resolve qualquer string de período
para `(inicio: date, fim: date, label: str)` segundo a tabela de mapeamento, sem nunca levantar
exceção (fallback silencioso para o mês atual).

## Arquivos (posse exclusiva)

- `agent/services/parser_periodo.py`
- `tests/test_parser_periodo.py`

## Escopo

1. `parsear_periodo(periodo: str | None, relogio: Relogio) -> tuple[date, date, str]`.
2. Constantes internas `_MESES_PT` (com `março`/`marco`) e `_MESES_LABEL` (`Jan`..`Dez`).
3. Helper interno para 1º/último dia do mês (via `calendar.monthrange`).
4. Tratar, nesta ordem de desambiguação: `hoje`/`ontem` → `semana_atual`/`semana_passada` →
   `mes_atual`/`None`/`mes_passado` → `YYYY-MM-DD` → `YYYY-MM` → nome de mês PT → fallback.
5. Semana ISO: início = segunda (`hoje - timedelta(days=hoje.weekday())`), fim = +6 dias;
   semana passada = cada extremo − 7 dias.
6. Nenhum I/O, rede ou estado global. `relogio.hoje()` é a única fonte de "hoje".

## Critérios de aceite → teste

- [ ] `parsear_periodo("hoje", r)` → `(hoje, hoje, "hoje")`
- [ ] `parsear_periodo("ontem", r)` → `(hoje-1, hoje-1, "ontem")`
- [ ] `parsear_periodo("semana_atual", r)` → segunda e domingo da semana corrente, label `"semana atual"`
- [ ] `parsear_periodo("semana_passada", r)` → segunda e domingo da semana anterior, label `"semana passada"`
- [ ] caso `hoje = domingo`: `semana_atual` devolve a seg–dom da semana corrente
- [ ] `parsear_periodo("mes_atual", r)` e `parsear_periodo(None, r)` → 1º e último do mês atual, label `"Jun/2026"`
- [ ] `parsear_periodo("mes_passado", r)` → 1º e último do mês anterior, **sem fallback** (inclui virada de ano)
- [ ] `parsear_periodo("2026-05", r)` → `(date(2026,5,1), date(2026,5,31), "Mai/2026")`
- [ ] `parsear_periodo("2026-06-15", r)` → `(date(2026,6,15), date(2026,6,15), "15/06/2026")`
- [ ] `parsear_periodo("junho", r)` → 1º e 30/06 do ano corrente, label `"Jun/2026"`
- [ ] `parsear_periodo("março", r)` e `parsear_periodo("marco", r)` resolvem março
- [ ] `parsear_periodo("valor_invalido", r)` → mês atual (fallback) sem exceção
- [ ] `parsear_periodo("2026-13", r)` (mês inválido) → fallback sem exceção
- [ ] Testes usam `Relogio(tz, _fixed=...)` com "hoje" fixado; sem rede/DB/LLM

## Verificação local

```bash
uv run pytest tests/test_parser_periodo.py -v
```
