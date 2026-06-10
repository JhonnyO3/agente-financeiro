# Tarefa 06 — Templates HTML

**Stack:** python
**Dependências:** 01
**Contratos:** `contracts/api-json.md`

---

## Objetivo

Criar o layout HTML completo do dashboard: base com CDNs e navbar, e `index.html` com todos os placeholders dos widgets. O JavaScript é implementado nas tarefas T07, T08, T09.

---

## Arquivos que esta tarefa possui

- `dashboard/templates/base.html`
- `dashboard/templates/index.html`

---

## O que implementar

### `dashboard/templates/base.html`

```html
<!DOCTYPE html>
<html lang="pt-BR">
<head>
  <meta charset="UTF-8">
  <title>Dashboard Financeiro</title>
  <!-- Bootstrap 5 CSS -->
  <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css" rel="stylesheet">
</head>
<body class="bg-light">
  <!-- Navbar -->
  <nav class="navbar navbar-dark bg-dark">
    <div class="container-fluid">
      <span class="navbar-brand">💰 Dashboard Financeiro</span>
    </div>
  </nav>
  <div class="container-fluid py-4">
    {% block content %}{% endblock %}
  </div>
  <!-- Bootstrap JS -->
  <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/js/bootstrap.bundle.min.js"></script>
  <!-- Chart.js -->
  <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.3/dist/chart.umd.min.js"></script>
  <!-- App scripts -->
  <script src="{{ url_for('static', filename='charts.js') }}"></script>
  <script src="{{ url_for('static', filename='table.js') }}"></script>
  <script src="{{ url_for('static', filename='app.js') }}"></script>
</body>
</html>
```

### `dashboard/templates/index.html`

Layout da página principal com as seguintes seções em ordem:

1. **Seletor de período** (RF-01):
   - `<form method="GET">` com `<select name="periodo">` com as 6 opções
   - `onchange="this.form.submit()"` para recarregar ao selecionar
   - `selected` no valor atual passado pelo Flask via template context

2. **Cards de resumo** (RF-02) — 3 colunas:
   - `id="card-gastos"`, `id="card-investimentos"`, `id="card-saldo"` para atualização via JS
   - Placeholders com `—` até o JS carregar

3. **Gráficos — linha 1** (RF-03, RF-04) — 2 colunas:
   - `<canvas id="chart-pizza">` para pizza de categorias
   - `<canvas id="chart-barras">` para barras mensais

4. **Gráfico evolução** (RF-05) — largura total:
   - `<canvas id="chart-linha">` para linha de evolução

5. **Parcelas em andamento** (RF-06):
   - `<div id="parcelas-container">` para cards dinâmicos

6. **Tabela de transações** (RF-07):
   - Filtros: `<select id="filtro-tipo">`, `<select id="filtro-categoria">`
   - Botão `+ Adicionar`
   - `<table id="tabela-transacoes">` com colunas: Data, Descrição, Categoria, Valor, Parcela, Tipo, Ações
   - `<div id="paginacao">` para controles de página

7. **Seção de investimentos** (RF-08):
   - Card com totais `id="card-invest-periodo"` e `id="card-invest-total"`
   - `<table id="tabela-investimentos">` (mesma estrutura, filtrada por tipo)

8. **Modais Bootstrap** (usados por T08):
   - `id="modal-editar"` — formulário de edição
   - `id="modal-adicionar"` — formulário de inclusão
   - Campos: `data`, `descricao`, `categoria` (select), `valor`, `tipo` (select)

### Dados passados pelo Flask para o template

```python
# Em app.py, rota GET /
return render_template("index.html",
    periodo=request.args.get("periodo", "mes_atual"),
    categorias=["ALIMENTACAO", "TRANSPORTE", "LAZER", "GASTOS_FIXOS", "COMPRAS", "GASTOS_PONTUAIS", "OUTROS"],
    tipos=["GASTO", "INVESTIMENTO"],
    periodos={"mes_atual": "Mês atual", "mes_anterior": "Mês anterior", ...},
)
```

---

## Critérios de aceite

- [ ] `GET /` retorna 200 sem erro de template
- [ ] Seletor de período tem as 6 opções; opção atual está selecionada
- [ ] Todos os `id` de containers JS existem no HTML
- [ ] Modais são renderizados (escondidos) na página
- [ ] Página é responsiva em mobile (Bootstrap grid)
- [ ] Nenhum JS é escrito aqui — só estrutura HTML

---

## Comando de verificação

```bash
curl -s http://localhost:5000/ | grep -c "chart-pizza"
# Esperado: 1 (encontrou o canvas)

curl -s http://localhost:5000/ | grep -c "modal-editar"
# Esperado: 1
```
