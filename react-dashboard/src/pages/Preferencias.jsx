import { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { Doughnut } from 'react-chartjs-2';
import { Chart as ChartJS, ArcElement, Tooltip, Legend } from 'chart.js';
import Layout from '../components/layout/Layout';
import Card from '../components/ui/Card';
import Field, { Input } from '../components/ui/Field';
import Button from '../components/ui/Button';
import { getPreferencias, salvarPreferencias } from '../api/preferencias';
import styles from './Preferencias.module.css';

ChartJS.register(ArcElement, Tooltip, Legend);

const CATEGORIAS = [
  'ALIMENTACAO', 'TRANSPORTE', 'LAZER', 'EDUCACAO',
  'GASTOS_FIXOS', 'COMPRAS', 'GASTOS_PONTUAIS', 'INVESTIMENTO',
];

const CAT_COLORS = {
  ALIMENTACAO: '#3B72FF', TRANSPORTE: '#22D3EE', LAZER: '#F59E0B', EDUCACAO: '#F472B6',
  GASTOS_FIXOS: '#A78BFA', COMPRAS: '#FB923C', GASTOS_PONTUAIS: '#22C55E',
  INVESTIMENTO: '#34D399', FOLGA: '#4B5563',
};

const BLANK_METAS = () => Object.fromEntries(CATEGORIAS.map(c => [c, '']));

const num = v => parseFloat(String(v).replace(',', '.')) || 0;
const BRL = v => Number(v || 0).toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' });

export default function Preferencias() {
  const navigate = useNavigate();
  const [renda, setRenda]   = useState('');
  const [metas, setMetas]   = useState(BLANK_METAS);
  const [error, setError]   = useState('');
  const [success, setSuccess] = useState('');
  const [saving, setSaving] = useState(false);

  const load = useCallback(async () => {
    try {
      const { data } = await getPreferencias();
      if (data && Object.keys(data).length) {
        setRenda(data.renda_mensal ?? '');
        setMetas({ ...BLANK_METAS(), ...Object.fromEntries(
          Object.entries(data.metas || {}).map(([k, v]) => [k, String(v)])
        ) });
      }
    } catch { /* mantém formulário em branco */ }
  }, []);

  useEffect(() => { load(); }, [load]);

  const setMeta = (cat, val) => setMetas(m => ({ ...m, [cat]: val }));

  const rendaNum = num(renda);
  const temRenda = rendaNum > 0;
  const soma = CATEGORIAS.reduce((s, c) => s + num(metas[c]), 0);
  const folga = Math.max(0, 100 - soma);
  const excedido = soma > 100;

  const valorDe = pct => rendaNum * num(pct) / 100;

  // Fatias: cada categoria com meta > 0 (proporção em %) + a folga.
  const fatias = [
    ...CATEGORIAS.filter(c => num(metas[c]) > 0).map(c => ({ label: c, pct: num(metas[c]) })),
    ...(folga > 0 ? [{ label: 'FOLGA', pct: folga }] : []),
  ];
  const temPizza = fatias.some(f => f.pct > 0);

  const pieCfg = {
    labels: fatias.map(f => f.label),
    datasets: [{
      data: fatias.map(f => f.pct),
      backgroundColor: fatias.map(f => CAT_COLORS[f.label] || '#4B5563'),
      borderColor: 'rgba(0,0,0,0.3)', borderWidth: 1, hoverOffset: 8,
    }],
  };
  const pieOpts = {
    responsive: true, maintainAspectRatio: false, cutout: '58%',
    plugins: {
      legend: { position: 'bottom', labels: { color: '#9CA3AF', font: { size: 11 }, padding: 12 } },
      tooltip: {
        callbacks: {
          label: ctx => {
            const pct = Number(ctx.raw);
            const rs = temRenda ? ` · ${BRL(rendaNum * pct / 100)}` : '';
            return ` ${ctx.label}: ${pct}%${rs}`;
          },
        },
      },
    },
  };

  async function handleSubmit(e) {
    e.preventDefault();
    if (excedido) { setError('A soma das metas não pode passar de 100%.'); return; }
    setSaving(true); setError(''); setSuccess('');
    const metasBody = {};
    for (const c of CATEGORIAS) {
      const v = num(metas[c]);
      if (v > 0) metasBody[c] = v;
    }
    const body = { metas: metasBody };
    if (temRenda) body.renda_mensal = rendaNum;
    try {
      await salvarPreferencias(body);
      setSuccess('Preferências salvas com sucesso!');
    } catch (err) {
      setError(err.response?.data?.erro || 'Erro ao salvar preferências.');
    } finally { setSaving(false); }
  }

  return (
    <Layout>
      <div className={styles.page}>
        <button className={styles.back} onClick={() => navigate('/')}>← Voltar</button>
        <h1 className={styles.title}>Perfil & Preferências</h1>

        <Card className={styles.card}>
          {error   && <div className={styles.alert}>{error}</div>}
          {success && <div className={styles.success}>{success}</div>}
          <form className={styles.form} onSubmit={handleSubmit}>
            <Field label="Renda mensal (R$)">
              <Input
                type="number" step="0.01" min="0"
                value={renda}
                onChange={e => setRenda(e.target.value)}
                placeholder="0.00"
              />
            </Field>

            <div className={styles.metasHeader}>
              <span className={styles.metasTitle}>Metas por categoria (% da renda)</span>
              <span className={excedido ? styles.somaBad : styles.somaOk}>
                {soma.toFixed(1)}% usados{excedido ? ' — passou de 100%' : ` · ${folga.toFixed(1)}% de folga`}
              </span>
            </div>
            {!temRenda && (
              <div className={styles.hint}>Informe a renda mensal para ver quanto cada meta representa em R$.</div>
            )}

            <div className={styles.progressTrack}>
              <div
                className={excedido ? styles.progressFillBad : styles.progressFill}
                style={{ width: `${Math.min(100, soma)}%` }}
              />
            </div>

            <div className={styles.metasGrid}>
              {CATEGORIAS.map(cat => (
                <Field key={cat} label={cat}>
                  <Input
                    type="number" step="0.1" min="0" max="100"
                    value={metas[cat]}
                    onChange={e => setMeta(cat, e.target.value)}
                    placeholder="0"
                  />
                  {num(metas[cat]) > 0 && (
                    <div className={styles.catValor}>
                      {temRenda ? BRL(valorDe(metas[cat])) : `${num(metas[cat])}%`}
                    </div>
                  )}
                </Field>
              ))}
            </div>

            <Button type="submit" size="lg" disabled={saving || excedido}>
              {saving ? 'Salvando…' : 'Salvar Preferências'}
            </Button>
          </form>
        </Card>

        <Card className={styles.card}>
          <div className={styles.pieHeader}>
            <span className={styles.metasTitle}>Distribuição {temRenda ? 'da renda' : '(proporção)'}</span>
            {temRenda && <span className={styles.somaOk}>{BRL(rendaNum)}/mês</span>}
          </div>
          {temPizza ? (
            <div className={styles.pieWrap}>
              <Doughnut data={pieCfg} options={pieOpts} />
            </div>
          ) : (
            <div className={styles.pieEmpty}>
              Preencha as metas por categoria para visualizar a distribuição.
            </div>
          )}
        </Card>
      </div>
    </Layout>
  );
}
