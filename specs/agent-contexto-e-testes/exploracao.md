# Exploração — agent-contexto-e-testes

## Estrutura relevante

### Fluxo atual de uma mensagem
```
webhook.py → Worker.receber() → Worker.processar_pendentes()
  → estado_store.obter()
  → Classificador.classificar(mensagem, historico, estado_pendente)
      └── montar_prompt("classificador", ctx) → LLM → Intencao
  → Roteador.rotear(intencao, usuario_id, agora, {"mensagem": texto})
      └── _executar_operacional → tool_cadastrar.executar(itens, contexto)
  → Formatador.formatar(resultado)
  → evolution_client.enviar_mensagem()
```

### Problema central (confirmado na exploração)
`agent/services/prompts.py` tem `ARQUIVO_POR_ACAO["cadastrar"] = "02-extracao-cadastrar.md"` e a função `montar_prompt("cadastrar", ctx)` existe e funciona — **mas nenhum código chama `montar_prompt("cadastrar", ...)`**. O único caller de `montar_prompt` é `Classificador.classificar` que chama `montar_prompt("classificador", ctx)`.

### Arquivos-chave

| Arquivo | Papel |
|---|---|
| `agent/services/prompts.py` | `montar_prompt(acao, ctx)` — constrói prompt base + injection |
| `agent/prompts/00-base.md` | Base com `{historico_recente}`, `{estado_pendente}`, `{injection_acao}` |
| `agent/prompts/01-classificador.md` | Injection do classificador — extraia intenção + params parciais |
| `agent/prompts/02-extracao-cadastrar.md` | Injection de extração — **NUNCA CHAMADO** atualmente |
| `agent/services/classificador.py` | Único caller LLM de classificação — usa `montar_prompt("classificador")` |
| `agent/services/roteador.py` | Mapeia `Intencao → Tool`. Ponto de inserção do `Extrator`. |
| `agent/tools/cadastrar.py` | `ToolCadastrar.executar(itens, contexto)` — valida campos, monta registros |
| `agent/domain/intencao.py` | `ItemCadastro` — campos: descricao, valor, forma_pagamento, parcela_atual, total_parcelas, dia_vencimento, data, tipo |
| `agent/entrypoint/worker.py` | Passa `historico` para classificador — contexto disponível |
| `agent/agents_llm.py` | `criar_llm()`, `criar_llm_formatacao()`, `Embedder` — fábrica de LLM |
| `scripts/` | Scripts existentes: backfill, criar_usuario, sanitizacao, seed_recuperacao |

### Contrato do `montar_prompt`

```python
montar_prompt("cadastrar", {
    "mensagem": str,
    "historico_recente": str,       # "usuario: ...\nassistente: ..."
    "estado_pendente": str,
    "user_name": str,
    "data_atual": str,              # DD/MM/YYYY
    "responsavel_padrao": str,      # injetado automaticamente
    "parametros": str,              # itens parciais do classificador (novo)
})
```

`00-base.md` usa: `{historico_recente}`, `{estado_pendente}`, `{responsavel_padrao}`, `{user_name}`, `{data_atual}`, `{injection_acao}`.

`02-extracao-cadastrar.md` usa: `{parametros}`, `{responsavel_padrao}`, `{data_atual}`.

### Saída do LLM de extração

O `Classificador` usa `llm.with_structured_output(Intencao)`. O `Extrator` pode usar `with_structured_output(ParamsCadastrar)` para retornar `list[ItemCadastro]` completos.

### `ToolCadastrar` — campos faltantes atuais

Só verifica `valor is None`. Adicionar cheque de `forma_pagamento is None` quando não há pista inferível (sem parcelas).

### Wiring em `main.py`

`Roteador` é construído via `construir_roteador(repo)` em `worker.py`. O `Extrator` pode ser injetado como dependência do `Roteador` ou instanciado dentro do método `_executar_operacional`.

### Testes existentes relevantes

- `tests/test_tool_cadastrar.py` — testes de `ToolCadastrar`
- `tests/test_roteador.py` — testes do `Roteador`
- `tests/test_classificador.py` — testes do `Classificador`
- `tests/test_prompts.py` — testa `montar_prompt`
- `tests/test_worker.py` — testa fluxo end-to-end mockado

### Riscos

1. `montar_prompt("cadastrar", ctx)` exige `{parametros}` no ctx — novo campo.
2. Segunda chamada LLM aumenta latência em ~1-2s por mensagem de cadastro.
3. `with_structured_output(ParamsCadastrar)` retorna objeto com `itens: list[ItemCadastro]` — precisa extrair `.itens`.
4. O harness precisa de DB real ou mockado — usar `EstadoStoreMemoria` e repo mockado para simplificar.
5. Modo `--seed` exige intercepção do LLM antes de chamar a API — monkey-patch de `ChatOpenAI` ou override de `criar_llm`.
