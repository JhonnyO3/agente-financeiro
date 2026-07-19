import api from './client';

export const getCartoes       = ()          => api.get('/api/cartoes');
export const criarCartao      = (body)       => api.post('/api/cartoes', body);
export const editarCartao     = (id, body)   => api.put(`/api/cartoes/${id}`, body);
export const deletarCartao    = (id)         => api.delete(`/api/cartoes/${id}`);
export const getResumoCartao  = (id, periodo = 'mes_atual') =>
  api.get(`/api/cartoes/${id}/resumo`, { params: { periodo } });

export const vincularCartaoLote = (ids, cartao_id) =>
  api.patch('/api/transacoes/cartao', { ids, cartao_id });
