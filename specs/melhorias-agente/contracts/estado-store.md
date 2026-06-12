# Contrato: EstadoStore e EstadoConversa

**Status:** Congelado
**Fronteira:** Roteador/Tools/Worker ↔ persistência de estado conversacional
**Arquivos de posse:** `agent/domain/estado.py` (modelos), `agent/services/estado_store.py` (interface + impl)

## Modelos (`agent/domain/estado.py`)

```python
from datetime import datetime
from typing import Literal
from pydantic import BaseModel

class Mensagem(BaseModel):
    papel: Literal["usuario", "assistente"]
    texto: str
    em: datetime                      # UTC-aware

class OpcaoPendente(BaseModel):
    numero: int                       # 1-based, como exibido ao usuário
    rotulo: str                       # texto curto da opção (ex: "Roupas Zara — R$ 180,00")
    ref: dict                         # dados p/ resolver a seleção (ex: {"id": 12} ou {"escopo": "todos"})

class EstadoConversa(BaseModel):
    usuario_id: int
    acao_pendente: Literal["cadastrar", "atualizar", "excluir"] | None = None
    payload_pendente: dict | None = None    # registro(s)/diff JÁ MONTADO(S) — confirmar persiste SEM LLM
    campos_faltantes: list[str] = []        # p/ complementar ("valor","parcelas")
    opcoes: list[OpcaoPendente] | None = None
    historico: list[Mensagem] = []          # últimas N=5 (ring buffer)
    expira_em: datetime | None = None       # TTL da PENDÊNCIA = 5 min
    historico_expira_em: datetime | None = None  # TTL do HISTÓRICO = 24h
```

- `payload_pendente` é `dict` opaco para o store; seu shape é o `ResultadoTool` serializado (contrato `resultado-tools`).
- Há **uma** `EstadoConversa` por `usuario_id` (chave do store é `usuario_id`).

## Interface `EstadoStore` (`agent/services/estado_store.py`)

```python
class EstadoStore(Protocol):
    async def obter(self, usuario_id: int, agora: datetime) -> EstadoConversa: ...
        # nunca None: retorna estado novo/limpo se inexistente; expira pendência/histórico vencidos vs `agora`
    async def salvar(self, estado: EstadoConversa) -> None: ...
    async def limpar_pendencia(self, usuario_id: int) -> None: ...
        # zera acao_pendente/payload_pendente/campos_faltantes/opcoes/expira_em; PRESERVA historico
    async def registrar_mensagem(self, usuario_id: int, msg: Mensagem, agora: datetime) -> None: ...
        # adiciona ao historico (corta em N=5), renova historico_expira_em
```

- Métodos **async** (a implementação de produção é Redis).
- `agora` é injetado (vem do `Relogio`, contrato `relogio-contexto`) — nada de `datetime.now()` interno, para testabilidade.
- `obter` aplica as expirações: pendência vencida → limpa só a pendência; histórico vencido → limpa só o histórico.

## Implementação v1 — `EstadoStoreRedis` (produção) + `EstadoStoreMemoria` (testes/dev)

- **`EstadoStoreRedis`**: `redis.asyncio` (pacote `redis>=5`), chave `estado:{usuario_id}`, valor = `EstadoConversa` serializada como JSON (`model_dump_json`/`model_validate_json`). TTL físico da chave = 24h (renovado a cada `salvar`/`registrar_mensagem`); a expiração **lógica** de pendência (5 min) e histórico (24h) continua decidida em `obter` contra `agora` injetado — comportamento idêntico entre as duas implementações.
- **`EstadoStoreMemoria`**: `dict[int, EstadoConversa]` (evolução de `confirmacao_state.py`) — usada nos testes e como fallback de desenvolvimento.
- Conexão via `Settings.REDIS_URL`. Testes da implementação Redis usam cliente mockado (`AsyncMock`) — sem Redis real, conforme convenção do repo.
- **Invariante mantida:** fila e micro-debounce do worker são in-process — o agente continua rodando **1 worker uvicorn** (o estado em Redis sobrevive a restart, mas a fila não é distribuída).

## Resumo de pendência para o classificador

Função utilitária `resumir_pendencia(estado) -> str` no mesmo arquivo, produzindo o `{estado_pendente}` textual esperado por `classificador.md` (ex: `"cadastro aguardando confirmação"`, `"cadastro aguardando valor"`, `"lista de 3 opções exibida (1. Internet, 2. Zara, 3. Batman)"`, `"exclusão aguardando escopo (1. somente este, 2. todos)"`, ou `"nenhuma"`).

## Critérios de aceitação

- `EstadoStoreRedis` e `EstadoStoreMemoria` passam a MESMA suíte de testes de comportamento (Redis com cliente mockado).
- `obter` em chave inexistente devolve estado limpo (não `None`).
- Pendência expira em 5 min sem afetar histórico; histórico expira em 24h sem afetar pendência.
- `limpar_pendencia` preserva `historico`.
- `registrar_mensagem` mantém no máximo 5 mensagens.
- `resumir_pendencia` cobre os formatos de `{estado_pendente}` do `classificador.md`.
