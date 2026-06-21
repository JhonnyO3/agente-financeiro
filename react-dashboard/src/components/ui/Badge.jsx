import styles from './Badge.module.css';

const MAP = {
  PAGO: 'success', PENDENTE: 'warning', CANCELADO: 'danger',
  GASTO: 'danger', RECEITA: 'success', INVESTIMENTO: 'info',
};

export default function Badge({ label, variant }) {
  const v = variant || MAP[label] || 'default';
  return <span className={`${styles.badge} ${styles[v]}`}>{label}</span>;
}
