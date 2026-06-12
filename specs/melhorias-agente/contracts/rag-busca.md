# Contrato: Busca RAG (3 faixas)

**Status:** Congelado
**Fronteira:** Tools Atualizar/Excluir ↔ RAG ↔ repository
**Arquivos de posse:** `agent/services/rag.py`; método aditivo em `backend/repositories/transacao_repository.py` + passthrough no adapter (T04)

## Método novo no repository (aditivo — não quebra contrato existente)

```python
async def buscar_semantico_multiplos_com_distancia(
    self, embedding: list[float], limite: int = 5, usuario_id: int | None = None,
) -> list[tuple[Transacao, float]]:
    ...  # ordenado por distância L2 crescente; respeita `limite`; filtra por usuario_id quando != None
```

- O método existente `buscar_semantico_com_distancia` (que faz `.first()`) **permanece intacto**.
- O adapter `_SessionFactoryRepository` ganha o passthrough com `usuario_id` fixo da instância.

## Texto de busca (correção de bug)

- Embeda **apenas a referência extraída** pelo classificador (`ParamsAtualizar.referencia` / `ParamsExcluir.referencia`) — ex: `"zara"`, `"flores"`. **Nunca** a mensagem crua com verbos de comando.
- O embedder é o `Embedder` atual (`text-embedding-3-small`, 1536d).

## Interface `BuscaRAG` (`agent/services/rag.py`)

```python
from enum import Enum

class Faixa(str, Enum):
    MATCH = "match"          # 1 candidato claramente acima → prosseguir direto
    AMBIGUO = "ambiguo"      # 2+ candidatos próximos → listar opções numeradas
    PISO = "piso"            # abaixo do piso → "não encontrei, pode detalhar?"

class ResultadoBusca(BaseModel):
    faixa: Faixa
    candidatos: list[tuple[Transacao, float]]   # ordenados por distância crescente

class BuscaRAG:
    async def buscar(self, referencia: str, usuario_id: int) -> ResultadoBusca: ...
```

## Regras das 3 faixas (limiares de `Settings`, calibráveis)

Dado `cands` ordenados por distância `d` crescente (menor = mais similar):

- `cands` vazio **ou** `cands[0].d > Settings.RAG_PISO` → **PISO**.
- 1 candidato dentro do piso, **ou** `cands[0].d` claramente menor que `cands[1].d` (gap ≥ `Settings.RAG_MARGEM`) → **MATCH** (devolve 1).
- 2+ candidatos dentro do piso e próximos entre si (gap < `Settings.RAG_MARGEM`) → **AMBIGUO** (devolve os próximos, até `Settings.RAG_MAX_OPCOES`).

> Limiares iniciais sugeridos (calibrar com dados): `RAG_PISO=1.0` (mantém o corte atual), `RAG_MARGEM=0.15`, `RAG_MAX_OPCOES=5`. Valores **só** em `Settings`, nunca hardcoded.

## Consumo pelas Tools

- **MATCH** → Tool segue para diff (atualizar) / confirmação (excluir).
- **AMBIGUO** → Tool devolve `aguardando_selecao` com `OpcaoPendente` a partir de `candidatos` (contrato `resultado-tools`).
- **PISO** → Tool devolve `nao_encontrado`.

## Critérios de aceitação

- `buscar_semantico_multiplos_com_distancia` respeita `limite` e ordena por distância (corrige o `.first()`).
- A referência embedada é a extraída, não a mensagem crua (teste compara o texto enviado ao embedder).
- As 3 faixas são decididas no `BuscaRAG` (serviço), não no repository; limiares vêm de `Settings`.
