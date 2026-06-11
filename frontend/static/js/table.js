/**
 * table.js — Tabela de transações com filtros, paginação e CRUD via modais (RF-07)
 * e seção de investimentos com tabela e cards de totais (RF-08).
 * v2 (T09): colunas Status (badge) e Responsável, tooltip de detalhes,
 * filtro de status e campos novos nos modais (contratos dom-v2 / api-json-v2).
 *
 * IIFE autocontido (contrato js-interop.md). Única global exposta:
 * window.filtrarPorCategoria — consumida por charts.js no clique da pizza.
 *
 * Valores monetários trafegam SEMPRE como string decimal — nenhuma aritmética
 * monetária é feita em JS, apenas formatação para exibição.
 */
(function () {
  "use strict";

  const PERIODO = new URLSearchParams(location.search).get("periodo") || "mes_atual";

  // ---------------------------------------------------------------- helpers

  function fmtBRL(s) {
    return Number(s).toLocaleString("pt-BR", { style: "currency", currency: "BRL" });
  }

  // "2026-06-09" -> "09/06/2026" (manipulação de string, sem Date/fuso)
  function fmtData(iso) {
    if (typeof iso !== "string") return "";
    const partes = iso.split("-");
    if (partes.length !== 3) return iso;
    return partes[2] + "/" + partes[1] + "/" + partes[0];
  }

  // Normaliza o valor do <input type="number"> para string com 2 casas
  // (apenas formatação de exibição/transporte, não aritmética).
  function normalizarValor(v) {
    return Number(v).toFixed(2);
  }

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

  // ------------------------------------------------------------- estado

  // Tabela geral de transações
  const estado = { pagina: 1, tipo: "", categoria: "", status: "", forma: "" };
  // Tabela de investimentos (paginação própria, independente)
  const estadoInvest = { pagina: 1 };

  // id da transação em edição no modal
  let editandoId = null;

  // ------------------------------------------------------- erro nos modais

  function obterAreaErro(modalEl) {
    let alerta = modalEl.querySelector(".js-modal-erro");
    if (!alerta) {
      alerta = document.createElement("div");
      alerta.className = "alert alert-danger d-none js-modal-erro";
      alerta.setAttribute("role", "alert");
      const corpo = modalEl.querySelector(".modal-body");
      if (corpo) corpo.prepend(alerta);
    }
    return alerta;
  }

  function mostrarErroModal(modalEl, mensagem) {
    const alerta = obterAreaErro(modalEl);
    alerta.textContent = mensagem;
    alerta.classList.remove("d-none");
  }

  function limparErroModal(modalEl) {
    const alerta = modalEl.querySelector(".js-modal-erro");
    if (alerta) {
      alerta.textContent = "";
      alerta.classList.add("d-none");
    }
  }

  // ------------------------------------------------------- renderização

  function criarBotaoAcao(rotulo, titulo, classes, onClick) {
    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = "btn btn-sm " + classes;
    btn.title = titulo;
    btn.setAttribute("aria-label", titulo);
    btn.textContent = rotulo;
    btn.addEventListener("click", onClick);
    return btn;
  }

  // Badge de status (dom-v2.md): PAGO verde, PENDENTE amarelo.
  // Construído via createElement/textContent — nunca innerHTML com dados.
  function criarBadgeStatus(status) {
    const badge = document.createElement("span");
    badge.className =
      status === "PAGO" ? "badge text-bg-success" : "badge text-bg-warning";
    badge.textContent = status || "";
    return badge;
  }

  function criarLinha(item) {
    const tr = document.createElement("tr");

    const parcela =
      item.parcela_total > 1 ? item.parcela_numero + "/" + item.parcela_total : "";
    const celulas = [
      fmtData(item.data),
      item.descricao || "",
      item.categoria || "",
      fmtBRL(item.valor),
      parcela,
      item.forma_pagamento || "",
      item.tipo || "",
    ];
    for (const texto of celulas) {
      const td = document.createElement("td");
      td.textContent = texto; // textContent: escapa dados do usuário
      tr.appendChild(td);
    }

    // detalhes não vazio → tooltip na célula Descrição (2ª coluna)
    if (item.detalhes) {
      tr.children[1].title = item.detalhes;
    }

    // Colunas novas entre Tipo e Ações (mesma ordem do thead): Status, Responsável
    const tdStatus = document.createElement("td");
    tdStatus.appendChild(criarBadgeStatus(item.status));
    tr.appendChild(tdStatus);

    const tdResponsavel = document.createElement("td");
    tdResponsavel.textContent = item.responsavel || "";
    tr.appendChild(tdResponsavel);

    const tdAcoes = document.createElement("td");
    const grupo = document.createElement("div");
    grupo.className = "d-flex gap-1";
    grupo.appendChild(
      criarBotaoAcao("✏️", "Editar", "btn-outline-secondary", function () {
        abrirModalEditar(item);
      })
    );
    grupo.appendChild(
      criarBotaoAcao("🗑️", "Excluir", "btn-outline-danger", function () {
        excluirTransacao(item);
      })
    );
    tdAcoes.appendChild(grupo);
    tr.appendChild(tdAcoes);

    return tr;
  }

  function renderizarTbody(tabela, itens) {
    const tbody = tabela.querySelector("tbody");
    if (!tbody) return;
    tbody.replaceChildren();
    if (!itens || itens.length === 0) {
      const tr = document.createElement("tr");
      const td = document.createElement("td");
      td.colSpan = 10;
      td.className = "text-center text-muted";
      td.textContent = "Nenhuma transação encontrada";
      tr.appendChild(td);
      tbody.appendChild(tr);
      return;
    }
    for (const item of itens) {
      tbody.appendChild(criarLinha(item));
    }
  }

  function renderizarPaginacao(container, dados, aoMudarPagina) {
    if (!container) return;
    container.replaceChildren();

    const pagina = dados.pagina || 1;
    const paginas = Math.max(1, dados.paginas || 1);

    const wrap = document.createElement("div");
    wrap.className = "d-flex align-items-center gap-2";

    const btnAnterior = document.createElement("button");
    btnAnterior.type = "button";
    btnAnterior.className = "btn btn-sm btn-outline-primary";
    btnAnterior.textContent = "Anterior";
    btnAnterior.disabled = pagina <= 1;
    btnAnterior.addEventListener("click", function () {
      aoMudarPagina(pagina - 1);
    });

    const indicador = document.createElement("span");
    indicador.className = "text-muted small";
    indicador.textContent = pagina + "/" + paginas;

    const btnProxima = document.createElement("button");
    btnProxima.type = "button";
    btnProxima.className = "btn btn-sm btn-outline-primary";
    btnProxima.textContent = "Próxima";
    btnProxima.disabled = pagina >= paginas;
    btnProxima.addEventListener("click", function () {
      aoMudarPagina(pagina + 1);
    });

    wrap.appendChild(btnAnterior);
    wrap.appendChild(indicador);
    wrap.appendChild(btnProxima);
    container.appendChild(wrap);
  }

  // ------------------------------------------------- tabela de transações

  async function carregarTabela() {
    const tabela = document.getElementById("tabela-transacoes");
    if (!tabela) return;

    const params = new URLSearchParams({ periodo: PERIODO, pagina: String(estado.pagina) });
    if (estado.tipo) params.set("tipo", estado.tipo);
    if (estado.categoria) params.set("categoria", estado.categoria);
    if (estado.status) params.set("status", estado.status);
    if (estado.forma) params.set("forma_pagamento", estado.forma);

    let dados;
    try {
      dados = await fetchJSON("/api/transacoes?" + params.toString());
    } catch (err) {
      console.error("Erro ao carregar transações:", err);
      return;
    }

    // Página fora do intervalo (ex.: após exclusão do último item) → recua
    if (dados.itens.length === 0 && dados.pagina > 1) {
      estado.pagina = Math.max(1, dados.paginas || 1);
      return carregarTabela();
    }

    renderizarTbody(tabela, dados.itens);
    renderizarPaginacao(document.getElementById("paginacao"), dados, function (novaPagina) {
      estado.pagina = novaPagina;
      carregarTabela();
    });
  }

  // ------------------------------------------------- investimentos (RF-08)

  // Container de paginação próprio, criado via JS logo após a tabela
  // (o template não define um; #tabela-investimentos pertence a este arquivo).
  function obterPaginacaoInvest() {
    let container = document.getElementById("paginacao-investimentos");
    if (!container) {
      const tabela = document.getElementById("tabela-investimentos");
      if (!tabela) return null;
      container = document.createElement("div");
      container.id = "paginacao-investimentos";
      container.className = "d-flex justify-content-center";
      const wrap = tabela.closest(".table-responsive") || tabela;
      wrap.insertAdjacentElement("afterend", container);
    }
    return container;
  }

  async function carregarInvestimentos() {
    const tabela = document.getElementById("tabela-investimentos");
    if (!tabela) return;

    const params = new URLSearchParams({
      periodo: PERIODO,
      tipo: "INVESTIMENTO",
      pagina: String(estadoInvest.pagina),
    });

    let dados;
    try {
      dados = await fetchJSON("/api/transacoes?" + params.toString());
    } catch (err) {
      console.error("Erro ao carregar investimentos:", err);
      return;
    }

    if (dados.itens.length === 0 && dados.pagina > 1) {
      estadoInvest.pagina = Math.max(1, dados.paginas || 1);
      return carregarInvestimentos();
    }

    renderizarTbody(tabela, dados.itens);
    renderizarPaginacao(obterPaginacaoInvest(), dados, function (novaPagina) {
      estadoInvest.pagina = novaPagina;
      carregarInvestimentos();
    });
  }

  async function carregarCardsInvestimentos() {
    const cardPeriodo = document.getElementById("card-invest-periodo");
    const cardTotal = document.getElementById("card-invest-total");
    if (!cardPeriodo && !cardTotal) return;

    if (cardPeriodo) {
      try {
        const resumo = await fetchJSON("/api/resumo?periodo=" + encodeURIComponent(PERIODO));
        cardPeriodo.textContent = fmtBRL(resumo.investimentos);
      } catch (err) {
        console.error("Erro ao carregar resumo do período:", err);
      }
    }
    if (cardTotal) {
      try {
        const resumoTudo = await fetchJSON("/api/resumo?periodo=tudo");
        cardTotal.textContent = fmtBRL(resumoTudo.investimentos);
      } catch (err) {
        console.error("Erro ao carregar resumo histórico:", err);
      }
    }
  }

  // Recarrega tudo que muda após uma mutação (POST/PUT/DELETE)
  function recarregarTabelas() {
    carregarTabela();
    carregarInvestimentos();
    carregarCardsInvestimentos();
  }

  // ------------------------------------------------------------ modais

  function obterModal(id) {
    const el = document.getElementById(id);
    if (!el || typeof bootstrap === "undefined" || !bootstrap.Modal) return null;
    return { el: el, modal: bootstrap.Modal.getOrCreateInstance(el) };
  }

  // ---- editar

  function abrirModalEditar(item) {
    const m = obterModal("modal-editar");
    if (!m) return;

    editandoId = item.id;
    limparErroModal(m.el);

    const campoData = document.getElementById("edit-data");
    const campoDescricao = document.getElementById("edit-descricao");
    const campoCategoria = document.getElementById("edit-categoria");
    const campoValor = document.getElementById("edit-valor");
    const campoStatus = document.getElementById("edit-status");
    const campoForma = document.getElementById("edit-forma-pagamento");
    const campoResponsavel = document.getElementById("edit-responsavel");
    const campoDetalhes = document.getElementById("edit-detalhes");

    if (campoData) campoData.value = item.data || "";
    if (campoDescricao) campoDescricao.value = item.descricao || "";
    if (campoCategoria) campoCategoria.value = item.categoria || "";
    if (campoValor) campoValor.value = item.valor || "";
    if (campoStatus) campoStatus.value = item.status || "";
    if (campoForma) campoForma.value = item.forma_pagamento || "";
    if (campoResponsavel) campoResponsavel.value = item.responsavel || "";
    if (campoDetalhes) campoDetalhes.value = item.detalhes || "";

    m.modal.show();
  }

  async function salvarEdicao() {
    const m = obterModal("modal-editar");
    if (!m || editandoId === null) return;

    const campoData = document.getElementById("edit-data");
    const campoDescricao = document.getElementById("edit-descricao");
    const campoCategoria = document.getElementById("edit-categoria");
    const campoValor = document.getElementById("edit-valor");
    const campoStatus = document.getElementById("edit-status");
    const campoForma = document.getElementById("edit-forma-pagamento");
    const campoResponsavel = document.getElementById("edit-responsavel");
    const campoDetalhes = document.getElementById("edit-detalhes");

    const data = campoData ? campoData.value : "";
    const valor = campoValor ? campoValor.value : "";
    const categoria = campoCategoria ? campoCategoria.value : "";

    if (!data || !valor || !categoria) {
      mostrarErroModal(m.el, "Preencha data, valor e categoria.");
      return;
    }

    const corpo = {
      data: data,
      descricao: campoDescricao ? campoDescricao.value : "",
      categoria: categoria,
      valor: normalizarValor(valor),
      status: campoStatus ? campoStatus.value : "",
      forma_pagamento: campoForma ? campoForma.value : "",
      responsavel: campoResponsavel ? campoResponsavel.value : "",
      detalhes: campoDetalhes ? campoDetalhes.value : "",
    };

    try {
      await fetchJSON("/api/transacoes/" + editandoId, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(corpo),
      });
    } catch (err) {
      mostrarErroModal(m.el, err.message);
      return;
    }

    editandoId = null;
    m.modal.hide();
    recarregarTabelas();
  }

  // ---- adicionar

  function abrirModalAdicionar() {
    const m = obterModal("modal-adicionar");
    if (!m) return;

    limparErroModal(m.el);
    const form = document.getElementById("form-adicionar");
    if (form) form.reset();

    m.modal.show();
  }

  async function salvarAdicao() {
    const m = obterModal("modal-adicionar");
    if (!m) return;

    const campoData = document.getElementById("add-data");
    const campoDescricao = document.getElementById("add-descricao");
    const campoCategoria = document.getElementById("add-categoria");
    const campoValor = document.getElementById("add-valor");
    const campoTipo = document.getElementById("add-tipo");
    const campoStatus = document.getElementById("add-status");
    const campoForma = document.getElementById("add-forma-pagamento");
    const campoResponsavel = document.getElementById("add-responsavel");
    const campoDetalhes = document.getElementById("add-detalhes");

    const data = campoData ? campoData.value : "";
    const valor = campoValor ? campoValor.value : "";
    const categoria = campoCategoria ? campoCategoria.value : "";
    const tipo = campoTipo ? campoTipo.value : "";

    // Validação client-side dos obrigatórios
    if (!data || !valor || !tipo || !categoria) {
      mostrarErroModal(m.el, "Preencha os campos obrigatórios: data, valor, tipo e categoria.");
      return;
    }

    const corpo = {
      data: data,
      descricao: campoDescricao ? campoDescricao.value : "",
      categoria: categoria,
      valor: normalizarValor(valor),
      tipo: tipo,
    };

    // Campos v2 opcionais: vazios ficam fora do body para o servidor
    // aplicar os defaults (api-json-v2.md).
    const status = campoStatus ? campoStatus.value : "";
    const forma = campoForma ? campoForma.value : "";
    const responsavel = campoResponsavel ? campoResponsavel.value : "";
    const detalhes = campoDetalhes ? campoDetalhes.value : "";
    if (status) corpo.status = status;
    if (forma) corpo.forma_pagamento = forma;
    if (responsavel) corpo.responsavel = responsavel;
    if (detalhes) corpo.detalhes = detalhes;

    try {
      await fetchJSON("/api/transacoes", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(corpo),
      });
    } catch (err) {
      mostrarErroModal(m.el, err.message);
      return;
    }

    m.modal.hide();
    recarregarTabelas();
  }

  // ---- excluir

  async function excluirTransacao(item) {
    const descricao = item.descricao || "transação";
    if (!window.confirm('Excluir "' + descricao + '" (' + fmtBRL(item.valor) + ")?")) {
      return;
    }
    try {
      await fetchJSON("/api/transacoes/" + item.id, { method: "DELETE" });
    } catch (err) {
      console.error("Erro ao excluir transação:", err);
      window.alert("Erro ao excluir: " + err.message);
      return;
    }
    recarregarTabelas();
  }

  // ------------------------------------------------------ global do contrato

  window.filtrarPorCategoria = function (categoria) {
    const select = document.getElementById("filtro-categoria");
    if (select) select.value = categoria;
    estado.categoria = categoria;
    estado.pagina = 1;
    carregarTabela();
  };

  // -------------------------------------------------------------- init

  document.addEventListener("DOMContentLoaded", function () {
    const filtroTipo = document.getElementById("filtro-tipo");
    if (filtroTipo) {
      filtroTipo.addEventListener("change", function () {
        estado.tipo = filtroTipo.value;
        estado.pagina = 1;
        carregarTabela();
      });
    }

    const filtroCategoria = document.getElementById("filtro-categoria");
    if (filtroCategoria) {
      filtroCategoria.addEventListener("change", function () {
        estado.categoria = filtroCategoria.value;
        estado.pagina = 1;
        carregarTabela();
      });
    }

    const filtroStatus = document.getElementById("filtro-status");
    if (filtroStatus) {
      filtroStatus.addEventListener("change", function () {
        estado.status = filtroStatus.value;
        estado.pagina = 1;
        carregarTabela();
      });
    }

    const filtroForma = document.getElementById("filtro-forma-pagamento");
    if (filtroForma) {
      filtroForma.addEventListener("change", function () {
        estado.forma = filtroForma.value;
        estado.pagina = 1;
        carregarTabela();
      });
    }

    const btnAdicionar = document.getElementById("btn-adicionar");
    if (btnAdicionar) btnAdicionar.addEventListener("click", abrirModalAdicionar);

    const btnSalvarEditar = document.getElementById("btn-salvar-editar");
    if (btnSalvarEditar) btnSalvarEditar.addEventListener("click", salvarEdicao);

    const btnSalvarAdicionar = document.getElementById("btn-salvar-adicionar");
    if (btnSalvarAdicionar) btnSalvarAdicionar.addEventListener("click", salvarAdicao);

    carregarTabela();
    carregarInvestimentos();
    carregarCardsInvestimentos();
  });
})();
