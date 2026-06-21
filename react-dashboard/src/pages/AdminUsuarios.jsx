import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { isAdmin } from '../api/auth';
import { criarUsuario } from '../api/transacoes';
import Layout from '../components/layout/Layout';
import Field, { Input, Select } from '../components/ui/Field';
import Button from '../components/ui/Button';
import Card from '../components/ui/Card';
import styles from './AdminUsuarios.module.css';

export default function AdminUsuarios() {
  const navigate = useNavigate();
  if (!isAdmin()) { navigate('/'); return null; }

  const [form, setForm] = useState({ nome:'', email:'', telefone:'', senha:'', role:'USER' });
  const [error, setError]     = useState('');
  const [success, setSuccess] = useState('');
  const [saving, setSaving]   = useState(false);
  const setF = (k,v) => setForm(f=>({...f,[k]:v}));

  async function handleSubmit(e) {
    e.preventDefault();
    if (!form.nome || !form.email || !form.senha) { setError('Nome, e-mail e senha são obrigatórios.'); return; }
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(form.email)) { setError('E-mail inválido.'); return; }
    if (form.senha.length < 6) { setError('Senha deve ter ao menos 6 caracteres.'); return; }
    setSaving(true); setError(''); setSuccess('');
    try {
      await criarUsuario(form);
      setSuccess('Usuário criado com sucesso!');
      setForm({ nome:'', email:'', telefone:'', senha:'', role:'USER' });
    } catch (err) {
      setError(err.response?.data?.detail || 'Erro ao criar usuário.');
    } finally { setSaving(false); }
  }

  return (
    <Layout>
      <div className={styles.page}>
        <button className={styles.back} onClick={()=>navigate('/')}>← Voltar</button>
        <h1 className={styles.title}>Novo Usuário</h1>
        <Card className={styles.card}>
          {error   && <div className={styles.alert}>{error}</div>}
          {success && <div className={styles.success}>{success}</div>}
          <form className={styles.form} onSubmit={handleSubmit}>
            <Field label="Nome completo" required>
              <Input value={form.nome} onChange={e=>setF('nome',e.target.value)} placeholder="João Silva" />
            </Field>
            <Field label="E-mail" required>
              <Input type="email" value={form.email} onChange={e=>setF('email',e.target.value)} placeholder="joao@email.com" />
            </Field>
            <Field label="Telefone">
              <Input type="tel" value={form.telefone} onChange={e=>setF('telefone',e.target.value)} placeholder="(11) 99999-9999" />
            </Field>
            <Field label="Senha" required>
              <Input type="password" value={form.senha} onChange={e=>setF('senha',e.target.value)} placeholder="••••••••" />
            </Field>
            <Field label="Perfil">
              <Select value={form.role} onChange={e=>setF('role',e.target.value)}>
                <option value="USER">Usuário</option>
                <option value="ADMIN">Administrador</option>
              </Select>
            </Field>
            <Button type="submit" disabled={saving} size="lg">
              {saving ? 'Criando…' : 'Criar Usuário'}
            </Button>
          </form>
        </Card>
      </div>
    </Layout>
  );
}
