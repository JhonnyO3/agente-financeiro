import { Bar } from 'react-chartjs-2';
import {
  Chart as ChartJS, CategoryScale, LinearScale, BarElement, Tooltip, Legend,
} from 'chart.js';

ChartJS.register(CategoryScale, LinearScale, BarElement, Tooltip, Legend);

const CAT_COLORS = {
  ALIMENTACAO:    '#3B72FF',
  TRANSPORTE:     '#22D3EE',
  LAZER:          '#F59E0B',
  EDUCACAO:       '#F472B6',
  GASTOS_FIXOS:   '#A78BFA',
  COMPRAS:        '#FB923C',
  GASTOS_PONTUAIS:'#22C55E',
};
const COLOR_LIST = Object.values(CAT_COLORS);

/* API retorna [{mes, ALIMENTACAO, TRANSPORTE, ...}, ...]  */
function transform(raw) {
  if (!raw || !raw.length) return { labels: [], datasets: [] };
  const labels = raw.map(r => r.mes);
  const cats = Object.keys(raw[0]).filter(k => k !== 'mes');
  const datasets = cats.map((cat, i) => ({
    label: cat,
    data: raw.map(r => Number(r[cat]) || 0),
    backgroundColor: (CAT_COLORS[cat] || COLOR_LIST[i % COLOR_LIST.length]) + 'CC',
    borderRadius: 4,
    borderSkipped: false,
  }));
  return { labels, datasets };
}

export default function BarChart({ data }) {
  if (!data || !data.length) return (
    <div style={{ color: 'var(--color-text-muted)', fontSize: 'var(--text-sm)', textAlign: 'center', padding: '40px 0' }}>
      Sem dados no período
    </div>
  );

  const { labels, datasets } = transform(data);
  const cfg  = { labels, datasets };
  const opts = {
    responsive: true,
    plugins: {
      legend: { position: 'bottom', labels: { color: '#9CA3AF', font: { size: 11 }, padding: 12 } },
      tooltip: {
        callbacks: {
          label: ctx => ` ${ctx.dataset.label}: ${Number(ctx.raw).toLocaleString('pt-BR',{style:'currency',currency:'BRL'})}`,
        },
      },
    },
    scales: {
      x: { stacked: true, ticks: { color: '#6B7280' }, grid: { color: 'rgba(255,255,255,0.04)' } },
      y: { stacked: true, ticks: { color: '#6B7280', callback: v => `R$ ${(v/1000).toFixed(0)}k` }, grid: { color: 'rgba(255,255,255,0.06)' } },
    },
  };

  return <Bar data={cfg} options={opts} />;
}
