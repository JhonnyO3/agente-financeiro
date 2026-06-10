# Contrato: Embedding

**Status: Congelado**

## Modelo

`text-embedding-3-small` — OpenAI — 1536 dimensões

## Texto que é embedado (criação de transação)

O texto para embedding é um composto dos campos mais relevantes para busca semântica:

```python
def texto_para_embedding(tipo: str, categoria: str, descricao: str | None, data: date) -> str:
    partes = [tipo, categoria]
    if descricao:
        partes.append(descricao)
    partes.append(data.strftime("%d/%m/%Y"))
    return " ".join(partes)

# Exemplos:
# "GASTO ALIMENTACAO mercado 12/06/2026"
# "GASTO TRANSPORTE uber 11/06/2026"
# "INVESTIMENTO INVESTIMENTO PETR4 09/06/2026"
```

Isso garante que buscas como "mercado de ontem" ou "gasto de transporte de sexta" encontrem o registro correto.

## Texto que é embedado (busca — alterar/excluir/consulta de grupo)

A mensagem original do usuário é embedada diretamente:

```python
embedding_busca = await embedder.gerar("muda o gasto do mercado de ontem")
```

O pgvector encontra o registro cuja representação vetorial é mais próxima dessa query.

## Interface — `app/agents/embedder.py`

```python
class Embedder:
    def __init__(self):
        self._client = OpenAIEmbeddings(model="text-embedding-3-small")

    async def gerar(self, texto: str) -> list[float]:
        return await self._client.aembed_query(texto)

    async def gerar_para_transacao(
        self, tipo: str, categoria: str, descricao: str | None, data: date
    ) -> list[float]:
        texto = texto_para_embedding(tipo, categoria, descricao, data)
        return await self.gerar(texto)
```

## Regras

| Regra | Detalhe |
|-------|---------|
| **1 chamada por grupo** | Parcelas do mesmo grupo compartilham o mesmo embedding (mesmo texto) |
| **Embedding imutável** | Não regenerar embedding ao alterar uma transação — a busca semântica usa a descrição original |
| **Nunca embedar valor** | Valor monetário não entra no texto de embedding — causa ruído semântico |
| **Quem chama** | Sempre o `service` — nunca o `repository` diretamente |
| **Dimensão fixa** | 1536d fixada no migration; nunca mudar sem dropar e recriar o index |

## Fluxo de criação

```
CadastrarService
    │
    ├── extrai dados (LLM)
    ├── categoriza (LLM)
    ├── Python calcula parcelas e datas
    │
    ├── embedder.gerar_para_transacao(tipo, categoria, descricao, data_1a_parcela)
    │   → 1 chamada à API OpenAI
    │   → mesmo vetor para todas as N parcelas do grupo
    │
    └── repository.criar_lote([...]) → salva N registros com o mesmo embedding
```

## Fluxo de busca (alterar/excluir)

```
AlterarService / ExcluirService
    │
    ├── embedder.gerar(mensagem_usuario)
    │   → 1 chamada à API OpenAI
    │
    └── repository.buscar_semantico(embedding, limite=1)
        → SELECT ... ORDER BY embedding <-> $1 LIMIT 1
```
