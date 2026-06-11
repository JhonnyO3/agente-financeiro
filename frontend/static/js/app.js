(function () {
  "use strict";

  const PERIODO = new URLSearchParams(location.search).get("periodo") || "mes_atual";

  // Apenas exibição — nunca aritmética monetária em JS (contrato js-interop.md).
  function fmtBRL(s) {
    return Number(s).toLocaleString("pt-BR", { style: "currency", currency: "BRL" });
  }

  // ISO "yyyy-mm-dd" → "dd/mm/yyyy" (manipulação de string, sem timezone).
  function fmtDataISO(iso) {
    const partes = String(iso).split("-");
    if (partes.length !== 3) {
      return String(iso);
    }
    return partes[2] + "/" + partes[1] + "/" + partes[0];
  }

  async function fetchJSON(url, opcoes) {
    const resposta = await fetch(url, opcoes);
    if (!resposta.ok) {
      throw new Error("HTTP " + resposta.status + " em " + url);
    }
    return resposta.json();
  }

  // --- Cards de resumo (RF-02) -------------------------------------------

  async function carregarResumo() {
    const elGastos = document.getElementById("card-gastos");
    const elReceitas = document.getElementById("card-receitas");
    const elInvestimentos = document.getElementById("card-investimentos");
    const elSaldo = document.getElementById("card-saldo");
    if (!elGastos || !elReceitas || !elInvestimentos || !elSaldo) {
      return;
    }
    try {
      const resumo = await fetchJSON("/api/resumo?periodo=" + encodeURIComponent(PERIODO));
      elGastos.textContent = fmtBRL(resumo.gastos);
      elReceitas.textContent = fmtBRL(resumo.receitas);
      elInvestimentos.textContent = fmtBRL(resumo.investimentos);
      // `saldo` v2 = receitas − gastos (api-json-v2) — semântica vem da API.
      elSaldo.textContent = fmtBRL(resumo.saldo);
      // Sinal decidido pela string vinda da API — sem aritmética JS.
      const negativo = String(resumo.saldo).startsWith("-");
      elSaldo.classList.remove("text-success", "text-danger");
      elSaldo.classList.add(negativo ? "text-danger" : "text-success");
    } catch (erro) {
      console.error("Falha ao carregar resumo:", erro);
    }
  }

  // --- Projeção dos próximos 6 meses (dom-v2 / api-json-v2) ----------------

  function criarCelula(tag, texto, classe) {
    const celula = document.createElement(tag);
    celula.textContent = texto;
    if (classe) {
      celula.className = classe;
    }
    return celula;
  }

  function criarTabelaProjecao(meses) {
    const tabela = document.createElement("table");
    tabela.className = "table table-sm table-striped align-middle mb-0";

    const thead = document.createElement("thead");
    const linhaCabecalho = document.createElement("tr");
    const titulos = ["Mês", "Gastos pendentes", "Receitas pendentes", "Saldo projetado", "Parcelas"];
    for (const titulo of titulos) {
      linhaCabecalho.appendChild(criarCelula("th", titulo));
    }
    thead.appendChild(linhaCabecalho);
    tabela.appendChild(thead);

    const tbody = document.createElement("tbody");
    for (const mes of meses) {
      const linha = document.createElement("tr");
      linha.appendChild(criarCelula("td", mes.mes));
      linha.appendChild(criarCelula("td", fmtBRL(mes.gastos_pendentes)));
      linha.appendChild(criarCelula("td", fmtBRL(mes.receitas_pendentes)));
      // Cor decidida pelo sinal da string vinda da API — sem aritmética JS.
      const negativo = String(mes.saldo_projetado).startsWith("-");
      linha.appendChild(
        criarCelula("td", fmtBRL(mes.saldo_projetado), negativo ? "text-danger" : "text-success")
      );
      linha.appendChild(criarCelula("td", String(mes.qtd_parcelas)));
      tbody.appendChild(linha);
    }
    tabela.appendChild(tbody);

    return tabela;
  }

  async function carregarProjecao() {
    const container = document.getElementById("projecao-container");
    if (!container) {
      return;
    }
    try {
      const meses = await fetchJSON("/api/projecao");
      container.replaceChildren();
      if (!Array.isArray(meses) || meses.length === 0) {
        const vazio = document.createElement("p");
        vazio.className = "text-muted mb-0";
        vazio.textContent = "Nenhum lançamento pendente nos próximos meses";
        container.appendChild(vazio);
        return;
      }
      container.appendChild(criarTabelaProjecao(meses));
    } catch (erro) {
      console.error("Falha ao carregar projeção:", erro);
    }
  }

  // --- Parcelas em andamento (RF-06) -------------------------------------

  function criarCardParcela(grupo) {
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
    titulo.textContent = grupo.descricao;
    corpo.appendChild(titulo);

    const detalhes = document.createElement("p");
    detalhes.className = "card-text small text-muted mb-2";
    detalhes.textContent =
      "Parcela " + grupo.parcela_numero + "/" + grupo.parcela_total +
      "  ·  Próximo: " + fmtDataISO(grupo.proxima_data) +
      "  ·  " + fmtBRL(grupo.valor_parcela) + "/parcela";
    corpo.appendChild(detalhes);

    // Proporção apenas para layout da barra — não é aritmética monetária.
    const percentual = grupo.parcela_total > 0
      ? (grupo.pagas / grupo.parcela_total) * 100
      : 0;

    const progresso = document.createElement("div");
    progresso.className = "progress mb-3";
    progresso.setAttribute("role", "progressbar");
    progresso.setAttribute("aria-valuemin", "0");
    progresso.setAttribute("aria-valuemax", String(grupo.parcela_total));
    progresso.setAttribute("aria-valuenow", String(grupo.pagas));
    const barra = document.createElement("div");
    barra.className = "progress-bar";
    barra.style.width = percentual + "%";
    progresso.appendChild(barra);
    corpo.appendChild(progresso);

    const botaoExcluir = document.createElement("button");
    botaoExcluir.type = "button";
    botaoExcluir.className = "btn btn-outline-danger btn-sm";
    botaoExcluir.textContent = "Excluir grupo";
    botaoExcluir.addEventListener("click", function () {
      excluirGrupo(grupo.grupo_parcela_id, grupo.descricao);
    });
    corpo.appendChild(botaoExcluir);

    return coluna;
  }

  async function carregarParcelas() {
    const container = document.getElementById("parcelas-container");
    if (!container) {
      return;
    }
    try {
      const grupos = await fetchJSON("/api/parcelas-ativas");
      container.replaceChildren();
      if (!Array.isArray(grupos) || grupos.length === 0) {
        const vazio = document.createElement("p");
        vazio.className = "text-muted";
        vazio.textContent = "Nenhuma parcela em andamento";
        container.appendChild(vazio);
        return;
      }
      for (const grupo of grupos) {
        container.appendChild(criarCardParcela(grupo));
      }
    } catch (erro) {
      console.error("Falha ao carregar parcelas ativas:", erro);
    }
  }

  async function excluirGrupo(grupoParcelaId, descricao) {
    const confirmado = confirm(
      'Excluir o grupo de parcelas "' + descricao + '"? Todas as parcelas serão removidas.'
    );
    if (!confirmado) {
      return;
    }
    try {
      await fetchJSON("/api/grupos/" + encodeURIComponent(grupoParcelaId), {
        method: "DELETE",
      });
      await carregarParcelas();
    } catch (erro) {
      console.error("Falha ao excluir grupo de parcelas:", erro);
    }
  }

  // --- Inicialização -------------------------------------------------------

  document.addEventListener("DOMContentLoaded", function () {
    carregarResumo();
    carregarProjecao();
    carregarParcelas();
  });
})();
