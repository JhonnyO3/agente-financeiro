---
name: orquestrar-squad
description: Use após o planejamento (plan.md + contracts/ + tasks/ + STATUS.md), ou quando o usuário pedir "executar", "rodar a squad", "implementar as tarefas". Orquestra a execução das tarefas pela squad de subagents, em paralelo via worktrees quando isoladas, e integra os resultados.
---

# Orquestrar a squad (execução)

Terceiro passo do fluxo. Você (sessão principal) é o **orquestrador**: despacha tarefas a subagents
isolados e integra os resultados. Os subagents não conversam entre si — toda coordenação passa por
você e pelos arquivos em `specs/<feature>/`. Ver `docs/squad-playbook.md`.

## Pré-condições

- **`plan.md` com `Status: Aprovado`** (gate humano). Se estiver `Rascunho`, PARE — peça a aprovação
  humana antes de despachar qualquer tarefa.
- `plan.md` com DAG, `STATUS.md` e `scenarios/*.feature` (Gherkin do QA) existem.
- Todos os contratos usados por tarefas prontas estão **Congelados**. Se algum estiver em rascunho,
  PARE e volte a `/planejar`.

## Ciclo de execução

Repita até todas as tarefas estarem `done`:

1. **Leia** `plan.md` (DAG) e `STATUS.md`. Releia — não confie em memória de turnos anteriores.
2. **Selecione tarefas prontas:** todas as dependências em `done` e contrato congelado.
3. **Classifique o lote:**
   - **Paralelizável:** tarefas prontas que NÃO compartilham arquivos.
   - **Sequencial:** tarefas que compartilham arquivos ou têm dependência pendente.
4. **Despache (paralelo):** para cada tarefa paralelizável,
   - crie um worktree isolado: `git worktree add ../<proj>-taskNN -b task/NN`;
   - dispare **uma instância nova** do agente certo pela stack (`impl-java`, `impl-go` ou `impl-python`) **por tarefa**,
     junto do `testador` — TDD: o `testador` converte os `scenarios/*.feature` em testes que falham
     primeiro, e o `impl-*` os faz passar. Emita as chamadas Agent **na mesma mensagem** para rodarem juntas;
   - marque a tarefa como `doing` no `STATUS.md` (anote worktree/branch).
5. **Despache (sequencial):** uma tarefa por vez, mesmo procedimento sem worktrees paralelos.
6. **Integre o lote:** quando os agentes do lote retornarem, dispare o subagent `integrador` para
   mesclar os branches na ordem do `plan.md`, resolver conflitos e rodar `/verificar`.
7. **Atualize o STATUS.md:** tarefas integradas e verdes → `done`; problemas → `blocked` com nota.
   Remova worktrees já integrados (`git worktree remove ...`).

## Regras

- **Nunca** despache uma tarefa cujo contrato não está congelado.
- Tarefas paralelas nunca compartilham arquivos (garantido pela decomposição; reconfirme).
- `done` exige `/verificar` verde após integração.
- Se um agente relatar contradição no contrato, PARE o lote e reabra o plano — não improvise.
- Mudanças destrutivas (remover worktree com trabalho não mesclado) exigem confirmação.

## Ao final

Todas as tarefas `done` → siga para `/revisar` (subagent `revisor`) e depois `/commit`.
