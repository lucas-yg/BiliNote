import { defineConfig, loadEnv } from 'vite';
import react from '@vitejs/plugin-react';
import path from 'path';
import tailwindcss from '@tailwindcss/vite';
import dns from 'dns';

// 强制使用IPv4解析
dns.setDefaultResultOrder('ipv4first');

// https://vitejs.dev/config/
export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd());
  const apiBaseUrl = env.VITE_API_BASE_URL || 'http://127.0.0.1:8483';
  const port = parseInt(env.VITE_FRONTEND_PORT || '3015', 10);

  return {
    base: './',
    plugins: [react(), tailwindcss()],
    resolve: {
      alias: {
        '@': path.resolve(__dirname, './src'),
      },
    },
    build: {
      outDir: 'dist',
      assetsDir: 'assets',
      sourcemap: false,
      chunkSizeWarningLimit: 1500,
      target: 'es2015',
      minify: 'terser',
      terserOptions: {
        compress: {
          drop_console: true,
          drop_debugger: true,
        },
      },
      rollupOptions: {
        output: {
          // manualChunks(id) {
          //   if (id.includes('node_modules/react') || id.includes('node_modules/react-dom')) {
          //     return 'reactVendor';
          //   }
          //   if (id.includes('node_modules/antd')) {
          //     return 'antdVendor';
          //   }
          //   if (id.includes('node_modules/@ant-design/icons')) {
          //     return 'iconsVendor';
          //   }
          //   if (id.includes('node_modules')) {
          //     return 'vendor';
          //   }
          //   // 不返回任何值，避免 rollup bug
          // },
        },
      },
    },
    optimizeDeps: {
      include: ['react', 'react-dom', 'antd'],
    },
    server: {
      host: '0.0.0.0',
      port: port,
      proxy: {
        '/api': {
          target: apiBaseUrl,
          changeOrigin: true,
          rewrite: (path) => path.replace(/^\/api/, '/api'),
        },
        '/static': {
          target: apiBaseUrl,
          changeOrigin: true,
          rewrite: (path) => path.replace(/^\/static/, '/static'),
        },
      },
    },
  };
});
