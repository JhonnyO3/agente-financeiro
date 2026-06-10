# Tarefa 09 — JavaScript Cards e Parcelas

**Stack:** python (projeto) / js (arquivo)
**Dependências:** 06
**Contratos:** `contracts/api-json.md`, `contracts/js-interop.md`

---

## Objetivo

Implementar os cards de resumo (RF-02) e a seção de parcelas em andamento (RF-06).

---

## Arquivos que esta tarefa possui

- `dashboard/static/app.js`

---

## O que implementar

Arquivo único, IIFE autocontido (ver `contracts/js-interop.md`): lê `PERIODO` da
URL, define `fmtBRL` localmente.

### Cards de resumo (RF-02)

1. `fetch('/api/resumo?periodo=' + PERIODO)`
2. Preencher `#card-gastos`, `#card-investimentos`, `#card-saldo` com `fmtBRL`
3. Saldo: classe `text-success` se `>= 0`, `text-danger` se `< 0`
   (comparar pelo sinal da string — `saldo.startsWith("-")` — sem aritmética JS)

### Parcelas em andamento (RF-06)

1. `fetch('/api/parcelas-ativas')`
2. Para cada grupo, renderizar card horizontal em `#parcelas-container`:
   ```
   [descricao]  Parcela X/N  Próximo: dd/mm/yyyy  R$ valor/parcela
   [progress bar Bootstrap: width = pagas/parcela_total * 100%]
   ```
3. Botão "Excluir grupo" em cada card:
   - confirmação (`confirm()` ou inline) antes de deletar
   - `DELETE /api/grupos/<grupo_parcela_id>`
   - sucesso → remover o card do DOM (ou re-fetch da lista)
4. Lista vazia → mensagem "Nenhuma parcela em andamento"

### Seletor de período (RF-01)

Nenhum JS necessário — o `<select>` em `index.html` submete o form via
`onchange` (implementado em T06). Não duplicar comportamento aqui.

---

## Critérios de aceite

- [ ] Cards mostram valores formatados em BRL ao carregar a página
- [ ] Cor do saldo muda conforme o sinal (verde/vermelho)
- [ ] Cards de parcela mostram progresso correto (`pagas` de `parcela_total`)
- [ ] Excluir grupo pede confirmação e remove todos os registros do grupo
- [ ] Container vazio mostra mensagem amigável
- [ ] Nenhuma global criada (não há globais permitidas para este arquivo)

---

## Comando de verificação

```bash
uv run flask --app dashboard.app run --port 5000 &
# Abrir http://localhost:5000 com dados no banco:
# - 3 cards preenchidos, saldo colorido conforme sinal
# - cards de parcelas com barra de progresso
# - excluir grupo → confirma → cards somem e registros saem do banco
```
