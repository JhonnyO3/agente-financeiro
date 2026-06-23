import axios from 'axios';

// Em dev com VITE_API_URL setado: URL absoluta (chamada direta ao backend).
// Em Docker/prod sem VITE_API_URL: URL relativa — nginx proxy assume /api, /auth, /admin.
const BASE = import.meta.env.VITE_API_URL || '';

const api = axios.create({ baseURL: BASE, headers: { 'Content-Type': 'application/json' } });

/* ── token helpers ── */
const getTokens = () => ({
  access: localStorage.getItem('access_token'),
  refresh: localStorage.getItem('refresh_token'),
});
const setTokens = (access, refresh) => {
  localStorage.setItem('access_token', access);
  if (refresh) localStorage.setItem('refresh_token', refresh);
};
const clearTokens = () => {
  localStorage.removeItem('access_token');
  localStorage.removeItem('refresh_token');
  localStorage.removeItem('user_email');
  localStorage.removeItem('user_role');
};

/* ── request interceptor: inject Bearer ── */
api.interceptors.request.use(cfg => {
  const { access } = getTokens();
  if (access) cfg.headers.Authorization = `Bearer ${access}`;
  return cfg;
});

/* ── response interceptor: auto-refresh on 401 ── */
let refreshing = null;
api.interceptors.response.use(
  res => res,
  async err => {
    const orig = err.config;
    if (err.response?.status === 401 && !orig._retry) {
      orig._retry = true;
      if (!refreshing) {
        const { refresh } = getTokens();
        refreshing = axios
          .post(`${BASE}/auth/refresh`, { refresh_token: refresh })
          .then(r => { setTokens(r.data.access_token, null); return r.data.access_token; })
          .catch(() => { clearTokens(); window.location.href = '/login'; })
          .finally(() => { refreshing = null; });
      }
      const token = await refreshing;
      if (token) {
        orig.headers.Authorization = `Bearer ${token}`;
        return api(orig);
      }
    }
    return Promise.reject(err);
  }
);

export { getTokens, setTokens, clearTokens };
export default api;
