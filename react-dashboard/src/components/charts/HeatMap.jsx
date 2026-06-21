import styles from './HeatMap.module.css';

const DIAS_SEMANA = ['Seg', 'Ter', 'Qua', 'Qui', 'Sex', 'Sáb', 'Dom'];
const BRL = v => Number(v ?? 0).toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' });

/* interpola entre #111827 (zero) → #3B72FF (max) passando por violeta */
function intensityColor(ratio) {
  if (ratio <= 0) return 'rgba(255,255,255,0.04)';
  // ratio: 0–1
  // low: azul escuro (#1e3a8a) → mid: azul (#3B72FF) → high: ciano (#22D3EE)
  if (ratio < 0.5) {
    const t = ratio * 2;
    const r = Math.round(30  + (59  - 30)  * t);
    const g = Math.round(58  + (114 - 58)  * t);
    const b = Math.round(138 + (255 - 138) * t);
    return `rgb(${r},${g},${b})`;
  } else {
    const t = (ratio - 0.5) * 2;
    const r = Math.round(59  + (34  - 59)  * t);
    const g = Math.round(114 + (211 - 114) * t);
    const b = Math.round(255 + (238 - 255) * t);
    return `rgb(${r},${g},${b})`;
  }
}

export default function HeatMap({ data }) {
  if (!data || !data.length) return (
    <div className={styles.empty}>Sem dados no mês</div>
  );

  const totais  = data.map(d => Number(d.total));
  const maxVal  = Math.max(...totais);
  const totalMes = totais.reduce((s, v) => s + v, 0);
  const diaPico  = totais.indexOf(maxVal) + 1;

  /* offset: dia_semana do primeiro dia (0=Seg) */
  const offset = data[0].dia_semana;

  /* células fantasma para alinhar no calendário */
  const cells = [
    ...Array.from({ length: offset }, (_, i) => ({ ghost: true, key: `g${i}` })),
    ...data.map(d => ({ ...d, ghost: false, ratio: maxVal > 0 ? Number(d.total) / maxVal : 0 })),
  ];

  return (
    <div className={styles.root}>
      {/* cabeçalho dias da semana */}
      <div className={styles.grid}>
        {DIAS_SEMANA.map(d => (
          <div key={d} className={styles.dayLabel}>{d}</div>
        ))}

        {cells.map((cell, i) =>
          cell.ghost ? (
            <div key={cell.key} className={styles.ghost} />
          ) : (
            <div
              key={cell.dia}
              className={`${styles.cell} ${cell.dia === diaPico && maxVal > 0 ? styles.pico : ''}`}
              style={{ '--bg': intensityColor(cell.ratio) }}
              title={`${cell.dia}: ${BRL(cell.total)}`}
            >
              <span className={styles.cellNum}>{cell.dia}</span>
              {Number(cell.total) > 0 && (
                <span className={styles.cellVal}>{BRL(cell.total)}</span>
              )}
            </div>
          )
        )}
      </div>

      {/* legenda */}
      <div className={styles.legend}>
        <div className={styles.legendScale}>
          <span className={styles.legendLabel}>R$ 0</span>
          <div className={styles.legendBar} />
          <span className={styles.legendLabel}>{BRL(maxVal)}</span>
        </div>
        <div className={styles.legendStats}>
          <span>Total do mês: <strong>{BRL(totalMes)}</strong></span>
          {maxVal > 0 && <span>Pico: dia <strong>{diaPico}</strong> ({BRL(maxVal)})</span>}
        </div>
      </div>
    </div>
  );
}
