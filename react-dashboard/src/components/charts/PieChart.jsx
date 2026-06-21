import { Doughnut } from 'react-chartjs-2';
import { Chart as ChartJS, ArcElement, Tooltip, Legend } from 'chart.js';

ChartJS.register(ArcElement, Tooltip, Legend);

const CAT_COLORS = {
  ALIMENTACAO:    '#3B72FF',
  TRANSPORTE:     '#22D3EE',
  LAZER:          '#F59E0B',
  EDUCACAO:       '#F472B6',
  GASTOS_FIXOS:   '#A78BFA',
  COMPRAS:        '#FB923C',
  GASTOS_PONTUAIS:'#22C55E',
  INVESTIMENTO:   '#34D399',
  RECEITA:        '#6EE7B7',
};

export default function PieChart({ data, onSliceClick }) {
  if (!data || !data.length) return null;

  const labels = data.map(d => d.categoria);
  const values = data.map(d => Number(d.total));
  const colors = labels.map(l => CAT_COLORS[l] || '#4B5563');

  const cfg = {
    labels,
    datasets: [{ data: values, backgroundColor: colors, borderColor: 'rgba(0,0,0,0.3)', borderWidth: 1, hoverOffset: 8 }],
  };
  const opts = {
    responsive: true,
    maintainAspectRatio: false,
    cutout: '62%',
    plugins: {
      legend: { position: 'bottom', labels: { color: '#9CA3AF', font: { size: 11 }, padding: 12 } },
      tooltip: {
        callbacks: {
          label: ctx => ` ${ctx.label}: ${Number(ctx.raw).toLocaleString('pt-BR',{style:'currency',currency:'BRL'})}`,
        },
      },
    },
    onClick: (_, el) => {
      if (el.length && onSliceClick) onSliceClick(labels[el[0].index]);
    },
  };

  return <Doughnut data={cfg} options={opts} />;
}
