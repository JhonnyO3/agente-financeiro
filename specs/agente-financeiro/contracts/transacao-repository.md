# Contrato: TransacaoRepository

**Status: Congelado**

## Interface

```python
class TransacaoRepository:
    async def criar(self, transacao: TransacaoCreate) -> Transacao: ...
    async def criar_lote(self, transacoes: list[TransacaoCreate]) -> list[Transacao]: ...
    async def buscar_por_id(self, id: int) -> Transacao | None: ...
    async def buscar_por_grupo(self, grupo_parcela_id: UUID) -> list[Transacao]: ...
    async def buscar_semantico(self, embedding: list[float], limite: int = 5) -> list[Transacao]: ...
    async def buscar_semantico_com_distancia(self, embedding: list[float], limite: int = 1) -> tuple[Transacao, float] | None: ...
    async def atualizar(self, id: int, dados: TransacaoUpdate) -> Transacao: ...
    async def excluir(self, id: int) -> None: ...
    async def excluir_grupo(self, grupo_parcela_id: UUID) -> int: ...  # retorna qtd excluída
    async def listar_por_periodo(self, inicio: date, fim: date) -> list[Transacao]: ...
    async def agregar_por_categoria(self, inicio: date, fim: date) -> list[AgregadoCategoria]: ...
```

## DTOs

```python
@dataclass
class TransacaoCreate:
    tipo: TipoEnum           # GASTO | INVESTIMENTO
    valor: Decimal
    descricao: str | None
    categoria: CategoriaEnum
    data: date
    parcela_numero: int      # começa em 1
    parcela_total: int       # 1 = à vista
    grupo_parcela_id: UUID
    embedding: list[float]   # 1536 dimensões

@dataclass
class TransacaoUpdate:
    tipo: TipoEnum | None = None
    valor: Decimal | None = None
    descricao: str | None = None
    categoria: CategoriaEnum | None = None
    data: date | None = None

@dataclass
class AgregadoCategoria:
    categoria: CategoriaEnum
    total: Decimal
    quantidade: int
```

## Enums

```python
class TipoEnum(str, Enum):
    GASTO = "GASTO"
    INVESTIMENTO = "INVESTIMENTO"

class CategoriaEnum(str, Enum):
    ALIMENTACAO = "ALIMENTACAO"
    TRANSPORTE = "TRANSPORTE"
    LAZER = "LAZER"
    INVESTIMENTO = "INVESTIMENTO"
    GASTOS_FIXOS = "GASTOS_FIXOS"
    COMPRAS = "COMPRAS"
```

## Regras

- `buscar_semantico` usa `<->` (L2 distance) do pgvector; retorna os N mais próximos
- `buscar_semantico_com_distancia` retorna `(Transacao, float)` com a distância L2; retorna `None` se banco vazio
- **Threshold de similaridade**: distância L2 > 1.0 é considerada "não encontrado" — decisão feita no service, não no repository
- `excluir` é hard delete (sem soft delete)
- `criar_lote` cria todos numa única transação de banco
- `agregar_por_categoria` retorna registros de **todos** os tipos — o service filtra por `tipo` para separar gastos de investimentos
