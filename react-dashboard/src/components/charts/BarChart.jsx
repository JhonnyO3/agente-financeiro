import { Bar } from 'react-chartjs-2';
import {
  Chart as ChartJS, CategoryScale, LinearScale, BarElement, Tooltip, Legend,
} from 'chart.js';

ChartJS.register(CategoryScale, LinearScale, BarElement, Tooltip, Legend);

const CAT_COLORS = [
  '#3B72FF','#22D3EE','#A78BFA','#22C55E','#F59E0B','#F472B6','#FB923C','#9CA3AF',
];

export default function BarChart({ data }) {
  if (!data) return null;

  const labels   = data.meses  || [];
  const datasets = (data.series || []).map((s, i) => ({
    label: s.categoria,
    data: s.valores,
    backgroundColor: CAT_COLORS[i % CAT_COLORS.length] + 'CC',
    borderRadius: 4,
    borderSkipped: false,
  }));

  const cfg  = { labels, datasets };
  const opts = {
    responsive: true,
    plugins: {
      legend: { position: 'bottom', labels: { color: '#9CA3AF', font: { size: 12 }, padding: 16 } },
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
