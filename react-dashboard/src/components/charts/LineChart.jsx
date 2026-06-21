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

function transform(raw) {
  if (!raw || !raw.length) return { labels: [], datasets: [] };
  const labels = raw.map(r => r.mes);
  const isMobile = window.innerWidth < 600;
  const datasets = Object.entries(SERIES).map(([key, { label, color }]) => ({
    label,
    data: raw.map(r => Number(r[key]) || 0),
    borderColor: color,
    backgroundColor: color + '22',
    fill: true,
    tension: 0.4,
    pointRadius: isMobile ? 4 : 3,
    pointHoverRadius: isMobile ? 8 : 6,
    borderWidth: isMobile ? 2.5 : 2,
  }));
  return { labels, datasets };
}

export default function LineChart({ data }) {
  if (!data || !data.length) return (
    <div style={{ color: 'var(--color-text-muted)', fontSize: 'var(--text-sm)', textAlign: 'center', padding: '60px 0' }}>
      Sem dados no período
    </div>
  );

  const isMobile = typeof window !== 'undefined' && window.innerWidth < 600;
  const { labels, datasets } = transform(data);
  const cfg  = { labels, datasets };
  const opts = {
    responsive: true,
    maintainAspectRatio: false,
    interaction: { mode: 'index', intersect: false },
    plugins: {
      legend: {
        position: 'bottom',
        labels: { color: '#9CA3AF', font: { size: isMobile ? 12 : 11 }, padding: isMobile ? 16 : 12, boxWidth: isMobile ? 24 : 20 },
      },
      tooltip: {
        titleFont: { size: 12 },
        bodyFont: { size: 12 },
        callbacks: {
          label: ctx => ` ${ctx.dataset.label}: ${Number(ctx.raw).toLocaleString('pt-BR',{style:'currency',currency:'BRL'})}`,
        },
      },
    },
    scales: {
      x: {
        ticks: {
          color: '#6B7280',
          font: { size: isMobile ? 10 : 11 },
          maxTicksLimit: isMobile ? 6 : 13,
          maxRotation: isMobile ? 45 : 0,
        },
        grid: { color: 'rgba(255,255,255,0.04)' },
      },
      y: {
        ticks: {
          color: '#6B7280',
          font: { size: isMobile ? 10 : 11 },
          maxTicksLimit: isMobile ? 4 : 6,
          callback: v => v >= 1000 ? `R$ ${(v/1000).toFixed(0)}k` : `R$ ${v}`,
        },
        grid: { color: 'rgba(255,255,255,0.06)' },
      },
    },
  };

  return <Line data={cfg} options={opts} />;
}
