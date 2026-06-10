/**
 * charts.js — Gráficos Chart.js do dashboard (T07).
 *
 * IIFE autocontido (contrato js-interop.md): nenhuma global é criada aqui.
 * Possui os canvas #chart-pizza, #chart-barras e #chart-linha.
 * Única interop permitida: chamar window.filtrarPorCategoria (definida por
 * table.js) no clique de uma fatia da pizza, sempre com guarda typeof.
 */
(function () {
  "use strict";

  // Período atual lido da URL (contrato js-interop.md, regra 3).
  const PERIODO =
    new URLSearchParams(location.search).get("periodo") || "mes_atual";

  // Formatação monetária — apenas exibição, nunca aritmética (regra 4).
  function fmtBRL(s) {
    return Number(s).toLocaleString("pt-BR", {
      style: "currency",
      currency: "BRL",
    });
  }

  // Cores fixas por categoria (contrato js-interop.md).
  const CORES_CATEGORIA = {
    ALIMENTACAO: "#fd7e14",
    TRANSPORTE: "#0d6efd",
    LAZER: "#6f42c1",
    GASTOS_FIXOS: "#dc3545",
    COMPRAS: "#d63384",
    GASTOS_PONTUAIS: "#ffc107",
    OUTROS: "#6c757d",
  };

  // fetch JSON com tratamento de erro do contrato: não-2xx vira exceção,
  // o chamador loga via console.error e deixa o canvas vazio.
  async function fetchJSON(url) {
    const resp = await fetch(url);
    if (!resp.ok) {
      throw new Error(`HTTP ${resp.status} em ${url}`);
    }
    return resp.json();
  }

  // ------------------------------------------------------------------
  // Pizza de gastos por categoria (RF-03) — #chart-pizza
  // ------------------------------------------------------------------
  async function initPizza() {
    const canvas = document.getElementById("chart-pizza");
    if (!canvas) return;

    let dados;
    try {
      dados = await fetchJSON(
        `/api/grafico/categorias?periodo=${encodeURIComponent(PERIODO)}`
      );
    } catch (erro) {
      console.error("Falha ao carregar grafico de categorias:", erro);
      return;
    }

    const categorias = dados.map((d) => d.categoria);

    new Chart(canvas, {
      type: "doughnut",
      data: {
        labels: categorias,
        datasets: [
          {
            data: dados.map((d) => Number(d.total)),
            backgroundColor: categorias.map(
              (c) => CORES_CATEGORIA[c] || CORES_CATEGORIA.OUTROS
            ),
          },
        ],
      },
      options: {
        responsive: true,
        onClick: (evento, elementos) => {
          if (!elementos.length) return;
          const categoria = categorias[elementos[0].index];
          if (typeof window.filtrarPorCategoria === "function") {
            window.filtrarPorCategoria(categoria);
          }
        },
        plugins: {
          legend: {
            position: "right",
            labels: {
              // "CATEGORIA — R$ 150,00 (42.86%)"
              generateLabels: (chart) => {
                const base =
                  Chart.overrides.doughnut.plugins.legend.labels.generateLabels(
                    chart
                  );
                return base.map((item) => {
                  const d = dados[item.index];
                  return {
                    ...item,
                    text: `${d.categoria} — ${fmtBRL(d.total)} (${d.percentual}%)`,
                  };
                });
              },
            },
          },
          tooltip: {
            callbacks: {
              label: (ctx) => {
                const d = dados[ctx.dataIndex];
                return `${d.categoria} — ${fmtBRL(d.total)} (${d.percentual}%)`;
              },
            },
          },
        },
      },
    });
  }

  // ------------------------------------------------------------------
  // Barras mensais empilhadas (RF-04) — #chart-barras
  // ------------------------------------------------------------------
  async function initBarras() {
    const canvas = document.getElementById("chart-barras");
    if (!canvas) return;

    let dados;
    try {
      // Sempre últimos 6 meses — sem query param de período (contrato api-json).
      dados = await fetchJSON("/api/grafico/mensal");
    } catch (erro) {
      console.error("Falha ao carregar grafico mensal:", erro);
      return;
    }

    const labels = dados.map((d) => d.mes);
    const categorias = Object.keys(CORES_CATEGORIA);

    new Chart(canvas, {
      type: "bar",
      data: {
        labels,
        datasets: categorias.map((categoria) => ({
          label: categoria,
          data: dados.map((d) => Number(d[categoria])),
          backgroundColor: CORES_CATEGORIA[categoria],
        })),
      },
      options: {
        responsive: true,
        scales: {
          x: { stacked: true },
          y: {
            stacked: true,
            ticks: {
              callback: (valor) => fmtBRL(valor),
            },
          },
        },
        plugins: {
          tooltip: {
            callbacks: {
              label: (ctx) => {
                const categoria = ctx.dataset.label;
                return `${categoria}: ${fmtBRL(dados[ctx.dataIndex][categoria])}`;
              },
            },
          },
        },
      },
    });
  }

  // ------------------------------------------------------------------
  // Linha de evolução gastos x investimentos (RF-05) — #chart-linha
  // ------------------------------------------------------------------
  async function initLinha() {
    const canvas = document.getElementById("chart-linha");
    if (!canvas) return;

    let dados;
    try {
      dados = await fetchJSON("/api/grafico/evolucao");
    } catch (erro) {
      console.error("Falha ao carregar grafico de evolucao:", erro);
      return;
    }

    new Chart(canvas, {
      type: "line",
      data: {
        labels: dados.map((d) => d.mes),
        datasets: [
          {
            label: "Gastos",
            data: dados.map((d) => Number(d.gastos)),
            borderColor: "#dc3545",
            backgroundColor: "#dc3545",
            pointRadius: 4,
          },
          {
            label: "Investimentos",
            data: dados.map((d) => Number(d.investimentos)),
            borderColor: "#198754",
            backgroundColor: "#198754",
            pointRadius: 4,
          },
        ],
      },
      options: {
        responsive: true,
        scales: {
          y: {
            ticks: {
              callback: (valor) => fmtBRL(valor),
            },
          },
        },
        plugins: {
          tooltip: {
            callbacks: {
              label: (ctx) => `${ctx.dataset.label}: ${fmtBRL(ctx.parsed.y)}`,
            },
          },
        },
      },
    });
  }

  document.addEventListener("DOMContentLoaded", () => {
    initPizza();
    initBarras();
    initLinha();
  });
})();
