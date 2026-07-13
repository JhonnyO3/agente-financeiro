import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  server: {
    port: parseInt(process.env.PORT || '5173'),
    proxy: {
      // 127.0.0.1 (nao 'localhost') evita o atraso/erro de resolucao IPv6 (::1)
      // quando o backend faz bind apenas em 127.0.0.1.
      '/api':   { target: 'http://127.0.0.1:8000', changeOrigin: true },
      '/auth':  { target: 'http://127.0.0.1:8000', changeOrigin: true },
      '/admin': { target: 'http://127.0.0.1:8000', changeOrigin: true },
    },
  },
});
