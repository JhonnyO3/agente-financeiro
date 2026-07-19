import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import Login         from './pages/Login';
import Dashboard     from './pages/Dashboard';
import Cartoes       from './pages/Cartoes';
import AdminUsuarios from './pages/AdminUsuarios';
import { isLogged }  from './api/auth';

function Guard({ children }) {
  return isLogged() ? children : <Navigate to="/login" replace />;
}

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={<Login />} />
        <Route path="/" element={<Guard><Dashboard /></Guard>} />
        <Route path="/cartoes" element={<Guard><Cartoes /></Guard>} />
        <Route path="/admin/usuarios/novo" element={<Guard><AdminUsuarios /></Guard>} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  );
}
