# Tarefa 08 — JavaScript Tabela e CRUD

**Stack:** python (projeto) / js (arquivo)
**Dependências:** 06
**Contratos:** `contracts/api-json.md`, `contracts/js-interop.md`

---

## Objetivo

Implementar a tabela paginada de transações com filtros e CRUD via modais (RF-07)
e a seção de investimentos com tabela e cards de totais (RF-08).

---

## Arquivos que esta tarefa possui

- `dashboard/static/table.js`

---

## O que implementar

Arquivo único, IIFE autocontido (ver `contracts/js-interop.md`). Estado interno:
`{ pagina: 1, tipo: "", categoria: "" }`.

### Tabela de transações — `#tabela-transacoes` (RF-07)

1. `carregarTabela()`: `fetch('/api/transacoes?periodo=' + PERIODO + ...)` com
   `tipo`, `categoria` e `pagina` do estado; re-renderiza `<tbody>` e `#paginacao`
2. Colunas: Data (dd/mm/yyyy), Descrição, Categoria, Valor (fmtBRL),
   Parcela (`X/N`), Tipo, Ações (✏️ 🗑️)
3. Paginação: botões anterior/próxima + indicador `pagina/paginas`;
   desabilitar nos extremos
4. Filtros `#filtro-tipo` e `#filtro-categoria`: `onchange` → atualiza estado,
   volta à página 1, `carregarTabela()`
5. Expor a global do contrato:
   ```js
   window.filtrarPorCategoria = (categoria) => {
     // seta #filtro-categoria, estado.categoria, pagina = 1, carregarTabela()
   };
   ```

### Modais CRUD (RF-07)

- **Editar (✏️)**: abre `#modal-editar` pré-preenchido com os dados da linha;
  salvar → `PUT /api/transacoes/<id>` com apenas os campos do formulário;
  sucesso → fecha modal + `carregarTabela()` + recarregar tabela de investimentos
- **Adicionar**: botão `+ Adicionar` abre `#modal-adicionar` vazio;
  salvar → `POST /api/transacoes`; validação client-side dos obrigatórios
  (data, valor, tipo, categoria); 400 da API exibe mensagem no modal
- **Excluir (🗑️)**: confirmação inline (trocar ícone por "Confirmar?/Cancelar"
  ou `confirm()`); confirmar → `DELETE /api/transacoes/<id>` + `carregarTabela()`
- Valores enviados como **string decimal** (`"95.00"`), nunca float

### Seção de investimentos (RF-08)

1. `#tabela-investimentos`: mesma renderização, fetch fixo com
   `tipo=INVESTIMENTO` (paginação própria, independente da tabela geral)
2. `#card-invest-periodo`: campo `investimentos` de
   `GET /api/resumo?periodo=` + PERIODO
3. `#card-invest-total`: campo `investimentos` de `GET /api/resumo?periodo=tudo`
4. Edição/remoção reutilizam os mesmos modais e atualizam ambas as tabelas

---

## Critérios de aceite

- [ ] Tabela carrega no load da página com o período da URL
- [ ] Filtros tipo + categoria combinados funcionam e resetam para página 1
- [ ] `window.filtrarPorCategoria` definida conforme contrato
- [ ] Modal de edição pré-preenche todos os campos
- [ ] POST/PUT/DELETE re-renderizam as tabelas sem recarregar a página
- [ ] Tabela de investimentos só mostra `tipo=INVESTIMENTO`
- [ ] Cards de investimento mostram total do período e total histórico
- [ ] Nenhuma aritmética monetária em JS (valores trafegam como string)

---

## Comando de verificação

```bash
uv run flask --app dashboard.app run --port 5000 &
# Abrir http://localhost:5000:
# - editar uma transação → valor muda na tabela sem reload
# - adicionar manual → aparece na tabela e no banco
# - excluir → some da tabela e do banco
# - filtrar por categoria → tabela atualiza
```
