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
import {
  getResumo, getGraficoCats, getGraficoMensal, getGraficoEvolucao,
  getProjecao, getParcelasAtivas, getTransacoes,
  criarTransacao, editarTransacao, deletarTransacao, deletarGrupo,
} from '../api/transacoes';
import styles from './Dashboard.module.css';

/* ── helpers ── */
const BRL = v => Number(v ?? 0).toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' });
const fmtDate = iso => iso ? iso.split('T')[0].split('-').reverse().join('/') : '';
const toISO   = br  => { const [d,m,y] = br.split('/'); return `${y}-${m}-${d}`; };
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
const CATS   = ['','Alimentação','Transporte','Moradia','Saúde','Lazer','Educação','Vestuário','Outros','Investimento'];
const STATUS = ['','PAGO','PENDENTE','CANCELADO'];
const FORMAS = ['','PIX','CREDITO','DEBITO','DINHEIRO','TRANSFERENCIA'];

/* ── table state reducer ── */
const INIT_TABLE = { pagina: 1, tipo: '', categoria: '', status: '', forma: '', ordenar: 'data', direcao: 'desc' };
function tableReducer(s, a) {
  if (a.type === 'set')   return { ...s, [a.key]: a.val, pagina: a.key === 'pagina' ? a.val : 1 };
  if (a.type === 'sort')  return { ...s, ordenar: a.col, direcao: s.ordenar === a.col && s.direcao === 'desc' ? 'asc' : 'desc', pagina: 1 };
  if (a.type === 'reset') return INIT_TABLE;
  return s;
}

const BLANK_FORM = { data: todayISO(), descricao: '', categoria: '', valor: '', tipo: '', status: 'PENDENTE', forma_pagamento: '', responsavel: '', detalhes: '' };

export default function Dashboard() {
  const [periodo, setPeriodo]     = useState('mes_atual');
  const [resumo,  setResumo]      = useState(null);
  const [cats,    setCats]        = useState(null);
  const [mensal,  setMensal]      = useState(null);
  const [evolucao,setEvolucao]    = useState(null);
  const [projecao,setProjecao]    = useState(null);
  const [parcelas,setParcelas]    = useState([]);
  const [transacoes,setTransacoes]= useState({ items:[], total:0, paginas:1 });
  const [investimentos,setInvest] = useState({ items:[], total:0, totalValor:0 });
  const [tableState, dispatch]    = useReducer(tableReducer, INIT_TABLE);
  const [filterCat, setFilterCat] = useState('');

  /* modals */
  const [addOpen,  setAddOpen]  = useState(false);
  const [editOpen, setEditOpen] = useState(false);
  const [editId,   setEditId]   = useState(null);
  const [form,     setForm]     = useState(BLANK_FORM);
  const [formErr,  setFormErr]  = useState('');
  const [saving,   setSaving]   = useState(false);

  /* ── data fetchers ── */
  const loadResumoCharts = useCallback(async () => {
    const [r, c, m, e, p, pa] = await Promise.allSettled([
      getResumo(periodo), getGraficoCats(periodo), getGraficoMensal(),
      getGraficoEvolucao(), getProjecao(), getParcelasAtivas(),
    ]);
    if (r.status  === 'fulfilled') setResumo(r.value.data);
    if (c.status  === 'fulfilled') setCats(c.value.data);
    if (m.status  === 'fulfilled') setMensal(m.value.data);
    if (e.status  === 'fulfilled') setEvolucao(e.value.data);
    if (p.status  === 'fulfilled') setProjecao(p.value.data);
    if (pa.status === 'fulfilled') setParcelas(pa.value.data || []);
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
    };
    const [t, i] = await Promise.allSettled([
      getTransacoes({ ...params, tipo: params.tipo || undefined }),
      getTransacoes({ ...params, tipo: 'INVESTIMENTO' }),
    ]);
    if (t.status === 'fulfilled') setTransacoes(t.value.data);
    if (i.status === 'fulfilled') {
      const d = i.value.data;
      setInvest({
        items: d.items || [],
        total: d.total || 0,
        totalValor: (d.items || []).reduce((s, x) => s + Number(x.valor), 0),
      });
    }
  }, [periodo, tableState, filterCat]);

  useEffect(() => { loadResumoCharts(); }, [loadResumoCharts]);
  useEffect(() => { loadTransacoes();   }, [loadTransacoes]);

  const reload = () => { loadResumoCharts(); loadTransacoes(); };

  /* ── form helpers ── */
  const setF = (k, v) => setForm(f => ({ ...f, [k]: v }));

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
          <PieChart data={cats} onSliceClick={cat=>{ setFilterCat(cat); dispatch({type:'set',key:'categoria',val:cat}); }} />
        </Card>
        <Card className={styles.chartCard}>
          <div className={styles.cardHeader}><span className={styles.cardTitle}>Gastos Mensais (6 meses)</span></div>
          <BarChart data={mensal} />
        </Card>
      </div>

      {/* ── Evolution chart ── */}
      <Card style={{marginBottom:'var(--space-8)'}}>
        <div className={styles.cardHeader}><span className={styles.cardTitle}>Evolução Financeira</span></div>
        <LineChart data={evolucao} />
      </Card>

      {/* ── Projeção ── */}
      {projecao && projecao.length > 0 && (
        <Card style={{marginBottom:'var(--space-8)'}}>
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

      {/* ── Parcelas ativas ── */}
      {parcelas.length > 0 && (
        <div style={{marginBottom:'var(--space-8)'}}>
          <h2 className={styles.sectionTitle}>Parcelas Ativas</h2>
          <div className={styles.parcelasGrid}>
            {parcelas.map(p=>(
              <Card key={p.grupo_parcela_id}>
                <div className={styles.parcelaHeader}>
                  <span className={styles.parcelaDesc}>{p.descricao}</span>
                  <button className={styles.deleteBtn} onClick={()=>handleDeleteGrupo(p.grupo_parcela_id)}>🗑</button>
                </div>
                <div className={styles.parcelaInfo}>
                  <span>{p.pagas}/{p.total} pagas</span>
                  <span>{BRL(p.valor_parcela)}/parcela</span>
                </div>
                <div className={styles.progressTrack}>
                  <div className={styles.progressFill} style={{width:`${(p.pagas/p.total)*100}%`}} />
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
                {(transacoes.items || []).map(t=>(
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
                {!(transacoes.items?.length) && (
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
      <div>
        <div className={styles.tableToolbar}>
          <h2 className={styles.sectionTitle}>Investimentos</h2>
          <div style={{display:'flex',gap:'var(--space-4)'}}>
            <Card style={{padding:'var(--space-3) var(--space-4)',minWidth:160}}>
              <div className={styles.miniLabel}>Período</div>
              <div className={styles.miniValue}>{PERIODOS.find(p=>p.value===periodo)?.label}</div>
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
                {investimentos.items.map(t=>(
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
                {!investimentos.items.length && (
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
    </Layout>
  );
}
