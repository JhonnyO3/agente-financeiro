import { useNavigate } from 'react-router-dom';
import { logout } from '../../api/auth';
import { useAuth } from '../../hooks/useAuth';
import styles from './Navbar.module.css';

export default function Navbar() {
  const { email, role } = useAuth();
  const navigate = useNavigate();

  async function handleLogout() {
    await logout();
    navigate('/login');
  }

  return (
    <nav className={styles.nav}>
      <div className={styles.logo}>
        <div className={styles.dot} />
        Agente Financeiro
      </div>
      <div className={styles.right}>
        <button className={styles.link} onClick={() => navigate('/')}>
          Dashboard
        </button>
        <button className={styles.link} onClick={() => navigate('/cartoes')}>
          Cartões
        </button>
        <button className={styles.link} onClick={() => navigate('/preferencias')}>
          Preferências
        </button>
        {role === 'ADMIN' && (
          <button className={styles.link} onClick={() => navigate('/admin/usuarios/novo')}>
            + Usuário
          </button>
        )}
        <span className={styles.email}>{email}</span>
        <button className={styles.logout} onClick={handleLogout}>Sair</button>
      </div>
    </nav>
  );
}
