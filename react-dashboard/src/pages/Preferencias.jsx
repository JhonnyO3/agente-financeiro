import { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import Layout from '../components/layout/Layout';
import Card from '../components/ui/Card';
import Field, { Input } from '../components/ui/Field';
import Button from '../components/ui/Button';
import { getPreferencias, salvarPreferencias } from '../api/preferencias';
import styles from './Preferencias.module.css';

const CATEGORIAS = [
  'ALIMENTACAO', 'TRANSPORTE', 'LAZER', 'EDUCACAO',
  'GASTOS_FIXOS', 'COMPRAS', 'GASTOS_PONTUAIS', 'INVESTIMENTO',
];

const BLANK_METAS = () => Object.fromEntries(CATEGORIAS.map(c => [c, '']));

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

  const soma = CATEGORIAS.reduce((s, c) => s + (parseFloat(String(metas[c]).replace(',', '.')) || 0), 0);
  const folga = Math.max(0, 100 - soma);
  const excedido = soma > 100;

  async function handleSubmit(e) {
    e.preventDefault();
    if (excedido) { setError('A soma das metas não pode passar de 100%.'); return; }
    setSaving(true); setError(''); setSuccess('');
    const metasBody = {};
    for (const c of CATEGORIAS) {
      const v = parseFloat(String(metas[c]).replace(',', '.'));
      if (!Number.isNaN(v) && v > 0) metasBody[c] = v;
    }
    const body = { metas: metasBody };
    const rendaNum = parseFloat(String(renda).replace(',', '.'));
    if (!Number.isNaN(rendaNum)) body.renda_mensal = rendaNum;
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
              <span className={styles.metasTitle}>Metas por categoria (% das saídas)</span>
              <span className={excedido ? styles.somaBad : styles.somaOk}>
                {soma.toFixed(1)}% usados{excedido ? ' — passou de 100%' : ` · ${folga.toFixed(1)}% de folga`}
              </span>
            </div>

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
                </Field>
              ))}
            </div>

            <Button type="submit" size="lg" disabled={saving || excedido}>
              {saving ? 'Salvando…' : 'Salvar Preferências'}
            </Button>
          </form>
        </Card>
      </div>
    </Layout>
  );
}
