---
name: revisao-codigo
description: Use antes de finalizar uma tarefa ou abrir PR, ou quando o usuário pedir "revisar", "code review", "checar qualidade". Roteiro de autorrevisão de qualidade e segurança alinhado ao CLAUDE.md, com foco em Java e Go.
---

# Revisão de código

Aplique este checklist às mudanças (use `git diff` para ver o que mudou).

## Correção

- O código cumpre os contratos congelados e a `spec.md`? Casos de borda tratados?
- Há teste cobrindo a mudança? Roda verde?

## Segurança

- Nenhum segredo hardcoded; entrada externa validada.
- Sem injeção (SQL/command); erros não vazam dados sensíveis.

## Qualidade — Go

- Erros tratados (`if err != nil`, wrap com `%w`), sem `panic` em libs.
- `context.Context` propagado; sem goroutine vazando; sem `defer` em loop quente.
- Rode `go test -race` quando houver concorrência.

## Qualidade — Java

- Sem `null` vazando em API pública (Optional); exceções tipadas, não engolidas.
- Imutabilidade onde possível; recursos fechados (try-with-resources); `equals`/`hashCode` corretos.
- Controllers finos; lógica no domínio.

## Geral

- Aderente às convenções do CLAUDE.md (nomes, tipos, estrutura de camadas).
- Sem duplicação óbvia; funções coesas; nomes claros. Sem dependência nova injustificada.

## Antes de concluir

- Rodar `/verificar`. Não declarar "pronto" com lint/teste quebrado.
- Para revisão independente e mais rigorosa, delegar ao subagente `revisor`.
