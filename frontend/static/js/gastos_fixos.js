(function () {
  "use strict";

  // Mapa id → item carregado do backend, para preencher o modal de edição.
  var _itens = {};

  // fetchJSON que extrai corpo.erro — mesmo padrão de grupos.js.
  async function fetchJSON(url, opcoes) {
    const res = await fetch(url, opcoes);
    let corpo = null;
    try {
      corpo = await res.json();
    } catch (_e) {
      corpo = null;
    }
    if (!res.ok) {
      const msg = corpo && corpo.erro ? corpo.erro : "Erro HTTP " + res.status;
      const err = new Error(msg);
      err.status = res.status;
      throw err;
    }
    return corpo;
  }

  function obterModal() {
    const el = document.getElementById("modal-gasto-fixo");
    if (!el || typeof bootstrap === "undefined" || !bootstrap.Modal) return null;
    return { el: el, modal: bootstrap.Modal.getOrCreateInstance(el) };
  }

  function limparErro() {
    const el = document.getElementById("gf-erro");
    if (el) el.textContent = "";
  }

  // Exibição do valor: recebe string do backend e formata como BRL sem aritmética.
  function fmtBRL(s) {
    return Number(s).toLocaleString("pt-BR", { style: "currency", currency: "BRL" });
  }

  function criarCardGastoFixo(item) {
    const coluna = document.createElement("div");
    coluna.className = "col-12 col-md-6 col-lg-4";

    const card = document.createElement("div");
    card.className = "card h-100";
    coluna.appendChild(card);

    const corpo = document.createElement("div");
    corpo.className = "card-body";
    card.appendChild(corpo);

    const titulo = document.createElement("h6");
    titulo.className = "card-title";
    titulo.textContent = item.descricao;
    corpo.appendChild(titulo);

    const detalhes = document.createElement("p");
    detalhes.className = "card-text small text-muted mb-2";
    detalhes.textContent =
      fmtBRL(item.valor) +
      "  ·  todo dia " + item.dia_vencimento +
      "  ·  " + item.categoria +
      "  ·  " + item.forma_pagamento;
    corpo.appendChild(detalhes);

    const acoes = document.createElement("div");
    acoes.className = "d-flex gap-2";

    const botaoEditar = document.createElement("button");
    botaoEditar.type = "button";
    botaoEditar.className = "btn btn-outline-secondary btn-sm btn-editar-gasto-fixo";
    botaoEditar.textContent = "Editar";
    botaoEditar.dataset.id = String(item.id);
    acoes.appendChild(botaoEditar);

    const botaoRemover = document.createElement("button");
    botaoRemover.type = "button";
    botaoRemover.className = "btn btn-outline-danger btn-sm btn-remover-gasto-fixo";
    botaoRemover.textContent = "Remover";
    botaoRemover.dataset.id = String(item.id);
    acoes.appendChild(botaoRemover);

    corpo.appendChild(acoes);

    return coluna;
  }

  async function carregarGastosFixos() {
    const container = document.getElementById("gastos-fixos-container");
    const vazio = document.getElementById("gastos-fixos-vazio");
    const totalEl = document.getElementById("gastos-fixos-total");

    if (!container) return;

    try {
      const dados = await fetchJSON("/api/gastos-fixos");
      const itens = dados.itens || [];

      // Atualiza mapa em memória para edição posterior.
      _itens = {};
      for (const item of itens) {
        _itens[String(item.id)] = item;
      }

      container.replaceChildren();

      if (itens.length === 0) {
        if (vazio) vazio.classList.remove("d-none");
      } else {
        if (vazio) vazio.classList.add("d-none");
        for (const item of itens) {
          container.appendChild(criarCardGastoFixo(item));
        }
      }

      // Total mensal exibido como string recebida do backend — sem somar no JS.
      if (totalEl) totalEl.textContent = dados.total_mensal || "0.00";
    } catch (erro) {
      console.error("Falha ao carregar gastos fixos:", erro);
    }
  }

  function abrirModoNovo() {
    const m = obterModal();
    if (!m) return;

    limparErro();

    const campos = ["gf-id", "gf-descricao", "gf-valor", "gf-data", "gf-responsavel"];
    for (const id of campos) {
      const el = document.getElementById(id);
      if (el) el.value = "";
    }

    // Restaura defaults do modal para modo criar.
    const categoria = document.getElementById("gf-categoria");
    if (categoria) {
      for (const opt of categoria.options) {
        opt.selected = opt.value === "GASTOS_FIXOS";
      }
    }
    const forma = document.getElementById("gf-forma-pagamento");
    if (forma) {
      for (const opt of forma.options) {
        opt.selected = opt.value === "PIX";
      }
    }

    m.modal.show();
  }

  function abrirModoEditar(btn) {
    const m = obterModal();
    if (!m) return;

    limparErro();

    const id = btn.dataset.id;
    const item = _itens[id];
    if (!item) return;

    const set = function (elId, val) {
      const el = document.getElementById(elId);
      if (el) el.value = val || "";
    };

    set("gf-id", String(item.id));
    set("gf-descricao", item.descricao);
    set("gf-valor", item.valor);
    set("gf-data", item.data);
    set("gf-responsavel", item.responsavel || "");

    const categoria = document.getElementById("gf-categoria");
    if (categoria && item.categoria) {
      for (const opt of categoria.options) {
        opt.selected = opt.value === item.categoria;
      }
    }
    const forma = document.getElementById("gf-forma-pagamento");
    if (forma && item.forma_pagamento) {
      for (const opt of forma.options) {
        opt.selected = opt.value === item.forma_pagamento;
      }
    }

    m.modal.show();
  }

  async function salvarGastoFixo() {
    const idEl = document.getElementById("gf-id");
    const id = idEl ? idEl.value : "";
    const descricao = (document.getElementById("gf-descricao") || {}).value || "";
    const valor = (document.getElementById("gf-valor") || {}).value || "";
    const data = (document.getElementById("gf-data") || {}).value || "";
    const categoria = (document.getElementById("gf-categoria") || {}).value || "";
    const forma = (document.getElementById("gf-forma-pagamento") || {}).value || "";
    const responsavel = (document.getElementById("gf-responsavel") || {}).value || "";
    const erroEl = document.getElementById("gf-erro");

    // Valor enviado como string — sem conversão numérica (proibido aritmética no JS).
    const payload = {
      descricao: descricao,
      valor: valor,
      data: data,
    };
    if (categoria) payload.categoria = categoria;
    if (forma) payload.forma_pagamento = forma;
    if (responsavel) payload.responsavel = responsavel;

    const url = id ? "/api/gastos-fixos/" + encodeURIComponent(id) : "/api/gastos-fixos";
    const method = id ? "PUT" : "POST";

    try {
      await fetchJSON(url, {
        method: method,
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
    } catch (err) {
      if (erroEl) erroEl.textContent = err.message;
      return;
    }

    const m = obterModal();
    if (m) m.modal.hide();

    await carregarGastosFixos();
  }

  async function removerGastoFixo(btn) {
    const id = btn.dataset.id;
    const confirmado = confirm("Remover este gasto fixo?");
    if (!confirmado) return;

    try {
      await fetchJSON("/api/gastos-fixos/" + encodeURIComponent(id), { method: "DELETE" });
    } catch (erro) {
      console.error("Falha ao remover gasto fixo:", erro);
    }

    await carregarGastosFixos();
  }

  document.addEventListener("DOMContentLoaded", function () {
    const btnNovo = document.getElementById("btn-novo-gasto-fixo");
    if (btnNovo) btnNovo.addEventListener("click", abrirModoNovo);

    // Delegação para botões injetados dinamicamente.
    document.addEventListener("click", function (ev) {
      const btnEditar = ev.target.closest(".btn-editar-gasto-fixo");
      if (btnEditar) { abrirModoEditar(btnEditar); return; }

      const btnRemover = ev.target.closest(".btn-remover-gasto-fixo");
      if (btnRemover) removerGastoFixo(btnRemover);
    });

    const btnSalvar = document.getElementById("btn-salvar-gasto-fixo");
    if (btnSalvar) btnSalvar.addEventListener("click", salvarGastoFixo);

    carregarGastosFixos();
  });
})();
