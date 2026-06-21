import { Navigate } from 'react-router-dom';
import { isLogged } from '../../api/auth';
import Navbar from './Navbar';
import styles from './Layout.module.css';

export default function Layout({ children }) {
  if (!isLogged()) return <Navigate to="/login" replace />;
  return (
    <div className={styles.root}>
      <Navbar />
      <main className={styles.main}>{children}</main>
    </div>
  );
}
