import { useState, useCallback } from 'react';

export function useApi(fn) {
  const [data, setData]   = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const execute = useCallback(async (...args) => {
    setLoading(true);
    setError(null);
    try {
      const res = await fn(...args);
      setData(res.data);
      return res.data;
    } catch (e) {
      const msg = e.response?.data?.detail || e.response?.data?.message || e.message || 'Erro desconhecido';
      setError(msg);
      throw e;
    } finally {
      setLoading(false);
    }
  }, [fn]);

  return { data, loading, error, execute, setData };
}
