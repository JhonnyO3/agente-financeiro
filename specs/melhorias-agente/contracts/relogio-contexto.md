# Contrato: Relógio e Contexto Temporal

**Status:** Congelado
**Fronteira:** Tools/Classificador/EstadoStore ↔ tempo (TZ do usuário)
**Arquivos de posse:** `agent/services/relogio.py`; novas Settings em `agent/config.py` (T03)

## Relógio injetável

```python
from datetime import date, datetime
from zoneinfo import ZoneInfo

class Relogio:
    def __init__(self, tz: str = "America/Sao_Paulo"): ...
    def agora(self) -> datetime: ...   # aware, no fuso do usuário
    def hoje(self) -> date: ...        # date no fuso do usuário (corrige "ontem/hoje" à noite em UTC)
```

- Substitui `date.today()` espalhado (cadastrar/listar/atualizar/excluir/estado).
- Injetado nas Tools e no `EstadoStore.obter`/`registrar_mensagem` (parâmetro `agora`).
- TZ via `Settings.TIMEZONE_USUARIO` (default `"America/Sao_Paulo"`).

## Coerção de datas brutas

- O classificador entrega datas como **texto bruto** (`"ontem"`, `"10 de julho"`, `"mês passado"`).
- A coerção para `date` é da Tool, usando `Relogio.hoje()` como referência + o `coagir_data` reusado de `agents_llm.py`.

## Novas Settings (em `agent/config.py`, posse T03)

```python
RESPONSAVEL_PADRAO: str               # obrigatório (sem default pessoal)
TIMEZONE_USUARIO: str = "America/Sao_Paulo"
WEBHOOK_APIKEY: str                   # obrigatório
DEBOUNCE_SEGUNDOS: int = 5
CONFIANCA_MINIMA: float = 0.7
RAG_PISO: float = 1.0
RAG_MARGEM: float = 0.15
RAG_MAX_OPCOES: int = 5
LLM_MODELO_CLASSIFICACAO: str = "gpt-4o-mini"
LLM_MODELO_CONVERSAR: str = "gpt-4o"
# AGENTE_USUARIO_EMAIL perde o default hardcoded → obrigatório
```

- Documentar no `config.py`/README a **invariante de 1 worker uvicorn** (estado/dedup/fila in-memory).

## Critérios de aceitação

- `Relogio("America/Sao_Paulo").hoje()` difere de `datetime.utcnow().date()` quando o relógio UTC já virou o dia e o BRT não (teste com relógio fixo).
- Nenhuma Tool usa `date.today()`/`datetime.now()` direto (usa `Relogio`).
- `RESPONSAVEL_PADRAO`, `WEBHOOK_APIKEY`, `AGENTE_USUARIO_EMAIL` sem default — app falha explicitamente se faltarem.
