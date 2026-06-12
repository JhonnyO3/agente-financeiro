# Tarefa 00 — Congelar contratos (gate de fronteira)

**Stack:** —
**Depende de:** `plan.md` com `Status: Aprovado`
**Contrato:** todos

## Objetivo
Garantir que os 7 contratos estão `Congelado` antes de qualquer implementação. Nenhuma task de implementação pode depender de fronteira em rascunho.

## Arquivos (posse exclusiva)
- `specs/melhorias-agente/contracts/intencao-schema.md`
- `specs/melhorias-agente/contracts/estado-store.md`
- `specs/melhorias-agente/contracts/resultado-tools.md`
- `specs/melhorias-agente/contracts/rag-busca.md`
- `specs/melhorias-agente/contracts/webhook-fila.md`
- `specs/melhorias-agente/contracts/prompts-injection.md`
- `specs/melhorias-agente/contracts/relogio-contexto.md`

## Escopo
1. Revisar cada contrato; confirmar `Status: Congelado`.
2. Conferir que os arquivos de posse não colidem entre tasks paralelas.

## Critérios de aceite
- [ ] Os 7 contratos marcados `Congelado`.
- [ ] Nenhuma fronteira citada por uma task está em rascunho.

## Verificação
```bash
grep -L "Status: Congelado" specs/melhorias-agente/contracts/*.md   # saída vazia
```
