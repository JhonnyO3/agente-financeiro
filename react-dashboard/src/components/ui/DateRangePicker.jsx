import { useState, useEffect, useRef } from 'react';
import styles from './DateRangePicker.module.css';

const MESES = ['Janeiro','Fevereiro','Março','Abril','Maio','Junho','Julho','Agosto','Setembro','Outubro','Novembro','Dezembro'];
const DIAS_LABEL = ['D','S','T','Q','Q','S','S'];

function diasNoMes(ano, mes) { return new Date(ano, mes + 1, 0).getDate(); }
function primeiroDiaSemana(ano, mes) { return new Date(ano, mes, 1).getDay(); }

function toISO(ano, mes, dia) {
  return `${ano}-${String(mes + 1).padStart(2,'0')}-${String(dia).padStart(2,'0')}`;
}
function fmtDisplay(iso) {
  if (!iso) return '';
  const [y, m, d] = iso.split('-');
  return `${d}/${m}/${y}`;
}

function compareDates(a, b) {
  if (!a || !b) return 0;
  return a < b ? -1 : a > b ? 1 : 0;
}

export default function DateRangePicker({ startDate, endDate, onChange, onClear }) {
  const today = new Date();
  const [open, setOpen]     = useState(false);
  const [viewYear, setYear] = useState(today.getFullYear());
  const [viewMes,  setMes]  = useState(today.getMonth());
  const [picking,  setPick] = useState(null); // null | 'start' | 'end'
  const [hover,    setHover]= useState(null);
  const ref = useRef();

  /* fecha ao clicar fora */
  useEffect(() => {
    if (!open) return;
    function handle(e) { if (ref.current && !ref.current.contains(e.target)) setOpen(false); }
    document.addEventListener('mousedown', handle);
    return () => document.removeEventListener('mousedown', handle);
  }, [open]);

  function navMes(delta) {
    const d = new Date(viewYear, viewMes + delta, 1);
    setYear(d.getFullYear()); setMes(d.getMonth());
  }

  function openPicker() {
    if (!open) { setPick('start'); setHover(null); }
    setOpen(o => !o);
  }

  function clickDia(iso) {
    if (!picking || picking === 'start') {
      onChange(iso, null);
      setPick('end');
    } else {
      const [s, e] = compareDates(startDate, iso) <= 0 ? [startDate, iso] : [iso, startDate];
      onChange(s, e);
      setPick(null);
      setOpen(false);
    }
  }

  function isInRange(iso) {
    const lo = startDate;
    const hi = picking === 'end' ? (hover || endDate) : endDate;
    if (!lo || !hi) return false;
    const [a, b] = compareDates(lo, hi) <= 0 ? [lo, hi] : [hi, lo];
    return iso > a && iso < b;
  }
  function isEdge(iso) { return iso === startDate || iso === endDate; }
  function isHoverEdge(iso) { return picking === 'end' && iso === hover; }

  /* células do calendário */
  const totalDias  = diasNoMes(viewYear, viewMes);
  const offset     = primeiroDiaSemana(viewYear, viewMes); // 0=Dom

  const label = startDate || endDate
    ? `${fmtDisplay(startDate) || '…'} – ${fmtDisplay(endDate) || '…'}`
    : 'Selecionar período';

  const hasSelection = startDate || endDate;

  return (
    <div className={styles.root} ref={ref}>
      <button
        className={`${styles.trigger} ${open ? styles.triggerOpen : ''} ${hasSelection ? styles.triggerActive : ''}`}
        onClick={openPicker}
        type="button"
      >
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <rect x="3" y="4" width="18" height="18" rx="2"/><line x1="16" y1="2" x2="16" y2="6"/><line x1="8" y1="2" x2="8" y2="6"/><line x1="3" y1="10" x2="21" y2="10"/>
        </svg>
        <span>{label}</span>
        {hasSelection && (
          <span className={styles.clearBtn} onClick={e=>{e.stopPropagation(); onClear(); setPick(null);}}>✕</span>
        )}
      </button>

      {open && (
        <div className={styles.popup}>
          {/* header navegação */}
          <div className={styles.header}>
            <button className={styles.nav} onClick={()=>navMes(-1)}>‹</button>
            <span className={styles.mesLabel}>{MESES[viewMes]} {viewYear}</span>
            <button className={styles.nav} onClick={()=>navMes(1)}>›</button>
          </div>

          {/* hint */}
          <div className={styles.hint}>
            {picking === 'start' || !picking ? 'Clique para selecionar a data inicial' : 'Clique para selecionar a data final'}
          </div>

          {/* cabeçalho dias da semana */}
          <div className={styles.calGrid}>
            {DIAS_LABEL.map((d,i)=><div key={i} className={styles.dayHead}>{d}</div>)}

            {/* células fantasma */}
            {Array.from({length: offset}, (_,i)=><div key={`g${i}`} />)}

            {/* dias */}
            {Array.from({length: totalDias}, (_,i)=>{
              const dia = i + 1;
              const iso = toISO(viewYear, viewMes, dia);
              const edge    = isEdge(iso);
              const inRange = isInRange(iso);
              const hEdge   = isHoverEdge(iso);
              const isToday = iso === toISO(today.getFullYear(), today.getMonth(), today.getDate());
              return (
                <div
                  key={dia}
                  className={[
                    styles.day,
                    edge    ? styles.dayEdge    : '',
                    inRange ? styles.dayRange   : '',
                    hEdge   ? styles.dayHEdge   : '',
                    isToday ? styles.dayToday   : '',
                  ].join(' ')}
                  onClick={()=>clickDia(iso)}
                  onMouseEnter={()=>picking==='end'&&setHover(iso)}
                  onMouseLeave={()=>setHover(null)}
                >
                  {dia}
                </div>
              );
            })}
          </div>

          {/* atalhos rápidos */}
          <div className={styles.shortcuts}>
            {[
              ['Esta semana', () => {
                const d = new Date(); const dow = d.getDay();
                const seg = new Date(d); seg.setDate(d.getDate() - (dow===0?6:dow-1));
                const dom = new Date(seg); dom.setDate(seg.getDate()+6);
                onChange(seg.toISOString().split('T')[0], dom.toISOString().split('T')[0]);
                setPick(null); setOpen(false);
              }],
              ['Este mês', () => {
                const d = new Date();
                const ini = new Date(d.getFullYear(), d.getMonth(), 1);
                const fim = new Date(d.getFullYear(), d.getMonth()+1, 0);
                onChange(ini.toISOString().split('T')[0], fim.toISOString().split('T')[0]);
                setPick(null); setOpen(false);
              }],
              ['Mês passado', () => {
                const d = new Date();
                const ini = new Date(d.getFullYear(), d.getMonth()-1, 1);
                const fim = new Date(d.getFullYear(), d.getMonth(), 0);
                onChange(ini.toISOString().split('T')[0], fim.toISOString().split('T')[0]);
                setPick(null); setOpen(false);
              }],
              ['Últimos 30d', () => {
                const fim = new Date(); const ini = new Date(); ini.setDate(fim.getDate()-29);
                onChange(ini.toISOString().split('T')[0], fim.toISOString().split('T')[0]);
                setPick(null); setOpen(false);
              }],
              ['Este ano', () => {
                const y = new Date().getFullYear();
                onChange(`${y}-01-01`, `${y}-12-31`);
                setPick(null); setOpen(false);
              }],
            ].map(([label, fn])=>(
              <button key={label} className={styles.shortcut} onClick={fn} type="button">{label}</button>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
