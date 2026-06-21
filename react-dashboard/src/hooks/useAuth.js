import { useState, useEffect } from 'react';
import { isLogged, getEmail, getRole } from '../api/auth';

export function useAuth() {
  const [logged, setLogged] = useState(isLogged);
  const [email,  setEmail]  = useState(getEmail);
  const [role,   setRole]   = useState(getRole);

  useEffect(() => {
    const sync = () => {
      setLogged(isLogged());
      setEmail(getEmail());
      setRole(getRole());
    };
    window.addEventListener('storage', sync);
    return () => window.removeEventListener('storage', sync);
  }, []);

  const refresh = () => {
    setLogged(isLogged());
    setEmail(getEmail());
    setRole(getRole());
  };

  return { logged, email, role, refresh };
}
