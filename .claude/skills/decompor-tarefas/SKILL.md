---
name: decompor-tarefas
description: Use após a spec estar aprovada, ou quando o usuário pedir "planejar", "decompor", "quebrar em tarefas". Transforma specs/<feature>/spec.md em plano técnico, contratos congelados e tarefas isoladas com DAG, prontos para a squad executar.
---

# Decomposição em tarefas (planejamento técnico)

Segundo passo do fluxo da squad: `spec.md` → plano + contratos + tarefas. O objetivo é produzir
unidades de trabalho **isoladas e delegáveis**, com fronteiras estáveis, para que subagents
trabalhem em paralelo sem conversar entre si.

## Passos

1. **Explorar** (`explorador`): mapeie a codebase a partir de `negocio.md`/`spec.md` →
   grave `specs/<feature>/exploracao.md` (estrutura, convenções reais, reuso, integrações, riscos).
2. **Arquitetar** (`arquiteto`): com a exploração + a spec, projete e **grave os artefatos** em `specs/<feature>/`:
   - `plan.md` (de `_template-plan.md`): arquitetura, decisões, tabela de tarefas com DAG, riscos,
     ordem de integração, verificação da feature. **Status inicial: `Rascunho`.**
   - `contracts/<nome>.md` (de `_template-contract.md`): um por fronteira. Marque como **Congelado** quando estável.
   - `tasks/NN-*.md` (de `_template-task.md`): uma por unidade de trabalho.
   - `STATUS.md`: task board com todas as tarefas em `todo`.
3. **QA** (`qa`): transforme critérios de aceite em cenários **Gherkin** →
   `specs/<feature>/scenarios/NN-*.feature` (um conjunto por tarefa).
4. **🚦 Gate humano:** apresente o `plan.md` ao humano para leitura, dúvidas e ajustes.
   **NÃO prossiga para `/squad`.** A implementação só começa quando o humano mudar o
   `Status` do `plan.md` para `Aprovado`.

## Regras de uma boa decomposição

- **Congele os contratos primeiro.** Nenhuma tarefa de implementação deve depender de uma fronteira
  ainda em rascunho.
- **Anti-colisão:** cada tarefa declara os arquivos que possui; tarefas que rodariam em paralelo NÃO
  compartilham arquivos. Se compartilham, vire dependência no DAG (sequencial).
- **Auto-contida:** a tarefa deve trazer tudo que o agente precisa (objetivo, contrato-ref, arquivos,
  critérios de aceite → testes, comando de verificação local).
- **Tamanho:** prefira tarefas pequenas e verificáveis isoladamente.
- **Stack explícita:** marque `java`, `go` ou `python` para o orquestrador escolher `impl-java`/`impl-go`/`impl-python`.

## STATUS.md inicial (formato)

```markdown
# STATUS — <feature>

| ID | Tarefa | Stack | Estado | Worktree/Branch | Nota |
|----|--------|-------|--------|-----------------|------|
| 01 | ...    | go    | todo   | —               |      |
| 02 | ...    | java  | todo   | —               |      |
```

Próximo passo (somente após aprovação humana do `plan.md`): `/squad <feature>`.
