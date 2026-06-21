import styles from './KpiCard.module.css';

const fmt = v => Number(v ?? 0).toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' });

const MAP = {
  gastos:       { label: 'Gastos',       icon: '↓', color: 'var(--color-danger)' },
  receitas:     { label: 'Receitas',      icon: '↑', color: 'var(--color-success)' },
  investimentos:{ label: 'Investimentos', icon: '◈', color: 'var(--color-cyan)' },
  saldo:        { label: 'Saldo',         icon: '⬡', color: 'var(--color-primary)' },
};

export default function KpiCard({ type, value }) {
  const { label, icon, color } = MAP[type] || { label: type, icon: '●', color: '#fff' };
  return (
    <div className={styles.card}>
      <div className={styles.icon} style={{ color }}>{icon}</div>
      <div className={styles.label}>{label}</div>
      <div className={styles.value} style={{ color }}>{fmt(value)}</div>
    </div>
  );
}
