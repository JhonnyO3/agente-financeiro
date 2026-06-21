import { Doughnut } from 'react-chartjs-2';
import { Chart as ChartJS, ArcElement, Tooltip, Legend } from 'chart.js';

ChartJS.register(ArcElement, Tooltip, Legend);

const CAT_COLORS = {
  'Alimentação':'#3B72FF','Transporte':'#22D3EE','Moradia':'#A78BFA',
  'Saúde':'#22C55E','Lazer':'#F59E0B','Educação':'#F472B6',
  'Vestuário':'#FB923C','Outros':'#9CA3AF','Investimento':'#34D399',
};

export default function PieChart({ data, onSliceClick }) {
  if (!data) return null;

  const labels  = data.map(d => d.categoria);
  const values  = data.map(d => d.total);
  const colors  = labels.map(l => CAT_COLORS[l] || '#4B5563');

  const cfg = {
    labels,
    datasets: [{ data: values, backgroundColor: colors, borderColor: 'transparent', hoverOffset: 8 }],
  };
  const opts = {
    responsive: true,
    cutout: '60%',
    plugins: {
      legend: { position: 'bottom', labels: { color: '#9CA3AF', font: { size: 12 }, padding: 16 } },
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
