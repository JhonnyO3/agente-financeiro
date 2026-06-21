import styles from './Card.module.css';

export default function Card({ children, className = '', glow, onClick, style }) {
  return (
    <div
      className={`${styles.card} ${glow ? styles.glow : ''} ${className}`}
      onClick={onClick}
      style={style}
    >
      {children}
    </div>
  );
}
