import api, { setTokens, clearTokens } from './client';

export async function login(email, senha) {
  const { data } = await api.post('/auth/login', { email, senha });
  setTokens(data.access_token, data.refresh_token);
  localStorage.setItem('user_email', email);
  localStorage.setItem('user_role', data.role || 'USER');
  return data;
}

export async function logout() {
  const refresh = localStorage.getItem('refresh_token');
  try { await api.post('/auth/logout', { refresh_token: refresh }); } catch (_) {}
  clearTokens();
}

export const getRole  = () => localStorage.getItem('user_role')  || 'USER';
export const getEmail = () => localStorage.getItem('user_email') || '';
export const isAdmin  = () => getRole() === 'ADMIN';
export const isLogged = () => !!localStorage.getItem('access_token');
