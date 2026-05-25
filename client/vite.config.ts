import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      '@': '/src',
    },
  },
  server: {
    port: 3000,
    host: true,
    // Dev-прокси повторяет маршрутизацию gateway (Caddy) в проде:
    //   /api       → chat-api
    //   /socket.io → support-rt (WebSocket вынесен из монолита в волне 5)
    //   /stt       → stt-service (префикс срезается, как и на gateway)
    proxy: {
      '/api': {
        target: 'http://localhost:5001',
        changeOrigin: true,
      },
      '/socket.io': {
        target: 'http://localhost:5040',
        changeOrigin: true,
        ws: true,
      },
      '/stt': {
        target: 'http://localhost:5020',
        changeOrigin: true,
        rewrite: (p) => p.replace(/^\/stt/, ''),
      },
    },
  },
  build: {
    target: 'es2020',
    sourcemap: false,
    rollupOptions: {
      output: {
        manualChunks: {
          react: ['react', 'react-dom', 'react-router-dom'],
          markdown: ['react-markdown', 'remark-gfm'],
          socket: ['socket.io-client'],
        },
      },
    },
  },
});
