---
name: requisitos-spec
description: Use ao iniciar qualquer nova feature ou mudança significativa de comportamento, ou quando o usuário pedir "spec", "requisitos", "planejar feature". Conduz desenvolvimento orientado a requisitos — transforma um pedido vago em uma especificação clara e testável ANTES de codar.
---

# Desenvolvimento orientado a requisitos (spec-driven)

Antes de escrever código de produção, produza/atualize `specs/<feature>/spec.md`.
É o primeiro passo do fluxo da squad (depois vêm `/planejar` → `/squad`).

## Passos

1. Escolha um nome curto em kebab-case para a feature e crie a pasta `specs/<feature>/`.
2. Faça as perguntas necessárias para remover ambiguidade (entradas, saídas, casos de erro, fora de escopo).
3. Escreva `spec.md` usando o template `specs/_template-spec.md`.
4. Liste critérios de aceitação como checklist verificável.
5. Só depois da spec aprovada, prossiga para `/planejar` (subagent `arquiteto` → plano + contratos + tarefas).

## Critérios de uma boa spec

- Cada requisito é observável e testável (evite "deve ser rápido"; prefira "p95 < 200ms").
- Define explicitamente o que está FORA de escopo.
- Inclui contratos de API (request/response) e mudanças de dados quando houver — o detalhe completo
  desses contratos será congelado em `contracts/` na fase de planejamento.
- Tem uma seção "Como verificar" mapeando requisito → teste.

Mantenha a spec versionada no git. Ela é a fonte da verdade da feature.
