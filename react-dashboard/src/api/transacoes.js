import api from './client';

export const getResumo        = (periodo) => api.get('/api/resumo', { params: { periodo } });
export const getGraficoCats   = (periodo) => api.get('/api/grafico/categorias', { params: { periodo } });
export const getGraficoMensal = ()        => api.get('/api/grafico/mensal');
export const getGraficoEvolucao = ()      => api.get('/api/grafico/evolucao');
export const getHeatmap         = ()      => api.get('/api/grafico/heatmap');
export const getProjecao      = ()        => api.get('/api/projecao');
export const getParcelasAtivas = ()       => api.get('/api/parcelas-ativas');

export const getTransacoes = (params)     => api.get('/api/transacoes', { params });
export const criarTransacao = (body)      => api.post('/api/transacoes', body);
export const editarTransacao = (id, body) => api.put(`/api/transacoes/${id}`, body);
export const deletarTransacao = (id)      => api.delete(`/api/transacoes/${id}`);
export const editarGrupo  = (grupo, body)  => api.put(`/api/grupos/${grupo}`, body);
export const deletarGrupo = (grupo)       => api.delete(`/api/grupos/${grupo}`);
export const atualizarStatusLote = (ids, status) => api.patch('/api/transacoes/status', { ids, status });

export const criarUsuario = (body)        => api.post('/admin/usuarios', body);
