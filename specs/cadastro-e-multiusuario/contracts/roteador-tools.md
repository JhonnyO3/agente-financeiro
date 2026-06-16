# Contrato: Roteador e Tools escopados por mensagem

**Status:** Congelado
**Fronteira:** `worker.py` ↔ `roteador.py` ↔ `tools/*` ↔ `_SessionFactoryRepository`

Define como o repositório por mensagem chega ao roteador e às tools **sem** alterar a API pública de cada `Tool.executar` (decisão no plan: reconstrução por mensagem é mais barata que re-threading o `repo` em todas as assinaturas).

## Decisão: `construir_roteador(repo)` (factory de roteador)

O `main.py` expõe uma fábrica que monta o roteador (e as tools que dependem de repo) já amarrado ao `repo` da mensagem:

```python
def _criar_construir_roteador(
    *, relogio, embedder, estado_store
) -> Callable[[_SessionFactoryRepository], Roteador]:
    def construir(repo) -> Roteador:
        rag = BuscaRAG(embedder=embedder, adapter=repo)
        tool_cadastrar = ToolCadastrar(relogio=relogio, repository=repo)
        tool_listar    = ToolListar(repo=repo, relogio=relogio, usuario_id=None)  # usuario_id flui via rotear
        tool_atualizar = ToolAtualizar(rag=rag, repository=repo, relogio=relogio)
        tool_excluir   = ToolExcluir(rag=rag, repository=repo, relogio=relogio)
        tool_conversar = ToolConversar()
        return Roteador(
            tool_cadastrar=tool_cadastrar,
            tool_listar=tool_listar,
            tool_atualizar=tool_atualizar,
            tool_excluir=tool_excluir,
            tool_conversar=tool_conversar,
            estado_store=estado_store,
            repository=repo,
        )
    return construir
```

- O `Worker` recebe esse `construir` e chama `construir(repo)` por mensagem (ver `worker-pipeline.md`).
- **API pública das tools NÃO muda** — elas continuam recebendo `repository`/`repo` no construtor. A diferença é que o construtor passa a rodar por mensagem, com o repo certo.
- **`Roteador.rotear` NÃO muda de assinatura:** continua `rotear(intencao, usuario_id, agora, contexto)` e usa `self._repo` (já o repo escopado).

## Por que não "repo como parâmetro de executar" (Opção A da spec)

A Opção A exigiria mudar a assinatura de **todas** as tools (`executar(..., repo)`) + o roteador + o main no mesmo PR — alta colisão e quebra de testes existentes das tools. A reconstrução por mensagem:

- Mantém as assinaturas atuais das tools (testes existentes seguem válidos).
- Concentra a mudança de wiring em `main.py` (uma task) + `worker.py` (outra task).
- Custo: instanciar objetos leves (tools são stateless além do repo/relogio) por mensagem — desprezível.

## Invariante de isolamento

- `construir(repo)` recebe **sempre** o `repo` da mensagem (escopado por `usuario_id`).
- Nenhuma tool ou o roteador retém repo entre mensagens (instâncias novas por mensagem).
- `usuario_id` continua sendo passado explicitamente a `rotear`, `tool_atualizar.executar`, `tool_excluir.executar` e ao `_repo.criar_lote(..., usuario_id=...)` etc. — dupla barreira (repo escopado **e** filtro explícito).

## Arquivos

- A factory `construir_roteador` vive em `main.py` (wiring) — **não** é uma mudança em `roteador.py` nem nas tools.
- `roteador.py` e `tools/*` permanecem **inalterados** por este contrato (zero edição). Isso libera paralelismo: nenhuma task precisa tocá-los.
