# Contrato: Modelo de Dados v2

**Status:** Congelado
**Usado por:** todas as tarefas

## Enums (`app/models/enums.py`)

```python
class TipoEnum(str, enum.Enum):
    GASTO = "GASTO"
    INVESTIMENTO = "INVESTIMENTO"
    RECEITA = "RECEITA"            # novo

class CategoriaEnum(str, enum.Enum):
    # ... 8 existentes ...
    RECEITA = "RECEITA"            # novo
    PARCELAMENTOS = "PARCELAMENTOS"  # novo

class StatusEnum(str, enum.Enum):      # novo
    PAGO = "PAGO"
    PENDENTE = "PENDENTE"

class FormaPagamentoEnum(str, enum.Enum):  # novo
    PIX = "PIX"
    CARTAO = "CARTAO"
    OUTRO = "OUTRO"
```

## Colunas novas em `transacoes` (`app/models/transacao.py`)

```python
status: Mapped[StatusEnum] = mapped_column(String, nullable=False, server_default="PENDENTE")
forma_pagamento: Mapped[FormaPagamentoEnum] = mapped_column(String, nullable=False, server_default="OUTRO")
responsavel: Mapped[str] = mapped_column(String, nullable=False, server_default="Jhonatas")
detalhes: Mapped[str | None] = mapped_column(TEXT, nullable=True)
```

## Migration `0002` (Alembic)

- `op.add_column` das 4 colunas com `server_default` acima
- Data-fix retroativo: `UPDATE transacoes SET status='PAGO' WHERE data < CURRENT_DATE`
- `downgrade`: `op.drop_column` das 4

## DTOs (`app/repositories/dtos.py`)

`TransacaoCreate` ganha (nesta ordem, após `embedding`):
```python
status: StatusEnum = StatusEnum.PENDENTE
forma_pagamento: FormaPagamentoEnum = FormaPagamentoEnum.OUTRO
responsavel: str = "Jhonatas"
detalhes: str | None = None
```

`TransacaoUpdate` ganha (todos `= None`):
```python
status: StatusEnum | None = None
forma_pagamento: FormaPagamentoEnum | None = None
responsavel: str | None = None
detalhes: str | None = None
```

`criar`/`criar_lote` no repository repassam os 4 campos ao construtor `Transacao(...)`.
`atualizar` não muda (usa `asdict` + não-None).

## Helper de parcelas (`app/services/parcelas.py` — novo, funções puras)

```python
def adicionar_meses(data: date, meses: int) -> date:
    """Soma/subtrai meses preservando o dia; clampa para o último dia do mês
    quando o dia não existe (31/01 + 1 → 28/02 ou 29 em bissexto)."""

def status_por_data(data: date, hoje: date | None = None) -> StatusEnum:
    """data < hoje → PAGO; senão PENDENTE."""

def datas_do_grupo(data_parcela_atual: date, parcela_atual: int, parcela_total: int) -> list[date]:
    """Retorna as N datas do grupo (índice 0 = parcela 1), derivadas da data da
    parcela atual via adicionar_meses (anteriores retrocedem, seguintes avançam)."""
```

Regra transversal: transações com `parcela_total > 1` recebem `categoria = PARCELAMENTOS`.
Receitas: `tipo = RECEITA` força `categoria = RECEITA`; status default PAGO se `data <= hoje`.
