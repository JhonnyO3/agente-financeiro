import api from './client';

export const getRecorrencias   = (params) => api.get('/api/recorrencias', { params });
export const criarRecorrencia  = (body)   => api.post('/api/recorrencias', body);
export const editarRecorrencia = (id, body) => api.put(`/api/recorrencias/${id}`, body);
export const deletarRecorrencia = (id)    => api.delete(`/api/recorrencias/${id}`);
export const materializarRecorrencias = () => api.post('/api/recorrencias/materializar');
