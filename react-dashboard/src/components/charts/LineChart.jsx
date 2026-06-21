import { Line } from 'react-chartjs-2';
import {
  Chart as ChartJS, CategoryScale, LinearScale, PointElement, LineElement, Filler, Tooltip, Legend,
} from 'chart.js';

ChartJS.register(CategoryScale, LinearScale, PointElement, LineElement, Filler, Tooltip, Legend);

const SERIES = {
  gastos:        { label: 'Gastos',        color: '#EF4444' },
  receitas:      { label: 'Receitas',       color: '#22C55E' },
  investimentos: { label: 'Investimentos',  color: '#22D3EE' },
};

/* API retorna [{mes, gastos, receitas, investimentos}, ...] */
function transform(raw) {
  if (!raw || !raw.length) return { labels: [], datasets: [] };
  const labels = raw.map(r => r.mes);
  const datasets = Object.entries(SERIES).map(([key, { label, color }]) => ({
    label,
    data: raw.map(r => Number(r[key]) || 0),
    borderColor: color,
    backgroundColor: color + '18',
    fill: true,
    tension: 0.4,
    pointRadius: 3,
    pointHoverRadius: 6,
    borderWidth: 2,
  }));
  return { labels, datasets };
}

export default function LineChart({ data }) {
  if (!data || !data.length) return (
    <div style={{ color: 'var(--color-text-muted)', fontSize: 'var(--text-sm)', textAlign: 'center', padding: '60px 0' }}>
      Sem dados no período
    </div>
  );

  const { labels, datasets } = transform(data);
  const cfg  = { labels, datasets };
  const opts = {
    responsive: true,
    maintainAspectRatio: false,
    interaction: { mode: 'index', intersect: false },
    plugins: {
      legend: { position: 'bottom', labels: { color: '#9CA3AF', font: { size: 11 }, padding: 12 } },
      tooltip: {
        callbacks: {
          label: ctx => ` ${ctx.dataset.label}: ${Number(ctx.raw).toLocaleString('pt-BR',{style:'currency',currency:'BRL'})}`,
        },
      },
    },
    scales: {
      x: { ticks: { color: '#6B7280' }, grid: { color: 'rgba(255,255,255,0.04)' } },
      y: { ticks: { color: '#6B7280', callback: v => `R$ ${(v/1000).toFixed(0)}k` }, grid: { color: 'rgba(255,255,255,0.06)' } },
    },
  };

  return <Line data={cfg} options={opts} />;
}
