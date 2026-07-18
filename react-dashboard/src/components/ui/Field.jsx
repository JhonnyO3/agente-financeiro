import styles from './Field.module.css';

export default function Field({ label, error, children, required }) {
  return (
    <div className={styles.field}>
      {label && <label className={styles.label}>{label}{required && <span className={styles.req}>*</span>}</label>}
      {children}
      {error && <span className={styles.error}>{error}</span>}
    </div>
  );
}

export function Input({ ...props }) {
  return <input className={styles.input} {...props} />;
}

export function Select({ children, ...props }) {
  return <select className={styles.select} {...props}>{children}</select>;
}

export function Checkbox({ label, ...props }) {
  return (
    <label className={styles.checkbox}>
      <input type="checkbox" {...props} />
      {label && <span>{label}</span>}
    </label>
  );
}
