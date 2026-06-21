import { useState, useEffect, useCallback, useReducer } from 'react';
import Layout from '../components/layout/Layout';
import KpiCard from '../components/ui/KpiCard';
import Card from '../components/ui/Card';
import Badge from '../components/ui/Badge';
import Button from '../components/ui/Button';
import Modal from '../components/ui/Modal';
import Field, { Input, Select } from '../components/ui/Field';
import PieChart from '../components/charts/PieChart';
import BarChart from '../components/charts/BarChart';
import LineChart from '../components/charts/LineChart';
import HeatMap from '../components/charts/HeatMap';
import {
  getResumo, getGraficoCats, getGraficoMensal, getGraficoEvolucao,
  getProjecao, getParcelasAtivas, getTransacoes, getHeatmap,
  criarTransacao, editarTransacao, deletarTransacao, editarGrupo, deletarGrupo,
} from '../api/transacoes';
import styles from './Dashboard.module.css';

/* ── helpers ── */
const BRL = v => Number(v ?? 0).toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' });
const fmtDate = iso => iso ? iso.split('T')[0].split('-').reverse().join('/') : '';
const todayISO = () => new Date().toISOString().split('T')[0];

const PERIODOS = [
  { value:'mes_atual',       label:'Mês Atual' },
  { value:'mes_anterior',    label:'Mês Anterior' },
  { value:'ultimos_3_meses', label:'Últimos 3 Meses' },
  { value:'ultimos_6_meses', label:'Últimos 6 Meses' },
  { value:'ano_atual',       label:'Ano Atual' },
  { value:'tudo',            label:'Tudo' },
];
const TIPOS  = ['','GASTO','RECEITA','INVESTIMENTO'];
const CATS   = ['','ALIMENTACAO','TRANSPORTE','LAZER','EDUCACAO','GASTOS_FIXOS','COMPRAS','GASTOS_PONTUAIS','INVESTIMENTO','RECEITA'];
const STATUS = ['','PAGO','PENDENTE'];
const FORMAS = ['','PIX','CARTAO_CREDITO','CARTAO_DEBITO','BOLETO'];

/* ── table state reducer ── */
const INIT_TABLE = { pagina: 1, tipo: '', categoria: '', status: '', forma: '', ordenar: 'data', direcao: 'desc', dataInicio: '', dataFim: '' };
function tableReducer(s, a) {
  if (a.type === 'set')   return { ...s, [a.key]: a.val, pagina: a.key === 'pagina' ? a.val : 1 };
  if (a.type === 'sort')  return { ...s, ordenar: a.col, direcao: s.ordenar === a.col && s.direcao === 'desc' ? 'asc' : 'desc', pagina: 1 };
  if (a.type === 'reset') return INIT_TABLE;
  return s;
}

const BLANK_FORM = { data: todayISO(), descricao: '', categoria: '', valor: '', tipo: '', status: 'PENDENTE', forma_pagamento: '', responsavel: '', detalhes: '' };
const BLANK_PARCELA_FORM = { descricao: '', valor_parcela: '', pagas: '' };

export default function Dashboard() {
  const [periodo, setPeriodo]     = useState('mes_atual');
  const [resumo,  setResumo]      = useState(null);
  const [cats,    setCats]        = useState(null);
  const [mensal,  setMensal]      = useState(null);
  const [evolucao,setEvolucao]    = useState(null);
  const [projecao,setProjecao]    = useState(null);
  const [parcelas,setParcelas]    = useState([]);
  const [assinaturas,setAssins]   = useState([]);
  const [heatmap,    setHeatmap]  = useState([]);
  const [transacoes,setTransacoes]= useState({ itens:[], total:0, paginas:1 });
  const [investimentos,setInvest] = useState({ itens:[], total:0, totalValor:0 });
  const [tableState, dispatch]    = useReducer(tableReducer, INIT_TABLE);
  const [filterCat, setFilterCat] = useState('');

  /* modals — transação */
  const [addOpen,  setAddOpen]  = useState(false);
  const [editOpen, setEditOpen] = useState(false);
  const [editId,   setEditId]   = useState(null);
  const [form,     setForm]     = useState(BLANK_FORM);
  const [formErr,  setFormErr]  = useState('');
  const [saving,   setSaving]   = useState(false);

  /* modal — editar parcela */
  const [parcelaEditOpen, setParcelaEditOpen] = useState(false);
  const [parcelaEditGrupo, setParcelaEditGrupo] = useState(null);
  const [parcelaForm, setParcelaForm] = useState(BLANK_PARCELA_FORM);
  const [parcelaErr, setParcelaErr]   = useState('');
  const [parcelaSaving, setParcelaSaving] = useState(false);

  /* ── data fetchers ── */
  const loadResumoCharts = useCallback(async () => {
    const [r, c, m, e, p, pa, ass, hm] = await Promise.allSettled([
      getResumo(periodo),
      getGraficoCats(periodo),
      getGraficoMensal(),
      getGraficoEvolucao(),
      getProjecao(),
      getParcelasAtivas(),
      getTransacoes({ categoria: 'GASTOS_FIXOS', periodo: 'mes_atual', ordenar: 'valor', direcao: 'desc' }),
      getHeatmap(),
    ]);
    if (r.status   === 'fulfilled') setResumo(r.value.data);
    if (c.status   === 'fulfilled') setCats(c.value.data);
    if (m.status   === 'fulfilled') setMensal(m.value.data);
    if (e.status   === 'fulfilled') setEvolucao(e.value.data);
    if (p.status   === 'fulfilled') setProjecao(p.value.data);
    if (pa.status  === 'fulfilled') setParcelas(pa.value.data || []);
    if (ass.status === 'fulfilled') setAssins(ass.value.data?.itens || []);
    if (hm.status  === 'fulfilled') setHeatmap(hm.value.data || []);
  }, [periodo]);

  const loadTransacoes = useCallback(async () => {
    const params = {
      periodo, pagina: tableState.pagina,
      tipo: tableState.tipo || undefined,
      categoria: (filterCat || tableState.categoria) || undefined,
      status: tableState.status || undefined,
      forma_pagamento: tableState.forma || undefined,
      ordenar: tableState.ordenar,
      direcao: tableState.direcao,
      data_inicio: tableState.dataInicio || undefined,
      data_fim:    tableState.dataFim    || undefined,
    };
    const [t, i] = await Promise.allSettled([
      getTransacoes({ ...params }),
      getTransacoes({ periodo: 'tudo', tipo: 'INVESTIMENTO', ordenar: 'data', direcao: 'desc' }),
    ]);
    if (t.status === 'fulfilled') setTransacoes(t.value.data);
    if (i.status === 'fulfilled') {
      const d = i.value.data;
      setInvest({
        itens: d.itens || [],
        total: d.total || 0,
        totalValor: (d.itens || []).reduce((s, x) => s + Number(x.valor), 0),
      });
    }
  }, [periodo, tableState, filterCat]);

  useEffect(() => { loadResumoCharts(); }, [loadResumoCharts]);
  useEffect(() => { loadTransacoes();   }, [loadTransacoes]);

  const reload = () => { loadResumoCharts(); loadTransacoes(); };

  /* ── form helpers ── */
  const setF = (k, v) => setForm(f => ({ ...f, [k]: v }));
  const setPF = (k, v) => setParcelaForm(f => ({ ...f, [k]: v }));

  function openAdd()  { setForm(BLANK_FORM); setFormErr(''); setAddOpen(true); }
  function openEdit(t) {
    setForm({
      data: t.data ? t.data.split('T')[0] : todayISO(),
      descricao: t.descricao || '',
      categoria: t.categoria || '',
      valor: String(t.valor || ''),
      tipo: t.tipo || '',
      status: t.status || 'PENDENTE',
      forma_pagamento: t.forma_pagamento || '',
      responsavel: t.responsavel || '',
      detalhes: t.detalhes || '',
    });
    setEditId(t.id);
    setFormErr('');
    setEditOpen(true);
  }

  function openParcelaEdit(p) {
    setParcelaForm({
      descricao: p.descricao || '',
      valor_parcela: String(p.valor_parcela || ''),
      pagas: String(p.pagas ?? ''),
    });
    setParcelaEditGrupo(p);
    setParcelaErr('');
    setParcelaEditOpen(true);
  }

  async function handleAdd(e) {
    e.preventDefault();
    if (!form.data || !form.valor || !form.tipo || !form.categoria) { setFormErr('Preencha os campos obrigatórios.'); return; }
    setSaving(true); setFormErr('');
    try {
      await criarTransacao({ ...form, valor: parseFloat(form.valor.replace(',','.')) });
      setAddOpen(false); reload();
    } catch (err) { setFormErr(err.response?.data?.detail || 'Erro ao salvar.'); }
    finally { setSaving(false); }
  }

  async function handleEdit(e) {
    e.preventDefault();
    if (!form.data || !form.valor || !form.categoria) { setFormErr('Preencha os campos obrigatórios.'); return; }
    setSaving(true); setFormErr('');
    try {
      await editarTransacao(editId, { ...form, valor: parseFloat(form.valor.replace(',','.')) });
      setEditOpen(false); reload();
    } catch (err) { setFormErr(err.response?.data?.detail || 'Erro ao salvar.'); }
    finally { setSaving(false); }
  }

  async function handleParcelaEdit(e) {
    e.preventDefault();
    setParcelaSaving(true); setParcelaErr('');
    try {
      const body = {};
      if (parcelaForm.descricao)    body.descricao    = parcelaForm.descricao;
      if (parcelaForm.valor_parcela) body.valor_parcela = parseFloat(parcelaForm.valor_parcela.replace(',','.'));
      if (parcelaForm.pagas !== '')  body.pagas         = parseInt(parcelaForm.pagas, 10);
      await editarGrupo(parcelaEditGrupo.grupo_parcela_id, body);
      setParcelaEditOpen(false); reload();
    } catch (err) { setParcelaErr(err.response?.data?.detail || 'Erro ao salvar.'); }
    finally { setParcelaSaving(false); }
  }

  async function handleDelete(id) {
    if (!confirm('Excluir transação?')) return;
    await deletarTransacao(id); reload();
  }

  async function handleDeleteGrupo(grupo) {
    if (!confirm('Excluir todas as parcelas deste grupo?')) return;
    await deletarGrupo(grupo); reload();
  }

  /* ── sort indicator ── */
  const sortIcon = col => tableState.ordenar === col ? (tableState.direcao === 'asc' ? ' ▲' : ' ▼') : '';

  /* ── form section shared ── */
  const FormBody = (
    <>
      {formErr && <div className={styles.formAlert}>{formErr}</div>}
      <div className={styles.formGrid}>
        <Field label="Data" required><Input type="date" value={form.data} onChange={e=>setF('data',e.target.value)} /></Field>
        <Field label="Valor (R$)" required><Input type="number" step="0.01" value={form.valor} onChange={e=>setF('valor',e.target.value)} placeholder="0.00" /></Field>
      </div>
      <Field label="Descrição"><Input value={form.descricao} onChange={e=>setF('descricao',e.target.value)} placeholder="Ex: Supermercado…" /></Field>
      <div className={styles.formGrid}>
        <Field label="Tipo" required>
          <Select value={form.tipo} onChange={e=>setF('tipo',e.target.value)}>
            <option value="">Selecione…</option>
            {['GASTO','RECEITA','INVESTIMENTO'].map(t=><option key={t}>{t}</option>)}
          </Select>
        </Field>
        <Field label="Categoria" required>
          <Select value={form.categoria} onChange={e=>setF('categoria',e.target.value)}>
            <option value="">Selecione…</option>
            {CATS.filter(Boolean).map(c=><option key={c}>{c}</option>)}
          </Select>
        </Field>
      </div>
      <div className={styles.formGrid}>
        <Field label="Status">
          <Select value={form.status} onChange={e=>setF('status',e.target.value)}>
            {STATUS.filter(Boolean).map(s=><option key={s}>{s}</option>)}
          </Select>
        </Field>
        <Field label="Forma de Pagamento">
          <Select value={form.forma_pagamento} onChange={e=>setF('forma_pagamento',e.target.value)}>
            <option value="">—</option>
            {FORMAS.filter(Boolean).map(f=><option key={f}>{f}</option>)}
          </Select>
        </Field>
      </div>
      <Field label="Responsável"><Input value={form.responsavel} onChange={e=>setF('responsavel',e.target.value)} /></Field>
      <Field label="Detalhes"><Input value={form.detalhes} onChange={e=>setF('detalhes',e.target.value)} /></Field>
    </>
  );

  return (
    <Layout>
      {/* ── Period selector ── */}
      <div className={styles.toolbar}>
        <h1 className={styles.pageTitle}>Dashboard</h1>
        <div className={styles.toolbarRight}>
          <Select value={periodo} onChange={e=>setPeriodo(e.target.value)} style={{width:'auto'}}>
            {PERIODOS.map(p=><option key={p.value} value={p.value}>{p.label}</option>)}
          </Select>
          <Button onClick={openAdd}>+ Transação</Button>
        </div>
      </div>

      {/* ── KPI Cards ── */}
      <div className={styles.kpiGrid}>
        {['gastos','receitas','investimentos','saldo'].map(k=>(
          <KpiCard key={k} type={k} value={resumo?.[k]} />
        ))}
      </div>

      {/* ── Charts row ── */}
      <div className={styles.chartsRow}>
        <Card className={styles.chartCard}>
          <div className={styles.cardHeader}><span className={styles.cardTitle}>Gastos por Categoria</span></div>
          <div className={styles.chartWrapPie}>
            <PieChart data={cats} onSliceClick={cat=>{ setFilterCat(cat); dispatch({type:'set',key:'categoria',val:cat}); }} />
          </div>
        </Card>
        <Card className={styles.chartCard}>
          <div className={styles.cardHeader}><span className={styles.cardTitle}>Gastos Mensais (6 meses)</span></div>
          <div className={styles.chartWrap}>
            <BarChart data={mensal} />
          </div>
        </Card>
      </div>

      {/* ── HeatMap ── */}
      <Card className={styles.heatmapCard}>
        <div className={styles.cardHeader}>
          <span className={styles.cardTitle}>Gastos por Dia — Mês Atual</span>
        </div>
        <HeatMap data={heatmap} />
      </Card>

      {/* ── Evolution chart ── */}
      <Card className={styles.evolucaoCard}>
        <div className={styles.cardHeader}><span className={styles.cardTitle}>Evolução Financeira</span></div>
        <div className={styles.chartWrapLine}>
          <LineChart data={evolucao} />
        </div>
      </Card>

      {/* ── Projeção ── */}
      {projecao && projecao.length > 0 && (
        <Card className={styles.projecaoCard}>
          <div className={styles.cardHeader}><span className={styles.cardTitle}>Projeção 6 Meses</span></div>
          <div className={styles.tableWrap}>
            <table className={styles.table}>
              <thead><tr>
                {Object.keys(projecao[0]).map(k=><th key={k}>{k}</th>)}
              </tr></thead>
              <tbody>
                {projecao.map((row,i)=>(
                  <tr key={i}>{Object.values(row).map((v,j)=><td key={j}>{typeof v==='number'?BRL(v):v}</td>)}</tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>
      )}

      {/* ── Assinaturas ── */}
      {assinaturas.length > 0 && (
        <div style={{marginBottom:'var(--space-8)'}}>
          <div className={styles.sectionHeader}>
            <h2 className={styles.sectionTitle}>Assinaturas & Gastos Fixos</h2>
            <span className={styles.sectionMeta}>{assinaturas.length} item{assinaturas.length !== 1 ? 's' : ''} · {BRL(assinaturas.reduce((s,a)=>s+Number(a.valor),0))}/mês</span>
          </div>
          <div className={styles.assinsGrid}>
            {assinaturas.map(a => (
              <Card key={a.id} className={styles.assinCard}>
                <div className={styles.assinTop}>
                  <span className={styles.assinNome}>{a.descricao}</span>
                  <span className={styles.assinValor}>{BRL(a.valor)}</span>
                </div>
                <div className={styles.assinMeta}>
                  <Badge label={a.status} />
                  <span className={styles.assinData}>{fmtDate(a.data)}</span>
                </div>
              </Card>
            ))}
          </div>
        </div>
      )}

      {/* ── Parcelas ativas ── */}
      {parcelas.length > 0 && (
        <div style={{marginBottom:'var(--space-8)'}}>
          <h2 className={styles.sectionTitle}>Parcelas Ativas</h2>
          <div className={styles.parcelasGrid}>
            {parcelas.map(p=>(
              <Card key={p.grupo_parcela_id} className={styles.parcelaCard} onClick={()=>openParcelaEdit(p)} style={{cursor:'pointer'}}>
                <div className={styles.parcelaHeader}>
                  <span className={styles.parcelaDesc}>{p.descricao}</span>
                  <button className={styles.deleteBtn} onClick={ev=>{ev.stopPropagation();handleDeleteGrupo(p.grupo_parcela_id);}}>🗑</button>
                </div>
                <div className={styles.parcelaInfo}>
                  <span>{p.pagas}/{p.parcela_total} pagas</span>
                  <span>{BRL(p.valor_parcela)}/parcela</span>
                </div>
                <div className={styles.progressTrack}>
                  <div className={styles.progressFill} style={{width:`${p.parcela_total > 0 ? (p.pagas/p.parcela_total)*100 : 0}%`}} />
                </div>
                <div className={styles.parcelaFaltam}>
                  <span>Faltam {p.parcela_total - p.pagas} parcela{(p.parcela_total - p.pagas) !== 1 ? 's' : ''}</span>
                  <span className={styles.parcelaTotal}>{BRL((p.parcela_total - p.pagas) * Number(p.valor_parcela))} restantes</span>
                </div>
              </Card>
            ))}
          </div>
        </div>
      )}

      {/* ── Transações table ── */}
      <div style={{marginBottom:'var(--space-8)'}}>
        <div className={styles.tableToolbar}>
          <h2 className={styles.sectionTitle}>Transações</h2>
        </div>
        <div className={styles.filtersBar}>
          <div className={styles.filters}>
            <Select value={tableState.tipo}      onChange={e=>dispatch({type:'set',key:'tipo',val:e.target.value})} style={{width:'auto'}}>
              <option value="">Todos tipos</option>
              {TIPOS.filter(Boolean).map(t=><option key={t}>{t}</option>)}
            </Select>
            <Select value={tableState.categoria || filterCat} onChange={e=>{setFilterCat('');dispatch({type:'set',key:'categoria',val:e.target.value})}} style={{width:'auto'}}>
              <option value="">Todas cats.</option>
              {CATS.filter(Boolean).map(c=><option key={c}>{c}</option>)}
            </Select>
            <Select value={tableState.status} onChange={e=>dispatch({type:'set',key:'status',val:e.target.value})} style={{width:'auto'}}>
              <option value="">Todos status</option>
              {STATUS.filter(Boolean).map(s=><option key={s}>{s}</option>)}
            </Select>
            <Select value={tableState.forma} onChange={e=>dispatch({type:'set',key:'forma',val:e.target.value})} style={{width:'auto'}}>
              <option value="">Todas formas</option>
              {FORMAS.filter(Boolean).map(f=><option key={f}>{f}</option>)}
            </Select>
          </div>
          <div className={styles.dateRange}>
            <span className={styles.dateRangeLabel}>Período</span>
            <Input type="date" value={tableState.dataInicio} onChange={e=>dispatch({type:'set',key:'dataInicio',val:e.target.value})} className={styles.dateInput} title="Data inicial" />
            <span className={styles.dateRangeSep}>–</span>
            <Input type="date" value={tableState.dataFim} onChange={e=>dispatch({type:'set',key:'dataFim',val:e.target.value})} className={styles.dateInput} title="Data final" />
            {(tableState.dataInicio || tableState.dataFim) && (
              <button className={styles.clearDates} onClick={()=>{dispatch({type:'set',key:'dataInicio',val:''});dispatch({type:'set',key:'dataFim',val:''});}}>✕</button>
            )}
          </div>
        </div>

        <Card>
          <div className={styles.tableWrap}>
            <table className={styles.table}>
              <thead><tr>
                <th onClick={()=>dispatch({type:'sort',col:'data'})}     className={styles.sortable}>Data{sortIcon('data')}</th>
                <th onClick={()=>dispatch({type:'sort',col:'descricao'})} className={styles.sortable}>Descrição{sortIcon('descricao')}</th>
                <th>Categoria</th>
                <th onClick={()=>dispatch({type:'sort',col:'valor'})}     className={styles.sortable}>Valor{sortIcon('valor')}</th>
                <th>Tipo</th>
                <th>Status</th>
                <th>Forma</th>
                <th style={{width:80}}>Ações</th>
              </tr></thead>
              <tbody>
                {(transacoes.itens || []).map(t=>(
                  <tr key={t.id}>
                    <td>{fmtDate(t.data)}</td>
                    <td>{t.descricao}</td>
                    <td>{t.categoria}</td>
                    <td className={t.tipo==='RECEITA'?styles.positive:t.tipo==='GASTO'?styles.negative:''}>{BRL(t.valor)}</td>
                    <td><Badge label={t.tipo} /></td>
                    <td><Badge label={t.status} /></td>
                    <td>{t.forma_pagamento || '—'}</td>
                    <td>
                      <div className={styles.actions}>
                        <button className={styles.editBtn}   onClick={()=>openEdit(t)}>✏️</button>
                        <button className={styles.deleteBtn} onClick={()=>handleDelete(t.id)}>🗑</button>
                      </div>
                    </td>
                  </tr>
                ))}
                {!(transacoes.itens?.length) && (
                  <tr><td colSpan={8} className={styles.empty}>Nenhuma transação encontrada</td></tr>
                )}
              </tbody>
            </table>
          </div>

          {/* pagination */}
          <div className={styles.pagination}>
            <Button variant="ghost" size="sm" disabled={tableState.pagina<=1} onClick={()=>dispatch({type:'set',key:'pagina',val:tableState.pagina-1})}>← Anterior</Button>
            <span className={styles.pageInfo}>Página {tableState.pagina} de {transacoes.paginas || 1}</span>
            <Button variant="ghost" size="sm" disabled={tableState.pagina>=(transacoes.paginas||1)} onClick={()=>dispatch({type:'set',key:'pagina',val:tableState.pagina+1})}>Próxima →</Button>
          </div>
        </Card>
      </div>

      {/* ── Investimentos ── */}
      <div style={{marginBottom:'var(--space-8)'}}>
        <div className={styles.tableToolbar}>
          <h2 className={styles.sectionTitle}>Investimentos</h2>
          <div style={{display:'flex',gap:'var(--space-4)',flexWrap:'wrap'}}>
            <Card style={{padding:'var(--space-3) var(--space-4)',minWidth:140}}>
              <div className={styles.miniLabel}>Total registros</div>
              <div className={styles.miniValue}>{investimentos.total}</div>
            </Card>
            <Card style={{padding:'var(--space-3) var(--space-4)',minWidth:160}}>
              <div className={styles.miniLabel}>Total Investido</div>
              <div className={styles.miniValue} style={{color:'var(--color-cyan)'}}>{BRL(investimentos.totalValor)}</div>
            </Card>
          </div>
        </div>
        <Card>
          <div className={styles.tableWrap}>
            <table className={styles.table}>
              <thead><tr>
                <th>Data</th><th>Descrição</th><th>Categoria</th>
                <th>Valor</th><th>Status</th><th style={{width:80}}>Ações</th>
              </tr></thead>
              <tbody>
                {investimentos.itens.map(t=>(
                  <tr key={t.id}>
                    <td>{fmtDate(t.data)}</td>
                    <td>{t.descricao}</td>
                    <td>{t.categoria}</td>
                    <td className={styles.positive}>{BRL(t.valor)}</td>
                    <td><Badge label={t.status} /></td>
                    <td>
                      <div className={styles.actions}>
                        <button className={styles.editBtn}   onClick={()=>openEdit(t)}>✏️</button>
                        <button className={styles.deleteBtn} onClick={()=>handleDelete(t.id)}>🗑</button>
                      </div>
                    </td>
                  </tr>
                ))}
                {!investimentos.itens.length && (
                  <tr><td colSpan={6} className={styles.empty}>Nenhum investimento encontrado</td></tr>
                )}
              </tbody>
            </table>
          </div>
        </Card>
      </div>

      {/* ── Add Modal ── */}
      <Modal open={addOpen} onClose={()=>setAddOpen(false)} title="Adicionar Transação"
        footer={<><Button variant="ghost" onClick={()=>setAddOpen(false)}>Cancelar</Button><Button onClick={handleAdd} disabled={saving}>{saving?'Salvando…':'Adicionar'}</Button></>}>
        <form onSubmit={handleAdd}>{FormBody}</form>
      </Modal>

      {/* ── Edit Modal ── */}
      <Modal open={editOpen} onClose={()=>setEditOpen(false)} title="Editar Transação"
        footer={<><Button variant="ghost" onClick={()=>setEditOpen(false)}>Cancelar</Button><Button onClick={handleEdit} disabled={saving}>{saving?'Salvando…':'Salvar'}</Button></>}>
        <form onSubmit={handleEdit}>{FormBody}</form>
      </Modal>

      {/* ── Edit Parcela Modal ── */}
      <Modal open={parcelaEditOpen} onClose={()=>setParcelaEditOpen(false)} title="Editar Parcelamento"
        footer={<><Button variant="ghost" onClick={()=>setParcelaEditOpen(false)}>Cancelar</Button><Button onClick={handleParcelaEdit} disabled={parcelaSaving}>{parcelaSaving?'Salvando…':'Salvar'}</Button></>}>
        <form onSubmit={handleParcelaEdit}>
          {parcelaErr && <div className={styles.formAlert}>{parcelaErr}</div>}
          {parcelaEditGrupo && (
            <div className={styles.parcelaEditInfo}>
              <span>Total: <strong>{parcelaEditGrupo.parcela_total}</strong> parcelas</span>
              <span>Próxima: <strong>#{parcelaEditGrupo.parcela_numero}</strong></span>
            </div>
          )}
          <Field label="Nome / Descrição">
            <Input value={parcelaForm.descricao} onChange={e=>setPF('descricao',e.target.value)} placeholder="Nome do parcelamento" />
          </Field>
          <div className={styles.formGrid}>
            <Field label="Valor por parcela (R$)">
              <Input type="number" step="0.01" value={parcelaForm.valor_parcela} onChange={e=>setPF('valor_parcela',e.target.value)} placeholder="0.00" />
            </Field>
            <Field label={`Parcelas pagas (de ${parcelaEditGrupo?.parcela_total ?? '?'})`}>
              <Input type="number" min="0" max={parcelaEditGrupo?.parcela_total} value={parcelaForm.pagas} onChange={e=>setPF('pagas',e.target.value)} placeholder="0" />
            </Field>
          </div>
          {parcelaForm.valor_parcela && parcelaEditGrupo && (
            <div className={styles.parcelaEditCalc}>
              Total do parcelamento: <strong>{BRL(parseFloat(parcelaForm.valor_parcela||0) * parcelaEditGrupo.parcela_total)}</strong>
              {' · '}Restante: <strong>{BRL(parseFloat(parcelaForm.valor_parcela||0) * (parcelaEditGrupo.parcela_total - parseInt(parcelaForm.pagas||0,10)))}</strong>
            </div>
          )}
        </form>
      </Modal>
    </Layout>
  );
}
