# Contrato: Helpers de data de parcelas (backend)

**Status:** Congelado
**Fronteira:** `backend/services/datas_parcela.py` ↔ `backend/services/grupos.py` (e qualquer service backend que monte cadeias de datas/status de parcela)

## Decisão de camada

O backend **não importa de `agent`** (camadas e deploys Docker separados). As funções puras
equivalentes existem em `agent/services/parcelas.py`, mas são **duplicadas** aqui (são
triviais e dependem só de `backend.models.enums`). `agent/services/parcelas.py` permanece
intocado.

## Assinaturas (idênticas às do agente, mesma semântica)

```python
from datetime import date
from backend.models.enums import StatusEnum

def adicionar_meses(data: date, meses: int) -> date: ...
def status_por_data(data: date, hoje: date | None = None) -> StatusEnum: ...
def datas_do_grupo(
    data_parcela_atual: date, parcela_atual: int, parcela_total: int
) -> list[date]: ...
```

### `adicionar_meses(data, meses)`
- Soma/subtrai `meses` preservando o dia; clampa para o último dia do mês quando o dia não
  existe (`31/01 + 1 → 28/02`, ou `29/02` em bissexto).

### `status_por_data(data, hoje=None)`
- `data < hoje` → `StatusEnum.PAGO`; senão `StatusEnum.PENDENTE`. `hoje` default `date.today()`.

### `datas_do_grupo(data_parcela_atual, parcela_atual, parcela_total)`
- Retorna `parcela_total` datas (índice 0 = parcela 1). A parcela em posição `parcela_atual`
  recebe `data_parcela_atual`; anteriores recuam e seguintes avançam via `adicionar_meses`.
- `datas[i] = adicionar_meses(data_parcela_atual, i + 1 - parcela_atual)`.

## Invariantes
- Funções **puras**, sem I/O, sem LLM, sem `date.today()` implícito exceto o default
  documentado de `status_por_data`.
- Aritmética de data, não monetária. Nenhuma destas funções toca em `Decimal`.
