import { defineConfig, loadEnv } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'

// https://vitejs.dev/config/
export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '');
  const proxyTarget = env.VITE_API_PROXY_TARGET || 'http://localhost:8000';

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
