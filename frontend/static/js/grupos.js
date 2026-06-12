(function () {
  "use strict";

  // fetchJSON que extrai corpo.erro — mesmo padrão de table.js
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
    const el = document.getElementById("modal-grupo");
    if (!el || typeof bootstrap === "undefined" || !bootstrap.Modal) return null;
    return { el: el, modal: bootstrap.Modal.getOrCreateInstance(el) };
  }

  function limparErro() {
    const el = document.getElementById("grupo-erro");
    if (el) el.textContent = "";
  }

  // Campos exclusivos do modo criar (categoria/forma/responsavel não aceitos no PUT)
  function definirModoCriar(visivel) {
    const wrappers = [
      document.getElementById("grupo-categoria-wrapper"),
      document.getElementById("grupo-forma-pagamento-wrapper"),
      document.getElementById("grupo-responsavel-wrapper"),
    ];
    for (const w of wrappers) {
      if (w) w.classList.toggle("d-none", !visivel);
    }
  }

  function abrirModoNovo() {
    const m = obterModal();
    if (!m) return;

    limparErro();
    definirModoCriar(true);

    const campos = ["grupo-id", "grupo-descricao", "grupo-valor", "grupo-parcela-atual",
                    "grupo-parcela-total", "grupo-proxima-data"];
    for (const id of campos) {
      const el = document.getElementById(id);
      if (el) el.value = "";
    }

    m.modal.show();
  }

  function abrirModoEditar(btn) {
    const m = obterModal();
    if (!m) return;

    limparErro();
    definirModoCriar(false);

    const set = function (id, val) {
      const el = document.getElementById(id);
      if (el) el.value = val || "";
    };

    set("grupo-id",           btn.dataset.grupo);
    set("grupo-descricao",    btn.dataset.descricao);
    set("grupo-valor",        btn.dataset.valor);
    set("grupo-parcela-atual", btn.dataset.parcelaAtual);
    set("grupo-parcela-total", btn.dataset.parcelaTotal);
    set("grupo-proxima-data", btn.dataset.proximaData);

    m.modal.show();
  }

  async function salvarGrupo() {
    const grupoId = (document.getElementById("grupo-id") || {}).value || "";
    const descricao = (document.getElementById("grupo-descricao") || {}).value || "";
    const valorParcela = (document.getElementById("grupo-valor") || {}).value || "";
    const parcelaAtual = (document.getElementById("grupo-parcela-atual") || {}).value || "";
    const parcelaTotal = (document.getElementById("grupo-parcela-total") || {}).value || "";
    const proximaData = (document.getElementById("grupo-proxima-data") || {}).value || "";

    const erroEl = document.getElementById("grupo-erro");

    let url, method, payload;

    if (grupoId) {
      // Modo editar — PUT (campos categoria/forma/responsavel não aceitos)
      method = "PUT";
      url = "/api/grupos/" + encodeURIComponent(grupoId);
      payload = {
        descricao: descricao,
        valor_parcela: valorParcela,
        proxima_data: proximaData,
        parcela_atual: parseInt(parcelaAtual, 10),
        parcela_total: parseInt(parcelaTotal, 10),
      };
    } else {
      // Modo criar — POST
      method = "POST";
      url = "/api/grupos";
      const categoria = (document.getElementById("grupo-categoria") || {}).value || "";
      const forma = (document.getElementById("grupo-forma-pagamento") || {}).value || "";
      const responsavel = (document.getElementById("grupo-responsavel") || {}).value || "";
      payload = {
        descricao: descricao,
        valor_parcela: valorParcela,
        parcela_total: parseInt(parcelaTotal, 10),
        parcela_atual: parseInt(parcelaAtual, 10) || 1,
        proxima_data: proximaData,
      };
      if (categoria) payload.categoria = categoria;
      if (forma) payload.forma_pagamento = forma;
      if (responsavel) payload.responsavel = responsavel;
    }

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

    if (typeof window.carregarParcelas === "function") {
      window.carregarParcelas();
    }
  }

  document.addEventListener("DOMContentLoaded", function () {
    const btnNovo = document.getElementById("btn-novo-parcelamento");
    if (btnNovo) btnNovo.addEventListener("click", abrirModoNovo);

    // Delegação para .btn-editar-grupo (injetados dinamicamente)
    document.addEventListener("click", function (ev) {
      const btn = ev.target.closest(".btn-editar-grupo");
      if (btn) abrirModoEditar(btn);
    });

    const btnSalvar = document.getElementById("btn-salvar-grupo");
    if (btnSalvar) btnSalvar.addEventListener("click", salvarGrupo);
  });
})();
