import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { login } from '../api/auth';
import Button from '../components/ui/Button';
import Field, { Input } from '../components/ui/Field';
import styles from './Login.module.css';

export default function Login() {
  const navigate = useNavigate();
  const [email, setEmail]     = useState('');
  const [senha, setSenha]     = useState('');
  const [error, setError]     = useState('');
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e) {
    e.preventDefault();
    if (!email || !senha) { setError('Preencha email e senha.'); return; }
    setError(''); setLoading(true);
    try {
      await login(email, senha);
      navigate('/', { replace: true });
    } catch (err) {
      setError(err.response?.data?.detail || 'Credenciais inválidas.');
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className={styles.page}>
      <div className={styles.glow} />
      <div className={styles.card}>
        <div className={styles.logo}><div className={styles.dot}/>Agente Financeiro</div>
        <h1 className={styles.title}>Bem-vindo de volta</h1>
        <p className={styles.sub}>Faça login para acessar o dashboard</p>

        {error && <div className={styles.alert}>{error}</div>}

        <form className={styles.form} onSubmit={handleSubmit}>
          <Field label="E-mail" required>
            <Input type="email" value={email} onChange={e => setEmail(e.target.value)} placeholder="seu@email.com" autoFocus />
          </Field>
          <Field label="Senha" required>
            <Input type="password" value={senha} onChange={e => setSenha(e.target.value)} placeholder="••••••••" />
          </Field>
          <Button type="submit" disabled={loading} fullWidth size="lg">
            {loading ? 'Entrando…' : 'Entrar →'}
          </Button>
        </form>
      </div>
    </div>
  );
}
