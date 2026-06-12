# Contrato: Sistema de Prompts (base + injection)

**Status:** Congelado
**Fronteira:** Montagem de prompt ↔ chamadas LLM (classificador, extração cadastrar/atualizar, conversar)
**Arquivos de posse:** `agent/prompts/*.md`, `agent/services/prompts.py`

## Prompts existentes (apenas para chamadas LLM REAIS)

Só há prompt onde há chamada LLM (spec §3.9 ajuste 1): classificador, extrações especializadas e conversar. **Listar/Excluir não têm injection** (parâmetros saem do classificador; sem LLM próprio).

```
agent/prompts/
├── 00-base.md               # identidade + contexto (TODAS as chamadas)
├── 01-classificador.md      # 10 intenções + estado_pendente + histórico (de classificador.md)
├── 02-extracao-cadastrar.md # extração rica + categorização (absorve categorizador)
├── 03-extracao-atualizar.md # campos a alterar
└── 06-conversar.md          # diálogo financeiro PURO (sem banco)
```

## `00-base.md` — variáveis obrigatórias

Conteúdo conforme `prompt-base.md`. Placeholders:
`{user_name}`, `{data_atual}`, `{responsavel_padrao}`, `{historico_recente}`, `{estado_pendente}`, `{injection_acao}`.

- `{responsavel_padrao}` vem de `Settings.RESPONSAVEL_PADRAO` — **nunca hardcoded**.
- `{estado_pendente}` é o resumo de `resumir_pendencia` (contrato `estado-store`).
- Categorias/formas/status do base = enum rico atual (+ `DINHEIRO` na linguagem; mapeado p/ PIX pela Tool — ver plan D3).

## Montagem (`agent/services/prompts.py`)

```python
ARQUIVO_POR_ACAO = {
    "classificador": "01-classificador.md",
    "cadastrar":     "02-extracao-cadastrar.md",
    "atualizar":     "03-extracao-atualizar.md",
    "conversar":     "06-conversar.md",
}

def montar_prompt(acao: str, contexto: dict) -> str:
    base = carregar("00-base.md")
    injection = carregar(ARQUIVO_POR_ACAO[acao]).format(**contexto)
    return base.format(injection_acao=injection, **contexto)
```

- Cada chamada recebe **apenas** sua injection (sem contaminação entre ações).
- `carregar` é o `carregar_prompt` reusado de `agents_llm.py`.

## Contexto por chamada

| Chamada | Variáveis adicionais além das do base |
|---|---|
| classificador | (só as do base) |
| cadastrar (extração) | `{parametros}` (JSON dos itens do classificador) |
| atualizar (extração) | `{parametros}`, `{candidatos}` (do RAG) |
| conversar | `{mensagem}` (mensagem original do usuário) |

> `conversar` **não** recebe `{contexto_rag}` nem acessa o banco (decisão da spec: diálogo puro).

## Critérios de aceitação

- `montar_prompt("classificador", ctx)` injeta `01-classificador.md` no placeholder e preenche todas as variáveis sem `KeyError`.
- `{responsavel_padrao}` resolve de `Settings`, nunca string fixa.
- Faltar variável obrigatória no contexto falha explicitamente (não silenciosamente).
