import { defineConfig, loadEnv } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'

// https://vitejs.dev/config/
export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '');
  const proxyTarget = env.VITE_API_PROXY_TARGET || 'http://localhost:8000';

  // #region agent log
  fetch('http://127.0.0.1:7248/ingest/4bc30d7b-be40-43cb-a209-7c4afed73eca', { method: 'POST', headers: { 'Content-Type': 'application/json', 'X-Debug-Session-Id': 'e70ed4' }, body: JSON.stringify({ sessionId: 'e70ed4', runId: 'initial', hypothesisId: 'H1', location: 'frontend/vite.config.ts:10', message: 'Vite proxy target resolved', data: { mode, proxyTarget, hasEnvProxyTarget: Boolean(env.VITE_API_PROXY_TARGET) }, timestamp: Date.now() }) }).catch(() => { });
  // #endregion

  return {
    plugins: [react()],
    resolve: {
      alias: {
        '@': path.resolve(__dirname, './src'),
      },
    },
    build: {
      rollupOptions: {
        output: {
          manualChunks: {
            react: ["react", "react-dom"],
            router: ["react-router-dom"],
            framer: ["framer-motion"]
          },
        },
      },
    },
    server: {
      port: Number(env.VITE_PORT || 3000),
      proxy: {
        '/api': {
          target: proxyTarget,
          changeOrigin: true,
        },
        '/frames': {
          target: proxyTarget,
          changeOrigin: true,
        },
        '/fonts': {
          target: proxyTarget,
          changeOrigin: true,
        },
        '/static': {
          target: proxyTarget,
          changeOrigin: true,
        },
      },
    },
    define: {
      __APP_ENV__: JSON.stringify(env.NODE_ENV || mode),
    },
  }
})
