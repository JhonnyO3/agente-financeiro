import { useState, useEffect, useCallback } from 'react';
import Layout from '../components/layout/Layout';
import Card from '../components/ui/Card';
import Button from '../components/ui/Button';
import Badge from '../components/ui/Badge';
import Modal from '../components/ui/Modal';
import Field, { Input, Checkbox } from '../components/ui/Field';
import {
  getCartoes, criarCartao, editarCartao, deletarCartao,
  getResumoCartao, vincularCartaoLote,
} from '../api/cartoes';
import { getTransacoes } from '../api/transacoes';
import styles from './Cartoes.module.css';

const BRL = v => Number(v ?? 0).toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' });
const fmtDate = iso => iso ? iso.split('T')[0].split('-').reverse().join('/') : '';

const BLANK_CARTAO = { apelido: '', dia_fechamento: '', dia_vencimento: '', cor: '#7c5cff', ativo: true };

export default function Cartoes() {
  const [cartoes, setCartoes] = useState([]);
  const [selecionado, setSelecionado] = useState(null);

  /* modal de cartão */
  const [formOpen, setFormOpen] = useState(false);
  const [editId, setEditId] = useState(null);
  const [form, setForm] = useState(BLANK_CARTAO);
  const [formErr, setFormErr] = useState('');
  const [saving, setSaving] = useState(false);

  const setF = (k, v) => setForm(f => ({ ...f, [k]: v }));

  const loadCartoes = useCallback(async () => {
    try {
      const { data } = await getCartoes();
      setCartoes(data || []);
    } catch { setCartoes([]); }
  }, []);

  useEffect(() => { loadCartoes(); }, [loadCartoes]);

  function openAdd() { setForm(BLANK_CARTAO); setEditId(null); setFormErr(''); setFormOpen(true); }
  function openEdit(c) {
    setForm({
      apelido: c.apelido || '',
      dia_fechamento: c.dia_fechamento ?? '',
      dia_vencimento: c.dia_vencimento ?? '',
      cor: c.cor || '#7c5cff',
      ativo: c.ativo !== false,
    });
    setEditId(c.id);
    setFormErr('');
    setFormOpen(true);
  }

  async function handleSave(e) {
    e.preventDefault();
    if (!form.apelido.trim()) { setFormErr('Informe um apelido.'); return; }
    setSaving(true); setFormErr('');
    const body = {
      apelido: form.apelido.trim(),
      dia_fechamento: form.dia_fechamento === '' ? null : parseInt(form.dia_fechamento, 10),
      dia_vencimento: form.dia_vencimento === '' ? null : parseInt(form.dia_vencimento, 10),
      cor: form.cor || null,
      ativo: !!form.ativo,
    };
    try {
      if (editId) await editarCartao(editId, body);
      else await criarCartao(body);
      setFormOpen(false);
      await loadCartoes();
    } catch (err) {
      setFormErr(err.response?.data?.erro || 'Erro ao salvar cartão.');
    } finally { setSaving(false); }
  }

  async function handleDelete(id) {
    if (!confirm('Excluir cartão? As transações vinculadas serão desvinculadas (não apagadas).')) return;
    await deletarCartao(id);
    if (selecionado?.id === id) setSelecionado(null);
    await loadCartoes();
  }

  return (
    <Layout>
      <div className={styles.toolbar}>
        <h1 className={styles.pageTitle}>Cartões</h1>
        <Button onClick={openAdd}>+ Cartão</Button>
      </div>

      <div className={styles.grid}>
        {cartoes.map(c => (
          <Card
            key={c.id}
            className={styles.cartao}
            style={{ borderLeft: `4px solid ${c.cor || 'var(--color-primary)'}` }}
            onClick={() => setSelecionado(c)}
          >
            <div className={styles.cartaoTop}>
              <span className={styles.cartaoNome}>{c.apelido}</span>
              <Badge label={c.ativo ? 'Ativo' : 'Inativo'} />
            </div>
            <div className={styles.cartaoMeta}>
              {c.dia_fechamento != null && <span>Fecha dia {c.dia_fechamento}</span>}
              {c.dia_vencimento != null && <span>Vence dia {c.dia_vencimento}</span>}
            </div>
            <div className={styles.cartaoActions}>
              <button className={styles.linkBtn} onClick={ev => { ev.stopPropagation(); openEdit(c); }}>Editar</button>
              <button className={styles.linkBtnDanger} onClick={ev => { ev.stopPropagation(); handleDelete(c.id); }}>Excluir</button>
            </div>
          </Card>
        ))}
        {cartoes.length === 0 && <div className={styles.empty}>Nenhum cartão cadastrado ainda.</div>}
      </div>

      {selecionado && (
        <CartaoDetalhe
          cartao={selecionado}
          onClose={() => setSelecionado(null)}
          onChange={loadCartoes}
        />
      )}

      <Modal
        open={formOpen}
        onClose={() => setFormOpen(false)}
        title={editId ? 'Editar Cartão' : 'Novo Cartão'}
        footer={<>
          <Button variant="ghost" onClick={() => setFormOpen(false)}>Cancelar</Button>
          <Button onClick={handleSave} disabled={saving}>{saving ? 'Salvando…' : 'Salvar'}</Button>
        </>}
      >
        <form onSubmit={handleSave}>
          {formErr && <div className={styles.formAlert}>{formErr}</div>}
          <Field label="Apelido" required>
            <Input value={form.apelido} onChange={e => setF('apelido', e.target.value)} placeholder="Ex: Nubank" />
          </Field>
          <div className={styles.formGrid}>
            <Field label="Dia de fechamento">
              <Input type="number" min="1" max="31" value={form.dia_fechamento} onChange={e => setF('dia_fechamento', e.target.value)} placeholder="1–31" />
            </Field>
            <Field label="Dia de vencimento">
              <Input type="number" min="1" max="31" value={form.dia_vencimento} onChange={e => setF('dia_vencimento', e.target.value)} placeholder="1–31" />
            </Field>
          </div>
          <Field label="Cor">
            <Input type="color" value={form.cor} onChange={e => setF('cor', e.target.value)} />
          </Field>
          <div className={styles.formCheck}>
            <Checkbox label="Cartão ativo" checked={form.ativo} onChange={e => setF('ativo', e.target.checked)} />
          </div>
        </form>
      </Modal>
    </Layout>
  );
}

function CartaoDetalhe({ cartao, onClose, onChange }) {
  const [resumo, setResumo] = useState(null);
  const [gastos, setGastos] = useState([]);
  const [apenasParcelas, setApenasParcelas] = useState(false);
  const [soltos, setSoltos] = useState([]);
  const [selecionados, setSelecionados] = useState(() => new Set());
  const [vinculando, setVinculando] = useState(false);

  const load = useCallback(async () => {
    const [r, g, s] = await Promise.allSettled([
      getResumoCartao(cartao.id),
      getTransacoes({ cartao_id: cartao.id, periodo: 'tudo', ordenar: 'data', direcao: 'desc' }),
      getTransacoes({ sem_cartao: true, periodo: 'tudo', ordenar: 'data', direcao: 'desc' }),
    ]);
    if (r.status === 'fulfilled') setResumo(r.value.data);
    if (g.status === 'fulfilled') setGastos(g.value.data?.itens || []);
    if (s.status === 'fulfilled') setSoltos(s.value.data?.itens || []);
  }, [cartao.id]);

  useEffect(() => { load(); }, [load]);

  const gastosFiltrados = apenasParcelas ? gastos.filter(t => t.parcela_total > 1) : gastos;

  const toggleSel = id => setSelecionados(prev => {
    const n = new Set(prev);
    if (n.has(id)) n.delete(id); else n.add(id);
    return n;
  });

  async function handleVincular() {
    if (selecionados.size === 0) return;
    setVinculando(true);
    try {
      await vincularCartaoLote([...selecionados], cartao.id);
      setSelecionados(new Set());
      await load();
      onChange?.();
    } catch (err) {
      alert(err.response?.data?.erro || 'Erro ao vincular transações.');
    } finally { setVinculando(false); }
  }

  return (
    <Modal open onClose={onClose} title={`Cartão · ${cartao.apelido}`}>
      <div className={styles.resumoRow}>
        <div className={styles.resumoBox}>
          <span className={styles.resumoLabel}>Total do mês</span>
          <span className={styles.resumoValue}>{BRL(resumo?.total_periodo)}</span>
        </div>
        <div className={styles.resumoBox}>
          <span className={styles.resumoLabel}>Parcelas em aberto</span>
          <span className={styles.resumoValue}>{resumo?.parcelas_abertas ?? 0}</span>
        </div>
        <div className={styles.resumoBox}>
          <span className={styles.resumoLabel}>Restante a pagar</span>
          <span className={styles.resumoValue}>{BRL(resumo?.soma_restante)}</span>
        </div>
      </div>

      <div className={styles.sectionHead}>
        <h3 className={styles.sectionTitle}>Gastos do cartão</h3>
        <Checkbox label="Só parcelamentos" checked={apenasParcelas} onChange={e => setApenasParcelas(e.target.checked)} />
      </div>
      <div className={styles.tableWrap}>
        <table className={styles.table}>
          <thead><tr><th>Data</th><th>Descrição</th><th>Categoria</th><th>Valor</th><th>Parcela</th></tr></thead>
          <tbody>
            {gastosFiltrados.map(t => (
              <tr key={t.id}>
                <td>{fmtDate(t.data)}</td>
                <td>{t.descricao}</td>
                <td>{t.categoria}</td>
                <td>{BRL(t.valor)}</td>
                <td>{t.parcela_total > 1 ? `${t.parcela_numero}/${t.parcela_total}` : '—'}</td>
              </tr>
            ))}
            {gastosFiltrados.length === 0 && <tr><td colSpan={5} className={styles.empty}>Nenhum gasto.</td></tr>}
          </tbody>
        </table>
      </div>

      <div className={styles.sectionHead}>
        <h3 className={styles.sectionTitle}>Vincular gastos soltos</h3>
        {selecionados.size > 0 && (
          <Button size="sm" onClick={handleVincular} disabled={vinculando}>
            {vinculando ? 'Vinculando…' : `Vincular ${selecionados.size} a ${cartao.apelido}`}
          </Button>
        )}
      </div>
      <div className={styles.tableWrap}>
        <table className={styles.table}>
          <thead><tr><th style={{ width: 36 }} /><th>Data</th><th>Descrição</th><th>Categoria</th><th>Valor</th></tr></thead>
          <tbody>
            {soltos.map(t => (
              <tr key={t.id}>
                <td><input type="checkbox" checked={selecionados.has(t.id)} onChange={() => toggleSel(t.id)} /></td>
                <td>{fmtDate(t.data)}</td>
                <td>{t.descricao}</td>
                <td>{t.categoria}</td>
                <td>{BRL(t.valor)}</td>
              </tr>
            ))}
            {soltos.length === 0 && <tr><td colSpan={5} className={styles.empty}>Nenhuma transação sem cartão.</td></tr>}
          </tbody>
        </table>
      </div>
    </Modal>
  );
}
