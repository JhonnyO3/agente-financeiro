import api from './client';

export const getPreferencias = ()      => api.get('/api/preferencias');
export const salvarPreferencias = (body) => api.put('/api/preferencias', body);
export const getAderencia = (periodo = 'mes_atual') =>
  api.get('/api/preferencias/aderencia', { params: { periodo } });
