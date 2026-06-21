import { Line } from 'react-chartjs-2';
import {
  Chart as ChartJS, CategoryScale, LinearScale, PointElement, LineElement, Filler, Tooltip, Legend,
} from 'chart.js';

ChartJS.register(CategoryScale, LinearScale, PointElement, LineElement, Filler, Tooltip, Legend);

const SERIES_COLORS = { gastos:'#EF4444', investimentos:'#22D3EE', receitas:'#22C55E' };
const LABELS_MAP    = { gastos:'Gastos', investimentos:'Investimentos', receitas:'Receitas' };

export default function LineChart({ data }) {
  if (!data) return null;

  const labels   = data.labels || [];
  const datasets = Object.entries(data)
    .filter(([k]) => k !== 'labels')
    .map(([key, values]) => ({
      label: LABELS_MAP[key] || key,
      data: values,
      borderColor: SERIES_COLORS[key] || '#3B72FF',
      backgroundColor: (SERIES_COLORS[key] || '#3B72FF') + '22',
      fill: true,
      tension: 0.4,
      pointRadius: 4,
      pointHoverRadius: 6,
    }));

  const cfg  = { labels, datasets };
  const opts = {
    responsive: true,
    interaction: { mode: 'index', intersect: false },
    plugins: {
      legend: { position: 'bottom', labels: { color: '#9CA3AF', font: { size: 12 }, padding: 16 } },
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
